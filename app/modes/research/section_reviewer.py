"""PDF 论文审查（Nanonets Markdown → 大章节 → LLM 结构化 JSON）。

与旧 pipeline 区别：
  - 不按页硬切定理；不将章节标题伪装成 theorem；
  - 无证明或未逐步验证时不得输出 ``Correct``，只能 ``NotChecked`` / ``Partial``；
  - 引用核查仅基于章节文本，不做 TheoremSearch 误匹配。
"""
from __future__ import annotations

import inspect
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from core.config import nanonets_cfg
from core.llm import chat_json, lang_sys_suffix
from core.nanonets_client import NanonetsExtractResult, extract_pdf_markdown_nanonets

logger = logging.getLogger(__name__)

ProgressCb = Optional[Callable[[str, str], Awaitable[None]]]
ResultCb = Optional[Callable[[dict], Awaitable[None]]]

DEFAULT_SECTION_MODEL = "gemini-3.1-pro"

# chat_json 仅作提示的精简 schema（非严格 JSON Schema draft）
SECTION_REVIEW_SCHEMA: dict[str, Any] = {
    "section_title": "string — 本段对应的大章节标题（若文本无标题可写 Document）",
    "page_range": "string — 估计页码范围，如 3-7，未知则空字符串",
    "main_claims": [
        {
            "role": "theorem | lemma | corollary | proposition | informal_claim — 不得填 section_heading",
            "statement": "string — 数学陈述原文摘要，禁止把章节标题当作定理陈述",
            "proof_present": "boolean — 文本中是否出现针对该陈述的证明或证明草图",
            "verification_status": "verified | has_gaps | not_checked | insufficient_evidence",
            "verdict": "Correct | Partial | Incorrect | NotChecked",
            "source_quote": "string — 支持判断的原文短引（<=400字）",
        }
    ],
    "proofs_found": [{"label": "string", "summary": "string", "source_quote": "string"}],
    "logic_issues": [
        {"severity": "low | medium | high | critical", "description": "string", "source_quote": "string"}
    ],
    "citation_issues": [{"detail": "string", "source_quote": "string"}],
    "confidence": "number 0-1 — 对本节审查整体置信度",
    "source_quotes": [{"label": "string", "quote": "string"}],
}


SECTION_SYSTEM_PROMPT = """You are a meticulous mathematics paper reviewer.
Rules:
1) Output ONLY valid JSON matching the schema shape given in the user message. No markdown fences.
2) Never treat a section/chapter heading (e.g. "Introduction", "The Sphere Packing Problem in Dimension 24") as a theorem statement.
3) For each real mathematical claim (theorem/lemma/corollary/proposition or important informal claim), fill main_claims.
4) If there is no proof or only a proof sketch in the text, set proof_present=false and verification_status must be "not_checked" or "insufficient_evidence", and verdict MUST be "NotChecked" (never "Correct").
5) If you did not line-by-line verify the logic, use verification_status "not_checked" and verdict "NotChecked".
6) Citation issues: only flag unclear or broken INTERNAL references visible in this section (e.g. broken numbering). Do NOT invent external library matches.
7) source_quote fields must be verbatim excerpts from the provided section text (short).
"""


def split_major_sections(markdown: str) -> list[dict[str, str]]:
    """按 Markdown 一级/二级标题切分为大章节。"""
    text = (markdown or "").strip()
    if not text:
        return []

    lines = text.splitlines()
    sections: list[dict[str, str]] = []
    current_title = "(Preamble)"
    current_buf: list[str] = []

    def flush() -> None:
        body = "\n".join(current_buf).strip()
        if current_title == "(Preamble)" and not body:
            return
        sections.append({"title": current_title.strip(), "body": body if body else "(empty)"})

    for line in lines:
        s = line.strip()
        if s.startswith("###"):
            current_buf.append(line)
            continue
        if s.startswith("## ") and not s.startswith("###"):
            flush()
            current_title = s.lstrip("#").strip()
            current_buf = []
            continue
        if s.startswith("# ") and not s.startswith("##"):
            flush()
            current_title = s.lstrip("#").strip()
            current_buf = []
            continue
        current_buf.append(line)

    flush()

    # 合并过碎：若只有 Preamble 且很短，仍返回单节
    if not sections:
        return [{"title": "Document", "body": text}]
    return sections


