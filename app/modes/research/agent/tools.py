from __future__ import annotations

import asyncio
import base64
import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from core.config import paper_review_agent_cfg
from modes.research.agent.alignment import align_grobid_citations, build_parsed_pages_from_texts
from core.knowledge_base import extract_pdf_pages
from modes.research.agent.models import AgentClaim, AgentReviewContext, AgentSection
from modes.research.agent.parsers import extract_docling_page_texts
from modes.research.agent.quality import evaluate_document_quality
from modes.research.parser import TheoremProofPair, extract_statement_candidates_from_text
from modes.research.reviewer import (
    StructuredDocument,
    build_structured_document,
    enrich_pair_from_section,
    review_claim,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_docling_extract_page_texts = extract_docling_page_texts


def _agent_cfg_value(config_key: str, default: str = "") -> str:
    return str(paper_review_agent_cfg().get(config_key, default) or default).strip()


def _mathpix_base_url() -> str:
    return _agent_cfg_value("mathpix_base_url", "https://api.mathpix.com").rstrip("/")


def _mathpix_credentials() -> tuple[str, str]:
    cfg = paper_review_agent_cfg()
    return str(cfg.get("mathpix_app_id") or "").strip(), str(cfg.get("mathpix_app_key") or "").strip()


def _mistral_ocr_proxy() -> str:
    return _agent_cfg_value("mistral_ocr_url", "")


def _grobid_base_url() -> str:
    configured = _agent_cfg_value("grobid_url", "").rstrip("/")
    if configured:
        return configured

    use_public_demo = str(paper_review_agent_cfg().get("grobid_use_public_demo", False)).strip().lower()
    if use_public_demo in {"1", "true", "yes", "on"}:
        return str(paper_review_agent_cfg().get("grobid_public_demo_url", "https://grobidorg-grobid.hf.space")).strip().rstrip("/")
    return ""

def _sections_from_document(
    document: StructuredDocument,
    *,
    parser_source: str,
    low_confidence_pages: list[int],
    quality_score: float,
) -> list[AgentSection]:
    sections: list[AgentSection] = []
    for unit in document.sections:
        unit_pages = set(range(unit.page_start, unit.page_end + 1))
        low = bool(unit_pages & set(low_confidence_pages))
        unit_quality = quality_score if not low else max(0.2, quality_score - 0.25)
        sections.append(AgentSection(
            unit_id=unit.unit_id,
            section_title=unit.section_title,
            section_path=unit.section_path,
            page_start=unit.page_start,
            page_end=unit.page_end,
            raw_text=unit.raw_text,
            parser_source=parser_source,
            quality_score=round(unit_quality, 3),
            low_confidence=low,
            context_before=unit.context_before,
            context_after=unit.context_after,
            local_definitions=list(unit.local_definitions),
            local_citations=list(unit.local_citations),
        ))
    return sections


async def parse_pdf_primary_tool(
    pdf_bytes: bytes,
    *,
    source: str,
    lang: str = "zh",
) -> AgentReviewContext:
    page_texts = _docling_extract_page_texts(pdf_bytes)
    parser_source = "docling" if page_texts else "pipeline"
    if not page_texts:
        page_texts = extract_pdf_pages(pdf_bytes)

    clean_pages = [(p or "").strip() for p in page_texts if (p or "").strip()]
    parsed_pages = build_parsed_pages_from_texts(clean_pages, parser_source=parser_source)
    quality_score, low_confidence_pages, page_scores = evaluate_document_quality(parsed_pages)
    document = build_structured_document(clean_pages, source=source)
    sections = _sections_from_document(
        document,
        parser_source=parser_source,
        low_confidence_pages=low_confidence_pages,
        quality_score=quality_score,
    )
    context = AgentReviewContext(
        source=source,
        pdf_bytes=pdf_bytes,
        page_texts=clean_pages,
        structured_document=document,
        sections=sections,
        parsed_pages=parsed_pages,
        parser_source=parser_source,
        quality_score=quality_score,
        low_confidence_pages=low_confidence_pages,
        parser_details={
            "lang": lang,
            "page_count": len(clean_pages),
            "page_quality": {page_num: vars(score) for page_num, score in page_scores.items()},
        },
    )
    context.with_step(
        "parsing_primary",
        "ok",
        parser_source=parser_source,
        quality_score=quality_score,
        low_confidence_pages=low_confidence_pages,
    )
    return context


async def _try_grobid_fulltext(pdf_bytes: bytes, *, source: str) -> dict[str, dict]:
    base_url = _grobid_base_url()
    if not base_url:
        return {}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            files = {"input": (source, pdf_bytes, "application/pdf")}
            data = {"consolidateHeader": "1", "consolidateCitations": "1"}
            resp = await client.post(f"{base_url}/api/processFulltextDocument", files=files, data=data)
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.info("GROBID fulltext parse failed: %s", exc)
        return {}

    try:
        root = ET.fromstring(resp.text)
    except Exception as exc:  # noqa: BLE001
        logger.info("GROBID TEI parse failed: %s", exc)
        return {}

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    entries: dict[str, dict] = {}
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", ns):
        xml_id = bibl.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")
        title = "".join(bibl.findall(".//tei:title", ns)[0].itertext()).strip() if bibl.findall(".//tei:title", ns) else ""
        doi_el = bibl.find(".//tei:idno[@type='DOI']", ns)
        doi = "".join(doi_el.itertext()).strip() if doi_el is not None else ""
        key = xml_id or title.lower()
        if key:
            entries[key] = {"title": title, "doi": doi, "xml_id": xml_id}

    for ref in root.findall(".//tei:ref[@type='bibr']", ns):
        target = (ref.attrib.get("target") or "").lstrip("#")
        text = "".join(ref.itertext()).strip()
        if not text:
            continue
        meta = dict(entries.get(target, {}))
        meta["callout"] = text
        entries[text.lower()] = meta
    return entries


async def check_agent_tool_health() -> dict:
    health = {
        "docling": {"status": "unknown"},
        "grobid": {"status": "disabled"},
        "mathpix": {"status": "disabled"},
        "mistral_ocr": {"status": "disabled"},
    }

    try:
        import docling  # noqa: F401
        health["docling"] = {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        health["docling"] = {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}

    grobid_url = _grobid_base_url()
    if grobid_url:
        source = "public_demo" if "hf.space" in grobid_url else "configured"
        try:
            timeout = httpx.Timeout(30.0, connect=10.0) if source == "public_demo" else httpx.Timeout(15.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{grobid_url}/api/health")
                resp.raise_for_status()
                health["grobid"] = {"status": "ok", "url": grobid_url, "source": source}
        except Exception as exc:  # noqa: BLE001
            if source == "public_demo":
                health["grobid"] = {
                    "status": "configured",
                    "url": grobid_url,
                    "source": source,
                    "warning": f"{type(exc).__name__}: {exc}",
                }
            else:
                health["grobid"] = {"status": "unreachable", "url": grobid_url, "source": source, "error": f"{type(exc).__name__}: {exc}"}

    if all(_mathpix_credentials()):
        health["mathpix"] = {"status": "configured", "base_url": _mathpix_base_url()}

    mistral_url = _mistral_ocr_proxy()
    if mistral_url:
        health["mistral_ocr"] = {"status": "configured", "url": mistral_url}

    return health


async def _try_mathpix_page_ocr(pdf_bytes: bytes, *, source: str, page_num: int) -> str:
    app_id, app_key = _mathpix_credentials()
    if not app_id or not app_key:
        return ""

    headers = {"app_id": app_id, "app_key": app_key}
    options = {
        "page_ranges": str(page_num),
        "streaming": False,
        "conversion_formats": {"md": True},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        submit = await client.post(
            f"{_mathpix_base_url()}/v3/pdf",
            headers=headers,
            files={"file": (source, pdf_bytes, "application/pdf")},
            data={"options_json": json.dumps(options)},
        )
        submit.raise_for_status()
        pdf_id = (submit.json() or {}).get("pdf_id")
        if not pdf_id:
            return ""

        for _ in range(12):
            status_resp = await client.get(f"{_mathpix_base_url()}/v3/pdf/{pdf_id}", headers=headers)
            status_resp.raise_for_status()
            status = (status_resp.json() or {}).get("status", "")
            if status == "completed":
                for ext in ("mmd", "md"):
                    result = await client.get(f"{_mathpix_base_url()}/v3/pdf/{pdf_id}.{ext}", headers=headers)
                    if result.status_code == 200 and result.text.strip():
                        return result.text.strip()
                return ""
            if status == "error":
                return ""
            await asyncio.sleep(2)
    return ""


async def _try_mistral_proxy_ocr(pdf_bytes: bytes, *, source: str, pages: list[int], lang: str) -> dict[int, str]:
    proxy_url = _mistral_ocr_proxy()
    if not proxy_url:
        return {}
    try:
        payload = {
            "filename": source,
            "pages": pages,
            "lang": lang,
            "document_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
            resp = await client.post(proxy_url, json=payload)
            resp.raise_for_status()
            data = resp.json() or {}
    except Exception as exc:  # noqa: BLE001
        logger.info("Mistral OCR proxy fallback failed: %s", exc)
        return {}

    page_map = data.get("pages") or {}
    out: dict[int, str] = {}
    for raw_page, value in page_map.items():
        try:
            page_num = int(raw_page)
        except Exception:
            continue
        if isinstance(value, str) and value.strip():
            out[page_num] = value.strip()
    return out


async def parse_pdf_fallback_tool(
    context: AgentReviewContext,
    *,
    pages_to_retry: Optional[list[int]] = None,
    lang: str = "zh",
) -> AgentReviewContext:
    pages = sorted(set(pages_to_retry or context.low_confidence_pages))
    if not pages:
        return context

    replacements: dict[int, str] = {}

    used_mathpix = False
    if all(_mathpix_credentials()):
        for page in pages:
            try:
                recovered = await _try_mathpix_page_ocr(context.pdf_bytes, source=context.source, page_num=page)
            except Exception as exc:  # noqa: BLE001
                logger.info("Mathpix fallback failed on page %s: %s", page, exc)
                recovered = ""
            if recovered:
                replacements[page] = recovered
                used_mathpix = True

    if not replacements and _mistral_ocr_proxy():
        replacements = await _try_mistral_proxy_ocr(context.pdf_bytes, source=context.source, pages=pages, lang=lang)

    if replacements:
        for page_num, text in replacements.items():
            if 1 <= page_num <= len(context.page_texts):
                context.page_texts[page_num - 1] = text
        context.parser_source = "mathpix" if used_mathpix else "mistral_ocr"
        context.parsed_pages = build_parsed_pages_from_texts(context.page_texts, parser_source=context.parser_source)
        quality_score, low_conf_pages, page_scores = evaluate_document_quality(context.parsed_pages)
        context.quality_score = quality_score
        context.low_confidence_pages = [p for p in low_conf_pages if p not in replacements]
        context.structured_document = build_structured_document(context.page_texts, source=context.source)
        context.sections = _sections_from_document(
            context.structured_document,
            parser_source=context.parser_source,
            low_confidence_pages=context.low_confidence_pages,
            quality_score=context.quality_score,
        )
        context.fallback_pages = sorted(replacements)
        context.parser_details["page_quality"] = {page_num: vars(score) for page_num, score in page_scores.items()}
        context.with_step("running_page_fallback", "ok", fallback_pages=context.fallback_pages, provider=context.parser_source)
        return context

    logger.info("No fallback OCR result available for pages %s", pages)
    context.fallback_pages = []
    context.with_step("running_page_fallback", "skipped", fallback_pages=pages, lang=lang)
    return context


def classify_claims_tool(claims: list[AgentClaim]) -> list[AgentClaim]:
    for claim in claims:
        ref = (claim.pair.ref or "").lower()
        env = (claim.pair.env_type or "").lower()
        statement = (claim.pair.statement or "").lower()
        if any(token in ref or token in env for token in ("definition", "remark", "example", "notation", "定义", "注记", "例", "记号")):
            claim.claim_kind = "background_fact"
        elif any(token in ref or token in env for token in ("lemma", "claim", "corollary", "引理", "断言", "推论")):
            claim.claim_kind = "supporting_lemma"
        elif any(token in statement for token in ("recall that", "well-known", "it is known", "众所周知", "记住", "classical fact")):
            claim.claim_kind = "background_fact"
        elif not claim.pair.proof and any(token in statement for token in ("by ", "according to", "see ", "由", "根据", "见")):
            claim.claim_kind = "citation_only"
        else:
            claim.claim_kind = "core_result"
        claim.pair.claim_kind = claim.claim_kind
    return claims


async def extract_claim_batches_tool(
    context: AgentReviewContext,
    *,
    max_claims: int,
    model: Optional[str] = None,
    lang: str = "zh",
    batch_size: int = 3,
):
    seen: set[str] = set()
    claim_id = 1
    pending_batch: list[AgentClaim] = []

    for section in context.sections:
        location_hint = (
            f"{section.section_path} (page {section.page_start})"
            if section.page_start == section.page_end
            else f"{section.section_path} (pages {section.page_start}-{section.page_end})"
        )
        extracted = await extract_statement_candidates_from_text(
            section.raw_text,
            source=context.source,
            location_hint=location_hint,
            model=model,
            lang=lang,
        )

        if not extracted and any(token in section.raw_text.lower() for token in ("theorem", "proposition", "corollary", "proof", "定理", "命题", "推论", "证明")):
            synthetic = TheoremProofPair(
                env_type="section",
                ref=None,
                statement=section.section_title if not section.section_title.startswith("section ") else section.raw_text.split("\n", 1)[0][:200],
                proof=section.raw_text[:2200] if "proof" in section.raw_text.lower() or "证明" in section.raw_text else None,
                source=context.source,
                location_hint=location_hint,
                parser_source=context.parser_source,
                quality_score=section.quality_score,
            )
            extracted = [synthetic]

        reviewer_section = next((unit for unit in context.structured_document.sections if unit.unit_id == section.unit_id), None)
        if reviewer_section is None:
            continue

        for pair in extracted:
            pair = enrich_pair_from_section(pair, reviewer_section, document=context.structured_document)
            pair.parser_source = section.parser_source
            pair.quality_score = section.quality_score
            key = "".join(ch for ch in (pair.statement or "").lower() if ch.isalnum())
            if not key or key in seen:
                continue
            seen.add(key)
            pending_batch.append(AgentClaim(
                claim_id=claim_id,
                pair=pair,
                section_id=section.unit_id,
                parser_source=section.parser_source,
                quality_score=section.quality_score,
            ))
            claim_id += 1
            if len(seen) >= max_claims * 4:
                break
            if len(pending_batch) >= batch_size:
                yield classify_claims_tool(pending_batch)
                pending_batch = []
        if len(seen) >= max_claims * 4:
            break

    if pending_batch:
        yield classify_claims_tool(pending_batch)


async def extract_claims_tool(
    context: AgentReviewContext,
    *,
    max_claims: int,
    model: Optional[str] = None,
    lang: str = "zh",
) -> list[AgentClaim]:
    claims: list[AgentClaim] = []
    async for batch in extract_claim_batches_tool(context, max_claims=max_claims, model=model, lang=lang):
        claims.extend(batch)
        if len(claims) >= max_claims * 4:
            break

    context.with_step("extracting_claims", "ok", count=len(claims))
    return claims


async def resolve_citations_tool(context: AgentReviewContext, claims: list[AgentClaim]) -> dict[str, dict]:
    citation_map = await _try_grobid_fulltext(context.pdf_bytes, source=context.source)
    context.citation_map = citation_map
    context.aligned_citations = align_grobid_citations(context.parsed_pages, citation_map)
    if citation_map:
        for claim in claims:
            extra_terms = []
            for term in claim.pair.local_citations:
                meta = citation_map.get(term.lower()) or citation_map.get(term)
                if meta:
                    title = (meta.get("title") or "").strip()
                    doi = (meta.get("doi") or "").strip()
                    if title:
                        extra_terms.append(title)
                    if doi:
                        extra_terms.append(doi)
            if extra_terms:
                claim.pair.local_citations = list(dict.fromkeys([*claim.pair.local_citations, *extra_terms]))
    context.with_step(
        "aligning_references",
        "ok" if citation_map else "skipped",
        citation_count=len(citation_map),
        aligned_count=len(context.aligned_citations),
    )
    return citation_map


async def verify_claim_tool(
    claim: AgentClaim,
    *,
    idx: int,
    check_logic: bool,
    check_citations: bool,
    check_symbols: bool,
) -> tuple[AgentClaim, object]:
    review = await review_claim(
        claim.pair,
        idx,
        claim_kind=claim.claim_kind,
        check_logic=check_logic,
        check_citations=check_citations,
        check_symbols=check_symbols,
    )
    claim.review_confidence = float(review.theorem.review_confidence or 0.0)
    claim.pair.review_confidence = claim.review_confidence
    return claim, review


def get_local_context_tool(context: AgentReviewContext, *, section_id: int, keywords: Optional[list[str]] = None, max_chars: int = 2200) -> str:
    section = next((section for section in context.sections if section.unit_id == section_id), None)
    if section is None:
        return ""
    candidates = [
        section.context_before,
        section.raw_text,
        section.context_after,
        "\n".join(section.local_definitions[:4]),
    ]
    merged = "\n\n".join(part.strip() for part in candidates if part and part.strip())
    if keywords:
        lowered = merged.lower()
        keyword_hits = [kw for kw in keywords if kw and kw.lower() in lowered]
        if keyword_hits:
            merged = f"Keywords: {', '.join(keyword_hits)}\n\n{merged}"
    return merged[:max_chars]


def get_citation_detail_tool(context: AgentReviewContext, *, callout: str) -> dict:
    normalized = callout.strip().lower()
    for citation in context.aligned_citations:
        if citation.callout.lower() == normalized or citation.key == normalized.replace(" ", ""):
            return {
                "callout": citation.callout,
                "title": citation.title,
                "doi": citation.doi,
                "page_num": citation.page_num,
                "block_id": citation.block_id,
                "alignment_score": citation.alignment_score,
            }
    meta = context.citation_map.get(normalized) or context.citation_map.get(callout)
    return meta or {}


def submit_verification_result_tool(
    *,
    is_valid: bool,
    flaws_found: list[str],
    confidence: float,
    needs_human_review: bool,
    reason: str = "",
) -> dict:
    return {
        "is_valid": bool(is_valid),
        "flaws_found": [str(item).strip() for item in flaws_found if str(item).strip()],
        "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
        "needs_human_review": bool(needs_human_review),
        "reason": str(reason).strip(),
    }
