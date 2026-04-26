from __future__ import annotations

import logging
from typing import Optional

from modes.research.agent.models import AgentClaim, AgentRunResult
from modes.research.agent.tools import (
    extract_claim_batches_tool,
    get_citation_detail_tool,
    get_local_context_tool,
    parse_pdf_fallback_tool,
    parse_pdf_primary_tool,
    resolve_citations_tool,
    submit_verification_result_tool,
    verify_claim_tool,
)
from modes.research.reviewer import (
    ProgressCb,
    ResultCb,
    ReviewReport,
    TheoremReview,
    _determine_verdict,
    _emit,
    review_paper_pages,
)

logger = logging.getLogger(__name__)

_CLAIM_PRIORITY = {
    "core_result": 0,
    "supporting_lemma": 1,
    "background_fact": 2,
    "citation_only": 3,
}


def _claim_sort_key(claim: AgentClaim) -> tuple[int, int, float]:
    return (
        _CLAIM_PRIORITY.get(claim.claim_kind, 9),
        0 if claim.pair.has_proof() else 1,
        -float(claim.quality_score or 0.0),
    )


def _expanded_context(claim: AgentClaim) -> str:
    parts = [
        claim.pair.context_before or "",
        claim.pair.context_excerpt or "",
        claim.pair.context_after or "",
    ]
    merged = "\n\n".join(part.strip() for part in parts if part and part.strip())
    return merged[:4500]