def _truncate(s: str, max_chars: int) -> str:
    s = s or ""
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n…(truncated)…"


async def _emit(cb: ResultCb, payload: dict) -> None:
    if not cb:
        return
    r = cb(payload)
    if inspect.isawaitable(r):
        await r  # type: ignore[arg-type]


async def _emit_progress(cb: ProgressCb, step: str, msg: str) -> None:
    if not cb:
        return
    r = cb(step, msg)
    if inspect.isawaitable(r):
        await r  # type: ignore[arg-type]


def _normalize_verdict_token(v: str) -> str:
    v = (v or "").strip()
    mapping = {
        "correct": "Correct",
        "partial": "Partial",
        "incorrect": "Incorrect",
        "notchecked": "NotChecked",
        "not_checked": "NotChecked",
    }
    return mapping.get(v.lower(), v if v in ("Correct", "Partial", "Incorrect", "NotChecked") else "NotChecked")


def _normalize_status_token(s: str) -> str:
    s = (s or "").strip().lower().replace("-", "_")
    if s in ("verified", "has_gaps", "not_checked", "insufficient_evidence"):
        return s
    aliases = {
        "notchecked": "not_checked",
        "insufficientevidence": "insufficient_evidence",
        "hasgaps": "has_gaps",
    }
    return aliases.get(s, "not_checked")


def enforce_verdict_rules(section: dict[str, Any]) -> dict[str, Any]:
    """强制：无证明 / not_checked / insufficient_evidence 不得为 Correct。"""
    sec = dict(section)
    claims = []
    for c in sec.get("main_claims") or []:
        if not isinstance(c, dict):
            continue
        cc = dict(c)
        proof_present = bool(cc.get("proof_present"))
        status = _normalize_status_token(str(cc.get("verification_status") or ""))
        cc["verification_status"] = status
        verdict = _normalize_verdict_token(str(cc.get("verdict") or ""))
        role = str(cc.get("role") or "").lower()
        stmt = str(cc.get("statement") or "").strip()

        # 章节标题式陈述：降级为 not_checked
        if role == "section_heading" or _looks_like_section_heading(stmt, sec.get("section_title") or ""):
            cc["verification_status"] = "not_checked"
            verdict = "NotChecked"
            cc["proof_present"] = False

        if not proof_present or status in ("not_checked", "insufficient_evidence"):
            if verdict == "Correct":
                verdict = "NotChecked"
        cc["verdict"] = verdict
        claims.append(cc)
    sec["main_claims"] = claims
    return sec


_HEADING_LIKE = re.compile(
    r"^(introduction|abstract|acknowledgements|references|appendix|background|"
    r"related work|discussion|conclusion|overview|notation|preliminaries)\b",
    re.I,
)


def _looks_like_section_heading(statement: str, section_title: str) -> bool:
    st = statement.strip()
    if len(st) < 120 and _HEADING_LIKE.match(st):
        return True
    if section_title and st.lower() == section_title.strip().lower():
        return True
    return False


def infer_paper_title(markdown: str, sections_payload: list[dict[str, Any]]) -> str:
    """从首个一级标题或 LLM 返回推断论文题目。"""
    for line in (markdown or "").splitlines():
        s = line.strip()
        if s.startswith("# ") and not s.startswith("##"):
            return s.lstrip("#").strip()
    for sec in sections_payload:
        t = str(sec.get("section_title") or "").strip()
        if t and t != "Document":
            return t
    return ""