async def run_paper_review_agent(
    pdf_bytes: bytes,
    *,
    source: str,
    max_theorems: int = 5,
    progress: ProgressCb = None,
    result_cb: ResultCb = None,
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
    model: Optional[str] = None,
    lang: str = "zh",
) -> ReviewReport:
    await _emit(progress, "parse_pdf", "正在以 agent 模式解析论文…")
    context = await parse_pdf_primary_tool(pdf_bytes, source=source, lang=lang)
    await _emit(progress, "chunk", f"主解析器 `{context.parser_source}` 已生成 {len(context.sections)} 个结构块…")

    if context.low_confidence_pages:
        await _emit(progress, "quality", f"检测到 {len(context.low_confidence_pages)} 个低置信页面，准备执行 fallback…")
        context = await parse_pdf_fallback_tool(context, pages_to_retry=context.low_confidence_pages, lang=lang)
        if context.fallback_pages:
            await _emit(progress, "fallback", f"已对 {len(context.fallback_pages)} 个页面执行 fallback 解析。")

    await _emit(progress, "quality", f"文档质量评分 {context.quality_score:.0%}，低置信页 {len(context.low_confidence_pages)}。")
    await _emit(progress, "extracting_claims", "正在分批提取命题并准备审查…")

    claims: list[AgentClaim] = []
    async for batch in extract_claim_batches_tool(
        context,
        max_claims=max_theorems,
        model=model,
        lang=lang,
        batch_size=2,
    ):
        claims.extend(batch)
        await _emit(progress, "classify", f"新增 {len(batch)} 条命题候选，累计 {len(claims)} 条。")
        if len(claims) >= max_theorems * 2:
            break

    if not claims:
        await _emit(progress, "fallback", "Agent 未提取到有效命题，回退为现有论文审查 pipeline…")
        return await review_paper_pages(
            context.page_texts,
            source=source,
            max_theorems=max_theorems,
            progress=progress,
            result_cb=result_cb,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
            model=model,
            lang=lang,
        )

    claims.sort(key=_claim_sort_key)
    claims = claims[: max_theorems * 2]
    await _emit(progress, "aligning_references", f"已分类 {len(claims)} 条候选命题，正在解析引用…")
    citation_map = await resolve_citations_tool(context, claims)
    if citation_map:
        await _emit(progress, "citations", f"已建立 {len(citation_map)} 条引用映射。")

    reviews: list[TheoremReview] = []
    retries = 0
    uncertain_claims = 0

    for claim in claims:
        if len(reviews) >= max_theorems:
            break
        idx = len(reviews) + 1
        label = claim.pair.section_title or claim.pair.location_hint or claim.pair.source
        await _emit(progress, "reviewing_claim", f"Agent 审查命题 {idx}/{max_theorems}（{label}）…")
        claim, review = await verify_claim_tool(
            claim,
            idx=idx,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )

        if review.verdict != "Correct" and claim.claim_kind in {"core_result", "supporting_lemma"} and claim.retry_count < 2:
            citation_details = [get_citation_detail_tool(context, callout=term) for term in claim.pair.local_citations[:3]]
            keywords = [claim.pair.ref or "", claim.pair.section_title or "", claim.claim_kind]
            expanded = get_local_context_tool(context, section_id=claim.section_id, keywords=keywords)
            if not expanded:
                expanded = _expanded_context(claim)
            if expanded and expanded != (claim.pair.context_excerpt or ""):
                retries += 1
                claim.retry_count += 1
                claim.pair.context_excerpt = expanded
                if any(detail for detail in citation_details):
                    extra_citations = []
                    for detail in citation_details:
                        title = (detail.get("title") or "").strip()
                        doi = (detail.get("doi") or "").strip()
                        if title:
                            extra_citations.append(title)
                        if doi:
                            extra_citations.append(doi)
                    if extra_citations:
                        claim.pair.local_citations = list(dict.fromkeys([*claim.pair.local_citations, *extra_citations]))
                await _emit(progress, "retrying_claim", f"命题 {idx} 初审存在缺口，补充上下文后重试…")
                claim, review = await verify_claim_tool(
                    claim,
                    idx=idx,
                    check_logic=check_logic,
                    check_citations=check_citations,
                    check_symbols=check_symbols,
                )

        if review.verdict != "Correct" and claim.retry_count >= 1:
            claim.uncertain = True
            uncertain_claims += 1

        verification_signal = submit_verification_result_tool(
            is_valid=review.verdict == "Correct",
            flaws_found=[issue.description for issue in review.issues],
            confidence=claim.review_confidence or review.theorem.review_confidence or 0.0,
            needs_human_review=claim.uncertain,
            reason=review.verification.summary if review.verification else "",
        )
        review.theorem.claim_kind = claim.claim_kind
        review.theorem.parser_source = claim.parser_source
        review.theorem.quality_score = claim.quality_score
        review.theorem.review_confidence = verification_signal["confidence"] or claim.review_confidence or review.theorem.review_confidence
        reviews.append(review)
        await _emit(result_cb, {"kind": "theorem", "index": idx, "data": review.to_dict()})

    if not reviews:
        await _emit(progress, "fallback", "Agent 未产出审查结果，回退为现有论文审查 pipeline…")
        return await review_paper_pages(
            context.page_texts,
            source=source,
            max_theorems=max_theorems,
            progress=progress,
            result_cb=result_cb,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
            model=model,
            lang=lang,
        )

    all_issues = [issue for review in reviews for issue in review.issues]
    run_result = AgentRunResult(
        claims=claims,
        retries=retries,
        uncertain_claims=uncertain_claims,
        claims_classified=len(claims),
        fallback_pages=len(context.fallback_pages),
        parser_source=context.parser_source,
        quality_score=context.quality_score,
        citation_map_size=len(citation_map),
    )
    await _emit(progress, "done", "Agent 审查完成，正在汇总结果…")
    return ReviewReport(
        source=source,
        overall_verdict=_determine_verdict(all_issues),
        theorem_reviews=list(reviews),
        issues=all_issues,
        stats={
            "paper_pages": len(context.page_texts),
            "chunks_processed": len(context.sections),
            "sections_processed": len(context.sections),
            "structured_sections": len(context.structured_document.sections),
            "statement_candidates": len(claims),
            "theorems_parsed": len(claims),
            "theorems_checked": len(reviews),
            "claims_reviewed": len(reviews),
            "claims_classified": run_result.claims_classified,
            "fallback_pages": run_result.fallback_pages,
            "agent_retries": run_result.retries,
            "uncertain_claims": run_result.uncertain_claims,
            "citations_checked": sum(len(review.citation_checks) for review in reviews),
            "citation_map_size": run_result.citation_map_size,
            "issues_found": len(all_issues),
            "parser_source": run_result.parser_source,
            "quality_score": run_result.quality_score,
            "input_type": "paper_pages",
            "scan_completed": len(reviews) < max_theorems,
            "agent_mode": True,
        },
    )