def aggregate_overall_verdict(sections: list[dict[str, Any]]) -> str:
    """汇总 overall_verdict（含 NotChecked）。"""
    claim_verdicts: list[str] = []
    has_critical = False
    for sec in sections:
        for iss in sec.get("logic_issues") or []:
            if not isinstance(iss, dict):
                continue
            if str(iss.get("severity") or "").lower() == "critical":
                has_critical = True
        for c in sec.get("main_claims") or []:
            if isinstance(c, dict):
                v = str(c.get("verdict") or "")
                if v:
                    claim_verdicts.append(v)
    if has_critical:
        return "Incorrect"
    if "Incorrect" in claim_verdicts:
        return "Incorrect"
    if "Partial" in claim_verdicts:
        return "Partial"
    if claim_verdicts and all(v == "Correct" for v in claim_verdicts):
        return "Correct"
    if claim_verdicts and all(v == "NotChecked" for v in claim_verdicts):
        return "NotChecked"
    if not claim_verdicts:
        return "NotChecked"
    return "Partial"


@dataclass
class SectionReviewFinalReport:
    """与 ReviewReport.summary_dict() 对齐的流式 final 负载。"""

    source: str
    overall_verdict: str
    issues: list[dict[str, Any]]
    stats: dict[str, Any]
    parse_failed: bool = False
    paper_title: str = ""
    parser_source: str = "nanonets"
    sections_reviewed: int = 0
    scan_completed: bool = False
    sections_detail: list[dict[str, Any]] = field(default_factory=list)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "overall_verdict": self.overall_verdict,
            "stats": self.stats,
            "issues": self.issues,
            "parse_failed": self.parse_failed,
            "parser_source": self.parser_source,
            "paper_title": self.paper_title,
            "sections_reviewed": self.sections_reviewed,
            "scan_completed": self.scan_completed,
            "mode": "nanonets_section",
        }


async def review_section_with_llm(
    section_title: str,
    section_body: str,
    *,
    model: Optional[str],
    lang: str,
) -> dict[str, Any]:
    """单章节结构化审查。"""
    m = model or DEFAULT_SECTION_MODEL
    user = (
        f"Section title: {section_title}\n\n"
        f"Section markdown:\n{_truncate(section_body, 28000)}\n\n"
        f"Return JSON with keys exactly as in this schema description:\n{SECTION_REVIEW_SCHEMA}"
    )
    system = SECTION_SYSTEM_PROMPT + lang_sys_suffix(lang if lang else None)
    raw = await chat_json(user, system=system, model=m, schema=SECTION_REVIEW_SCHEMA)
    if not isinstance(raw, dict):
        raw = {}
    raw.setdefault("section_title", section_title)
    raw.setdefault("page_range", "")
    raw.setdefault("main_claims", [])
    raw.setdefault("proofs_found", [])
    raw.setdefault("logic_issues", [])
    raw.setdefault("citation_issues", [])
    raw.setdefault("confidence", 0.5)
    raw.setdefault("source_quotes", [])
    return enforce_verdict_rules(raw)


async def run_pdf_nanonets_section_review(
    pdf_bytes: bytes,
    *,
    source: str,
    nanonets_api_key: str,
    progress: ProgressCb,
    result_cb: ResultCb,
    model: Optional[str],
    lang: str,
    max_sections: int = 48,
) -> SectionReviewFinalReport:
    """完整 PDF 流程：Nanonets → 切章 → 逐章 LLM。"""
    ncfg = nanonets_cfg()
    max_poll = float(ncfg.get("max_poll_seconds") or 900)
    poll_iv = float(ncfg.get("poll_interval_seconds") or 2)
    req_to = float(ncfg.get("request_timeout_seconds") or 120)

    await _emit_progress(progress, "nanonets", "正在通过 Nanonets OCR 解析 PDF…")

    ex = await extract_pdf_markdown_nanonets(
        pdf_bytes,
        api_key=nanonets_api_key,
        filename=source.split("/")[-1] or "document.pdf",
        httpx_timeout=req_to,
        poll_interval=poll_iv,
        max_poll_seconds=max_poll,
        include_hierarchy_json=True,
    )

    if not ex.ok or not (ex.markdown or "").strip():
        msg = ex.error_message or "Nanonets 解析失败"
        await _emit_progress(progress, "parse_failed", msg[:1200])
        issue = {
            "location": source,
            "issue_type": "parse_failed",
            "description": msg,
            "fix_suggestion": "检查 NANONETS_API_KEY / 网络 / PDF 是否损坏；查看 Nanonets 控制台任务状态。",
            "confidence": 1.0,
        }
        return SectionReviewFinalReport(
            source=source,
            overall_verdict="Incorrect",
            issues=[issue],
            stats={
                "parser_source": "nanonets",
                "nanonets_error_code": ex.error_code,
                "record_id": ex.record_id,
                "pages_processed": ex.pages_processed,
            },
            parse_failed=True,
            scan_completed=False,
        )

    md = ex.markdown
    await _emit_progress(progress, "nanonets_ok", f"Nanonets 解析完成（{len(md)} 字符）…")

    sections = split_major_sections(md)
    if len(sections) > max_sections:
        sections = sections[:max_sections]
        await _emit_progress(progress, "section_trim", f"章节数超过上限，仅审查前 {max_sections} 个大章节。")

    reviewed: list[dict[str, Any]] = []
    for idx, sec in enumerate(sections, start=1):
        title = sec["title"]
        body = sec["body"]
        await _emit_progress(progress, "section", f"正在结构化审查章节 {idx}/{len(sections)}：{title[:80]}")
        try:
            payload = await review_section_with_llm(title, body, model=model, lang=lang or "zh")
        except Exception as exc:  # noqa: BLE001
            logger.exception("section LLM failed for %s", title)
            payload = {
                "section_title": title,
                "page_range": "",
                "main_claims": [],
                "proofs_found": [],
                "logic_issues": [
                    {
                        "severity": "high",
                        "description": f"本章 LLM 审查失败：{type(exc).__name__}: {exc}",
                        "source_quote": "",
                    }
                ],
                "citation_issues": [],
                "confidence": 0.0,
                "source_quotes": [],
            }
        payload = enforce_verdict_rules(payload)
        await _emit(result_cb, {"kind": "section", "index": idx, "data": payload})
        reviewed.append(payload)

    paper_title = infer_paper_title(md, reviewed)
    overall = aggregate_overall_verdict(reviewed)
    stats = {
        "parser_source": "nanonets",
        "sections_checked": len(reviewed),
        "markdown_chars": len(md),
        "pages_processed": ex.pages_processed,
        "record_id": ex.record_id,
        "hierarchy_present": ex.hierarchy is not None,
    }
    return SectionReviewFinalReport(
        source=source,
        overall_verdict=overall,
        issues=[],
        stats=stats,
        parse_failed=False,
        paper_title=paper_title,
        parser_source="nanonets",
        sections_reviewed=len(reviewed),
        scan_completed=len(sections) <= max_sections,
        sections_detail=reviewed,
    )


def parse_nanonets_extract_mock_body(body: dict[str, Any]) -> NanonetsExtractResult:
    """测试用：从已解析的 API JSON 生成 NanonetsExtractResult（不发起网络）。"""
    ok = bool(body.get("success")) and str(body.get("status") or "") == "completed"
    md = ""
    if ok:
        res = body.get("result") or {}
        blk = res.get("markdown") or {}
        c = blk.get("content", "")
        md = c if isinstance(c, str) else str(c)
    return NanonetsExtractResult(
        ok=ok and bool(md.strip()),
        markdown=md,
        hierarchy=None,
        error_code="" if ok and md.strip() else "mock_not_completed",
        error_message=str(body.get("message") or ""),
        record_id=str(body.get("record_id") or ""),
        raw_status=str(body.get("status") or ""),
        pages_processed=int(body.get("pages_processed") or 0),
    )
