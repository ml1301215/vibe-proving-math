"""研究模式 Pipeline：论文审查 —— 自动化数学论文验证。

Pipeline：
  Step 1: 解析（parser.py）→ 提取定理-证明对
  Step 2: 逐步验证（verify_sequential）→ 标记每步 passed/gap/critical_error
  Step 3: 引用核查（TheoremSearch）→ verified/not_found/condition_mismatch
  Step 4: 反例搜索（对 uncertain 步骤）
  Step 5: 生成结构化审查报告

输出：ReviewReport（JSON + Markdown）
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

from modes.research.parser import (
    TheoremProofPair,
    parse_arxiv,
    _extract_tex_environments,
    _llm_extract_from_text,
    extract_statement_candidates_from_text,
    extract_statement_candidates_from_images,
)
from skills.verify_sequential import verify_sequential, VerificationResult
from skills.search_theorems import search_theorems, TheoremMatch
from skills.counterexamples import find_counterexample
from core.text_sanitize import ensure_inline_math, strip_non_math_latex, sanitize_dict
from core.llm import chat_json


# ── 流式回调协议（无破坏） ─────────────────────────────────────────────────
ProgressCb = Optional[Callable[[str, str], Awaitable[None]]]
"""(step, msg) → None  — 进度状态帧。"""

ResultCb = Optional[Callable[[dict], Awaitable[None]]]
"""partial review JSON → None  — 单个定理审查结果出炉时增量推送。"""


@dataclass
class PaperChunk:
    chunk_id: int
    page_start: int
    page_end: int
    text: str


@dataclass
class SectionUnit:
    unit_id: int
    section_title: str
    section_path: str
    page_start: int
    page_end: int
    raw_text: str
    context_before: str = ""
    context_after: str = ""
    local_definitions: list[str] = field(default_factory=list)
    local_citations: list[str] = field(default_factory=list)
    proof_excerpt: str = ""

    def page_span(self) -> str:
        return _format_page_span(self.page_start, self.page_end)

    def location_hint(self) -> str:
        page_span = self.page_span()
        if self.section_path and page_span:
            return f"{self.section_path} ({page_span})"
        return self.section_path or page_span


@dataclass
class StructuredDocument:
    source: str
    page_count: int
    sections: list[SectionUnit]


async def _emit(cb, *args) -> None:
    if cb is None:
        return
    try:
        await cb(*args)
    except Exception as exc:  # noqa: BLE001
        logger.debug("progress/result callback raised: %s", exc)

_CONFIDENCE_THRESHOLD = 0.5
_MAX_REVIEW_TEXT = 50_000
_MAX_PROOF_FALLBACK = 6_000
_PAPER_CHUNK_CHARS = 7_500
_SECTION_CHUNK_CHARS = 5_500
_SECTION_CONTEXT_CHARS = 1_200

_SECTION_HEADING_PATTERNS = [
    re.compile(r"^(?:\d+(?:\.\d+){0,3}|[IVXLC]+(?:\.\d+)?)\s+[A-Z][A-Za-z0-9 ,:;\-()]{2,120}$"),
    re.compile(r"^(?:abstract|introduction|preliminar(?:y|ies)|background|notation|main results?|proofs?|applications?|appendix|references)\b", re.IGNORECASE),
    re.compile(r"^(?:摘要|引言|预备知识|背景|记号|主要结果|证明|应用|附录|参考文献)\b"),
]

_FORMAL_CLAIM_LABEL_RE = re.compile(
    r"\b(theorem|lemma|proposition|corollary|claim|conjecture)\s+"
    r"\d+(?:\.\d+)*\b",
    re.IGNORECASE,
)
_NON_THEOREM_TITLE_RE = re.compile(
    r"^\s{0,3}#{0,6}\s*(abstract|references|bibliography|acknowledg(?:e)?ments|"
    r"introduction|contents|appendix|table|fig(?:ure)?\.?)\b",
    re.IGNORECASE,
)

_CITATION_PATTERNS = [
    r"\[REF\]",
    # 数字文献引用：[1]、[12]、[1,2]、[1-3]
    r"(\[\d+(?:[,\-]\d+)*\])",
    r"by\s+([A-Z][a-z]+(?:'s)?\s+(?:theorem|lemma|proposition|corollary))",
    r"((?:Theorem|Lemma|Proposition|Corollary)\s+[\d\.]+)",
    r"((?:定理|引理|命题|推论)\s*[\d\.一二三四五六七八九十]+)",
    r"\b([A-Z][a-z]+\s+et\s+al\.)",
    r"\b([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?\s*\(\d{4}\))",
    r"\b((?:Lemma|Proposition|Corollary|Claim)\s+\d+(?:\.\d+)?)\b",
]

_FALLBACK_STATEMENT = (
    "(用户未单独提供命题，请仅基于证明文本本身审查其逻辑自洽性、"
    "引用合理性与潜在漏洞；不要因为'缺少命题'判定 critical_error。)"
)
_STATEMENT_REVIEW_SCHEMA = {
    "overall": "has_gaps",
    "summary": "缺少足够证明细节，无法确认 `$|H| \\mid |G|$` 是否已被证明",
    "issues": [
        {
            "issue_type": "gap",
            "description": "未给出足够局部证明或论证支撑，无法推出 `$g \\in H$`",
            "fix_suggestion": "补充证明细节，并把关键数学对象写成 `$...$` 形式",
            "confidence": 0.72,
        }
    ],
}

_LATEX_STYLE_INSTRUCTION = (
    "When you mention any mathematical symbol, variable, formula, set, function, inequality, congruence, "
    "or relation in any JSON string field such as summary/description/fix_suggestion, wrap the mathematical "
    "part in inline LaTeX using `$...$`. "
    "Examples: `$G$`, `$H \\le G$`, `$|H| \\mid |G|$`, `$g \\in G$`, `$f: X \\to Y$`, `$a^{{p-1}} \\equiv 1 \\pmod p$`. "
    "Do not output bare Unicode math symbols like `∈`, `≤`, `⊂`, `≅`, `|G|` outside `$...$`. "
    "Use plain natural language outside math delimiters, and do not use Markdown formatting besides LaTeX math."
)


def _format_page_span(start_page: int, end_page: int) -> str:
    if start_page <= 0 and end_page <= 0:
        return ""
    if start_page == end_page:
        return f"page {start_page}"
    return f"pages {start_page}-{end_page}"


def _normalize_statement_key(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", cleaned)


def _is_reviewable_extracted_pair(pair: TheoremProofPair) -> bool:
    statement = (pair.statement or "").strip()
    normalized = re.sub(r"^\s{0,3}#{1,6}\s*", "", statement).strip(" *.:;-—–").lower()
    if not statement or len(normalized) < 12:
        return False
    if _NON_THEOREM_TITLE_RE.match(statement):
        return False
    if normalized in {"then", "hence", "thus", "therefore", "set", "moreover", "this gives", "proof", "we have"}:
        return False
    if re.match(r"^(?:then|hence|thus|therefore|set|suppose|assume|moreover|proof|note that|from\s+\(?\d|we have)\b", normalized, re.IGNORECASE):
        return False
    if statement.lstrip().startswith(("$$", "\\[")):
        return False
    has_label = bool(_FORMAL_CLAIM_LABEL_RE.search(statement) or _FORMAL_CLAIM_LABEL_RE.search(pair.ref or ""))
    has_math = bool(re.search(r"\$[^$\n]+\$|\\[a-zA-Z]+|[=<>≤≥∈∉⊂⊃∑∏∫]", statement))
    claim_start = bool(re.match(r"^(?:for every|for all|let|if|there exists|there is|given)\b", normalized, re.IGNORECASE))
    if pair.env_type == "section" and not has_label:
        return False
    return has_label or (has_math and claim_start and len(normalized.split()) >= 8)


def _sanitize_review_text(text: str) -> str:
    normalized = re.sub(r"`([^`\n]+)`", r"\1", str(text or ""))
    return strip_non_math_latex(ensure_inline_math(normalized))


def _review_confidence_from_review(review: "TheoremReview") -> float:
    if review.verdict == "Incorrect":
        return 0.15
    if review.verdict == "Partial":
        if review.issues:
            avg_issue_conf = sum(max(0.0, min(i.confidence, 1.0)) for i in review.issues) / max(len(review.issues), 1)
            return round(max(0.2, 1.0 - avg_issue_conf * 0.6), 2)
        return 0.45
    if review.verification and review.verification.overall == "passed":
        return 0.92
    if review.verification and review.verification.overall == "has_gaps":
        return 0.45
    return 0.78


def _truncate_preserving_math(text: str, *, max_chars: int = 96) -> str:
    normalized = _normalize_whitespace(text)
    if len(normalized) <= max_chars:
        return normalized
    clipped = normalized[:max_chars]
    if clipped.count("$") % 2 == 1:
        clipped = clipped.rsplit("$", 1)[0]
    return clipped.rstrip(" ,;:，；：") + "…"


def _display_theorem_name(tp: TheoremProofPair) -> str:
    ref = _normalize_whitespace(tp.ref or "")
    statement = _normalize_whitespace(tp.statement or "")
    generic_ref = bool(re.fullmatch(r"(?:theorem|lemma|proposition|corollary|claim|definition|remark|定理|引理|命题|推论|断言)\s*[\d\.一二三四五六七八九十]*", ref, re.IGNORECASE))
    if statement:
        first_clause = re.split(r"[。！？!?；;]", statement, maxsplit=1)[0].strip() or statement
        snippet = _truncate_preserving_math(first_clause, max_chars=96)
        if generic_ref and snippet:
            return f"{ref}: {snippet}" if ref else snippet
        if snippet:
            return snippet
    if ref:
        return ref
    return _truncate_preserving_math(tp.statement or f"{tp.env_type} theorem", max_chars=96)


def _split_long_page(page_text: str, *, max_chars: int = _PAPER_CHUNK_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", page_text or "") if p.strip()]
    if not paragraphs:
        paragraphs = [page_text.strip()] if (page_text or "").strip() else []

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(para) > max_chars:
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        current = para
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def build_paper_chunks(page_texts: list[str], *, max_chars: int = _PAPER_CHUNK_CHARS) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    chunk_id = 1
    for page_idx, page_text in enumerate(page_texts, start=1):
        cleaned = (page_text or "").strip()
        if not cleaned:
            continue
        for segment in _split_long_page(cleaned, max_chars=max_chars):
            chunks.append(PaperChunk(
                chunk_id=chunk_id,
                page_start=page_idx,
                page_end=page_idx,
                text=segment,
            ))
            chunk_id += 1
    return chunks


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _short_excerpt(text: str, *, max_chars: int = 220) -> str:
    cleaned = _normalize_whitespace(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def _is_running_header_or_footer(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return True
    if re.fullmatch(r"(?:page\s+)?\d{1,4}", lowered):
        return True
    if re.fullmatch(r"[ivxlcdm]{1,8}", lowered):
        return True
    if re.fullmatch(r"[A-Z]{1,8}", line.strip()):
        return True
    if any(token in lowered for token in ("arxiv", "doi", "http://", "https://", "email", "e-mail", "received", "accepted")):
        return True
    return False


def _clean_section_title(text: str) -> str:
    title = _normalize_whitespace(text)
    title = re.sub(r"\s*[·|]\s*part\s+\d+\s*$", "", title, flags=re.IGNORECASE)
    title = title.strip(" -:;,.|")
    if not title or _is_running_header_or_footer(title):
        return ""
    if len(title) > 90:
        return ""
    if sum(ch in title for ch in "。！？；;，,") >= 2:
        return ""
    return title


def _looks_like_section_heading(line: str) -> bool:
    candidate = _clean_section_title(line)
    if not candidate:
        return False
    if any(pat.match(candidate) for pat in _SECTION_HEADING_PATTERNS):
        return True
    if candidate.endswith((".", "?", "!", "。", "？", "！", ":")):
        return False
    if re.search(r"(?:theorem|lemma|proposition|corollary|claim|proof|定理|引理|命题|推论|证明)\s+\d", candidate, re.IGNORECASE):
        return False
    words = candidate.split()
    if 0 < len(words) <= 8 and sum(w[:1].isupper() for w in words if w[:1].isalpha()) >= max(1, len(words) - 1):
        return True
    if re.fullmatch(r"(?:\d+(?:\.\d+){0,3}\s+)?[\u4e00-\u9fffA-Z0-9 ()\-]{2,40}", candidate):
        return True
    return False


def _split_heading_from_paragraph(paragraph: str) -> tuple[str | None, str]:
    raw_lines = [line.strip() for line in re.split(r"\r?\n+", paragraph or "") if line.strip()]
    if not raw_lines:
        return None, ""
    for idx, line in enumerate(raw_lines[:3]):
        if _looks_like_section_heading(line):
            heading = _clean_section_title(line)
            remainder = "\n".join(raw_lines[idx + 1:]).strip()
            return heading, remainder
    return None, paragraph.strip()


def _infer_section_title(paragraph: str, index: int) -> str:
    heading, remainder = _split_heading_from_paragraph(paragraph)
    if heading:
        return heading
    line = _normalize_whitespace((remainder or paragraph).split("\n", 1)[0])
    lowered = line.lower()
    if lowered.startswith(("theorem", "lemma", "proposition", "corollary", "claim", "proof")):
        return _short_excerpt(line, max_chars=80)
    if line.startswith(("定理", "引理", "命题", "推论", "证明")):
        return _short_excerpt(line, max_chars=80)
    return f"section {index}"


def _split_page_paragraphs(page_texts: list[str]) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    for page_idx, page_text in enumerate(page_texts, start=1):
        cleaned = (page_text or "").strip()
        if not cleaned:
            continue
        parts = [p.strip() for p in re.split(r"\n\s*\n+", cleaned) if p.strip()]
        if not parts:
            parts = [cleaned]
        for para in parts:
            paragraphs.append((page_idx, para))
    return paragraphs


def _split_section_group(
    paragraphs: list[tuple[int, str]],
    *,
    max_chars: int = _SECTION_CHUNK_CHARS,
) -> list[list[tuple[int, str]]]:
    groups: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_chars = 0
    for page_num, para in paragraphs:
        para_len = len(para)
        projected = current_chars + para_len + (2 if current else 0)
        if current and projected > max_chars:
            groups.append(current)
            current = []
            current_chars = 0
        current.append((page_num, para))
        current_chars += para_len + (2 if current_chars else 0)
    if current:
        groups.append(current)
    return groups


def _collect_local_definitions(text: str) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()
    for para in re.split(r"\n\s*\n+", text or ""):
        raw = para.strip()
        if not raw:
            continue
        lowered = raw.lower()
        if any(token in lowered for token in ("definition", "notation", "denote", "let ", "suppose", "assume")) or any(
            token in raw for token in ("定义", "记号", "记作", "记为", "设", "令", "假设")
        ):
            excerpt = _short_excerpt(raw, max_chars=260)
            if excerpt and excerpt not in seen:
                seen.add(excerpt)
                snippets.append(excerpt)
        if len(snippets) >= 4:
            break
    return snippets


def _extract_citation_terms(text: str, *, limit: int = 12) -> list[str]:
    cited_terms: list[str] = []
    seen: set[str] = set()
    for pat in _CITATION_PATTERNS:
        for m in re.finditer(pat, text or "", re.IGNORECASE):
            term = (m.group(1) if m.groups() else m.group(0)).strip()
            key = term.lower()
            # 允许 [1] 等短引用；过滤单字符噪声
            if len(term) >= 2 and key not in seen:
                seen.add(key)
                cited_terms.append(term)
            if len(cited_terms) >= limit:
                return cited_terms
    return cited_terms


def _extract_proof_excerpt(text: str, *, max_chars: int = 2200) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    match = re.search(r"(?:^|\n)(proof[\s:\.-]|证明[\s：:])", cleaned, re.IGNORECASE)
    if match:
        proof = cleaned[match.start():].strip()
        return proof[:max_chars]
    lowered = cleaned.lower()
    proof_hints = (
        "therefore", "thus", "hence", "consider", "let ", "suppose", "assume",
        "involution", "fixed point", "contradiction", "we have", "it follows",
        "因此", "于是", "从而", "考虑", "设", "假设", "反证", "不动点",
    )
    if any(hint in lowered for hint in proof_hints) and len(cleaned) > 100:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", cleaned) if p.strip()]
        if len(paragraphs) >= 2:
            tail = "\n\n".join(paragraphs[1:]).strip()
            if len(tail) >= 40:
                return tail[:max_chars]
    return ""


def build_structured_document(
    page_texts: list[str],
    *,
    source: str,
    max_chars: int = _SECTION_CHUNK_CHARS,
) -> StructuredDocument:
    paragraphs = _split_page_paragraphs(page_texts)
    if not paragraphs:
        return StructuredDocument(source=source, page_count=0, sections=[])

    sections: list[SectionUnit] = []
    current_title = ""
    current_paragraphs: list[tuple[int, str]] = []
    section_index = 0
    unit_id = 1

    def _flush_current() -> None:
        nonlocal current_title, current_paragraphs, section_index, unit_id
        if not current_paragraphs:
            current_title = ""
            return
        section_index += 1
        base_title = _clean_section_title(current_title) or _infer_section_title(current_paragraphs[0][1], section_index)
        groups = _split_section_group(current_paragraphs, max_chars=max_chars)
        for part_idx, group in enumerate(groups, start=1):
            raw_text = "\n\n".join(para for _, para in group).strip()
            if not raw_text:
                continue
            path = base_title if len(groups) == 1 else f"{base_title} · part {part_idx}"
            sections.append(SectionUnit(
                unit_id=unit_id,
                section_title=base_title,
                section_path=path,
                page_start=group[0][0],
                page_end=group[-1][0],
                raw_text=raw_text,
                local_definitions=_collect_local_definitions(raw_text),
                local_citations=_extract_citation_terms(raw_text),
                proof_excerpt=_extract_proof_excerpt(raw_text),
            ))
            unit_id += 1
        current_title = ""
        current_paragraphs = []

    last_page_num: Optional[int] = None
    for page_num, para in paragraphs:
        if last_page_num is not None and page_num != last_page_num and current_paragraphs and not current_title:
            _flush_current()
        heading, remainder = _split_heading_from_paragraph(para)
        if heading:
            _flush_current()
            current_title = heading
            if remainder:
                current_paragraphs.append((page_num, remainder))
            last_page_num = page_num
            continue
        current_paragraphs.append((page_num, para))
        last_page_num = page_num
    _flush_current()

    for idx, section in enumerate(sections):
        before = ""
        after = ""
        if idx > 0:
            prev = sections[idx - 1]
            before = f"{prev.section_title}\n{prev.raw_text[-_SECTION_CONTEXT_CHARS:]}".strip()
        if idx + 1 < len(sections):
            nxt = sections[idx + 1]
            after = f"{nxt.section_title}\n{nxt.raw_text[:_SECTION_CONTEXT_CHARS]}".strip()
        section.context_before = before
        section.context_after = after

    return StructuredDocument(
        source=source,
        page_count=len([p for p in page_texts if (p or "").strip()]),
        sections=sections,
    )


def _build_claim_context(tp: TheoremProofPair) -> str:
    blocks: list[str] = []
    if tp.section_title:
        blocks.append(f"Section: {tp.section_title}")
    if tp.section_path and tp.section_path != tp.section_title:
        blocks.append(f"Section path: {tp.section_path}")
    if tp.location_hint:
        blocks.append(f"Location: {tp.location_hint}")
    if tp.local_definitions:
        blocks.append("Local definitions:\n" + "\n".join(f"- {x}" for x in tp.local_definitions[:4]))
    if tp.local_citations:
        blocks.append("Local citation hints:\n" + "\n".join(f"- {x}" for x in tp.local_citations[:6]))
    if tp.context_before:
        blocks.append(f"Previous context:\n{tp.context_before[-_SECTION_CONTEXT_CHARS:]}")
    if tp.context_excerpt:
        blocks.append(f"Current section excerpt:\n{tp.context_excerpt[:2500]}")
    if tp.proof:
        blocks.append(f"Recovered proof snippet:\n{tp.proof[:2200]}")
    if tp.context_after:
        blocks.append(f"Next context:\n{tp.context_after[:_SECTION_CONTEXT_CHARS]}")
    return "\n\n".join(blocks).strip()


def _recover_proof_from_pair(tp: TheoremProofPair) -> Optional[str]:
    if tp.has_proof():
        return tp.proof
    candidates = [
        tp.proof or "",
        tp.context_excerpt or "",
        tp.context_after or "",
        "\n\n".join(part for part in [tp.context_excerpt or "", tp.context_after or ""] if part),
    ]
    for text in candidates:
        recovered = _extract_proof_excerpt(text)
        if recovered and len(recovered.strip()) > 20:
            return recovered
    return None


def _section_index(document: StructuredDocument, unit: SectionUnit) -> int:
    for idx, candidate in enumerate(document.sections):
        if candidate.unit_id == unit.unit_id:
            return idx
    return -1


def collect_definitional_context(unit: SectionUnit, document: StructuredDocument) -> list[str]:
    items: list[str] = []
    idx = _section_index(document, unit)
    for section in ([unit] + list(reversed(document.sections[:idx]))) if idx >= 0 else [unit]:
        for definition in section.local_definitions:
            if definition not in items:
                items.append(definition)
            if len(items) >= 6:
                return items
    return items


def collect_neighbor_context(unit: SectionUnit, document: StructuredDocument) -> tuple[str, str]:
    idx = _section_index(document, unit)
    if idx < 0:
        return unit.context_before, unit.context_after
    before = unit.context_before
    after = unit.context_after
    if not before and idx > 0:
        prev = document.sections[idx - 1]
        before = f"{prev.section_title}\n{prev.raw_text[-_SECTION_CONTEXT_CHARS:]}".strip()
    if not after and idx + 1 < len(document.sections):
        nxt = document.sections[idx + 1]
        after = f"{nxt.section_title}\n{nxt.raw_text[:_SECTION_CONTEXT_CHARS]}".strip()
    return before, after


def collect_local_citation_map(unit: SectionUnit) -> list[str]:
    return list(dict.fromkeys(unit.local_citations))


def resolve_cross_references(unit: SectionUnit, document: StructuredDocument) -> list[str]:
    combined_text = "\n".join(part for part in (unit.raw_text, unit.context_before, unit.context_after) if part)
    resolved = list(dict.fromkeys([*collect_local_citation_map(unit), *_extract_citation_terms(combined_text, limit=8)]))
    idx = _section_index(document, unit)
    if idx < 0:
        return resolved
    current_text = unit.raw_text
    for prev in reversed(document.sections[:idx]):
        for citation in prev.local_citations:
            if citation in current_text and citation not in resolved:
                resolved.append(citation)
        if len(resolved) >= 8:
            break
    return resolved


def _enrich_pair_from_section(
    pair: TheoremProofPair,
    section: SectionUnit,
    *,
    document: Optional[StructuredDocument] = None,
) -> TheoremProofPair:
    pair.section_title = section.section_title
    pair.section_path = section.section_path
    if document is not None:
        before, after = collect_neighbor_context(section, document)
        pair.context_before = before
        pair.context_after = after
        pair.local_citations = list(dict.fromkeys([*pair.local_citations, *resolve_cross_references(section, document)]))
        pair.local_definitions = list(dict.fromkeys([*pair.local_definitions, *collect_definitional_context(section, document)]))
    else:
        pair.context_before = section.context_before
        pair.context_after = section.context_after
        pair.local_citations = list(dict.fromkeys([*pair.local_citations, *section.local_citations]))
        pair.local_definitions = list(dict.fromkeys([*pair.local_definitions, *section.local_definitions]))
    pair.page_span = section.page_span()
    pair.location_hint = section.location_hint()
    pair.context_excerpt = pair.context_excerpt or section.raw_text[:3000]
    if not pair.proof and section.proof_excerpt:
        pair.proof = section.proof_excerpt
    return pair


def enrich_pair_from_section(
    pair: TheoremProofPair,
    section: SectionUnit,
    *,
    document: Optional[StructuredDocument] = None,
) -> TheoremProofPair:
    """公开给 agent/tool 层复用的 section 上下文增强入口。"""
    return _enrich_pair_from_section(pair, section, document=document)


async def _review_statement_without_proof(tp: TheoremProofPair) -> tuple[VerificationResult, list[IssueReport]]:
    """对缺少显式证明的 statement 做保守型 LLM 审查。"""
    context = (_build_claim_context(tp) or tp.context_excerpt or tp.statement or "")[:4000]
    proof_snippet = _recover_proof_from_pair(tp) or ""
    location = tp.location_hint or tp.source or "paper"
    prompt = (
        f"Source: {tp.source}\n"
        f"Location: {location}\n"
        f"Section: {tp.section_title or tp.section_path or 'N/A'}\n"
        f"Statement: {tp.statement}\n\n"
        f"Recovered proof snippet:\n{proof_snippet[:2200] or 'N/A'}\n\n"
        f"Local context:\n{context}\n\n"
        "Review this extracted mathematical statement conservatively. "
        "If any inference step cannot be verified from the given context alone, you MUST emit issue_type='gap' "
        "(do not assume it is correct by default). "
        "If the local context does not contain enough proof detail, prefer issue_type='gap' instead of claiming correctness. "
        "Do not treat missing lemmas, unstated hypotheses, or skipped algebraic steps as acceptable unless they are explicit in the text. "
        f"{_LATEX_STYLE_INSTRUCTION} "
        "Return JSON only."
    )

    try:
        data = await chat_json(
            prompt,
            system=(
                "You are a strict mathematical paper reviewer. "
                "Assess whether the extracted statement is justified by the local context; when in doubt, report a gap. "
                f"{_LATEX_STYLE_INSTRUCTION}"
            ),
            schema=_STATEMENT_REVIEW_SCHEMA,
        )
    except Exception as exc:
        data = {
            "overall": "has_gaps",
            "summary": f"statement review failed: {exc}",
            "issues": [{
                "issue_type": "gap",
                "description": "局部 statement 审查失败，无法确认该命题是否得到支撑",
                "fix_suggestion": "补充更完整的证明上下文后重试",
                "confidence": 0.4,
            }],
        }

    issue_dicts = data.get("issues") or []
    issues: list[IssueReport] = []
    verdict = "passed"
    for idx, item in enumerate(issue_dicts, start=1):
        if not isinstance(item, dict):
            continue  # 跳过非 dict 元素，防止 item.get() AttributeError
        issue_type = item.get("issue_type", "gap")
        if issue_type not in {"gap", "critical_error", "citation_not_found"}:
            issue_type = "gap"
        confidence = item.get("confidence", 0.6)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.6
        issues.append(IssueReport(
            location=f"{location}, statement",
            issue_type=issue_type,
            description=str(item.get("description", "")).strip() or "该命题缺少足够局部支撑",
            fix_suggestion=str(item.get("fix_suggestion", "")).strip() or "补充证明或更完整的上下文",
            confidence=max(0.0, min(confidence, 1.0)),
        ))
        if issue_type == "critical_error":
            verdict = "critical_error"
        elif verdict != "critical_error":
            verdict = "gap"

    summary = str(data.get("summary", "")).strip()
    verification = VerificationResult(
        steps=[],
        overall=data.get("overall", "has_gaps") if issues else "passed",
        summary=summary or ("该命题缺少显式证明，已按局部上下文保守审查" if issues else "statement looks locally consistent"),
        theorem_search_results=[],
    )
    if not issues:
        verification.overall = "passed"
    elif verdict == "critical_error":
        verification.overall = "critical_error"
    else:
        verification.overall = "has_gaps"
    return verification, issues


@dataclass
class IssueReport:
    """单个问题报告。"""
    location: str      # "Theorem 1, Step 3"
    issue_type: str    # "gap" | "critical_error" | "citation_not_found" | "condition_mismatch"
    description: str
    fix_suggestion: str
    confidence: float  # 对此问题的置信度

    def to_dict(self) -> dict:
        return {
            "location": _sanitize_review_text(self.location),
            "issue_type": self.issue_type,
            "description": _sanitize_review_text(self.description),
            "fix_suggestion": _sanitize_review_text(self.fix_suggestion),
            "confidence": self.confidence,
        }


@dataclass
class TheoremReview:
    """单个定理的审查结果。"""
    theorem: TheoremProofPair
    verification: Optional[VerificationResult]
    citation_checks: list[dict]
    issues: list[IssueReport]
    verdict: str  # "Correct" | "Partial" | "Incorrect"

    def to_dict(self) -> dict:
        raw_name = _display_theorem_name(self.theorem)
        return {
            "theorem_name": _sanitize_review_text(raw_name),
            "theorem_ref": self.theorem.ref,
            "theorem_type": self.theorem.env_type,
            "location_hint": _sanitize_review_text(self.theorem.location_hint or ""),
            "page_span": _sanitize_review_text(self.theorem.page_span or ""),
            "section_title": _sanitize_review_text(self.theorem.section_title or ""),
            "section_path": _sanitize_review_text(self.theorem.section_path or ""),
            "claim_kind": _sanitize_review_text(self.theorem.claim_kind or ""),
            "parser_source": _sanitize_review_text(self.theorem.parser_source or ""),
            "quality_score": self.theorem.quality_score,
            "review_confidence": self.theorem.review_confidence,
            "statement": _sanitize_review_text(_truncate_preserving_math(self.theorem.statement, max_chars=2000)),
            "proof": _sanitize_review_text(_truncate_preserving_math(self.theorem.proof or "", max_chars=3000)),
            "verdict": self.verdict,
            "issues": [i.to_dict() for i in self.issues],
            "citation_checks": [
                {
                    **check,
                    "citation": _sanitize_review_text(check.get("citation", "")),
                    "matched": _sanitize_review_text(check.get("matched", "")),
                }
                for check in sanitize_dict(self.citation_checks, ("citation", "matched"))
            ],
            "proof_steps": (
                [
                    {
                        "step": s.step_num,
                        "verdict": s.verdict,
                        "reason": _sanitize_review_text(s.reason),
                        "text": _sanitize_review_text(getattr(s, "text", "") or ""),
                    }
                    for s in self.verification.steps
                ]
                if self.verification and self.verification.steps else []
            ),
            "verification_overall": self.verification.overall if self.verification else "not_checked",
            "unit_summary": _sanitize_review_text(self.verification.summary if self.verification else ""),
        }


@dataclass
class ReviewReport:
    """完整的论文审查报告。"""
    source: str
    overall_verdict: str  # "Correct" | "Partial" | "Incorrect"
    theorem_reviews: list[TheoremReview]
    issues: list[IssueReport]
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "overall_verdict": self.overall_verdict,
            "stats": self.stats,
            "issues": [i.to_dict() for i in self.issues],
            "theorem_reviews": [r.to_dict() for r in self.theorem_reviews],
        }

    def summary_dict(self) -> dict:
        """流式 final 帧用：仅整体 verdict + stats + 全部 issues，不含 theorem_reviews
        （定理卡片已经按 vp-result 帧增量送达，避免重复传输）。"""
        return {
            "source": self.source,
            "overall_verdict": self.overall_verdict,
            "stats": self.stats,
            "issues": [i.to_dict() for i in self.issues],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 论文审查报告：{self.source}",
            f"\n**总体评判：{self.overall_verdict}**\n",
            f"- 审查定理数：{self.stats.get('theorems_checked', 0)}",
            f"- 发现问题数：{len(self.issues)}",
            f"- 引用核查数：{self.stats.get('citations_checked', 0)}",
            "",
        ]

        if self.issues:
            lines.append("## 发现的问题\n")
            for i, issue in enumerate(self.issues, 1):
                lines.append(f"### 问题 {i}：{issue.issue_type}")
                lines.append(f"**位置：** {issue.location}")
                lines.append(f"**描述：** {issue.description}")
                lines.append(f"**修复建议：** {issue.fix_suggestion}")
                lines.append(f"**置信度：** {issue.confidence:.0%}")
                lines.append("")

        lines.append("## 逐定理审查\n")
        for r in self.theorem_reviews:
            ref = r.theorem.ref or r.theorem.env_type
            lines.append(f"### {ref} — {r.verdict}")
            if r.issues:
                for iss in r.issues:
                    lines.append(f"- [{iss.issue_type}] {iss.description}")
            else:
                lines.append("- 无问题")
            lines.append("")

        return "\n".join(lines)


def _determine_verdict(issues: list[IssueReport]) -> str:
    """规范化为 3 值枚举：Correct / Partial / Incorrect。

    - 无 issue → Correct
    - 仅有 gap/citation_not_found/verification_error → Partial（验证失败不能当 Correct）
    - 有 critical_error 或 parse_failed → Incorrect
    """
    critical = sum(1 for i in issues if i.issue_type in ("critical_error", "parse_failed"))
    gaps = sum(1 for i in issues if i.issue_type in ("gap", "citation_not_found", "verification_error"))
    if critical > 0:
        return "Incorrect"
    if gaps > 0:
        return "Partial"
    return "Correct"


async def _check_citations_in_proof(proof_text: Optional[str], *, extra_terms: Optional[list[str]] = None) -> list[dict]:
    """提取证明中的引用并用 TheoremSearch 核查。"""
    if not proof_text and not extra_terms:
        return []

    cited_terms = set(_extract_citation_terms(proof_text or "", limit=14))
    for term in extra_terms or []:
        if isinstance(term, str) and len(term.strip()) >= 2:
            cited_terms.add(term.strip())

    results = []
    for term in list(cited_terms)[:10]:  # 最多核查 10 条
        try:
            hits = await search_theorems(term, top_k=3, min_sim=0.3)
            if hits:
                status = "verified" if hits[0].similarity >= 0.5 else "not_found"
                results.append({
                    "citation": term,
                    "status": status,
                    "matched": hits[0].name if hits else None,
                    "similarity": hits[0].similarity if hits else 0.0,
                })
            else:
                results.append({"citation": term, "status": "not_found", "matched": None, "similarity": 0.0})
        except Exception as e:
            logger.debug("citation check failed for %r: %s: %s", term, type(e).__name__, e)
    return results


async def _review_single_theorem(
    tp: TheoremProofPair,
    idx: int,
    *,
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
) -> TheoremReview:
    """审查单个定理-证明对。

    check_logic: 是否进行逻辑漏洞审查（逐步验证）
    check_citations: 是否核查定理引用
    check_symbols: 是否检查符号一致性（目前合并在逐步验证中）
    """
    issues: list[IssueReport] = []
    recovered_proof = _recover_proof_from_pair(tp)
    if recovered_proof and not tp.has_proof():
        tp.proof = recovered_proof
    location_prefix = f"{tp.env_type.capitalize()} {idx}"
    if tp.ref:
        location_prefix += f" ({tp.ref})"
    if tp.location_hint:
        location_prefix += f" @ {tp.location_hint}"

    # 逐步验证（包含逻辑漏洞 + 符号一致性）
    verify_result: Optional[VerificationResult] = None
    if check_logic and tp.has_proof():
        try:
            verify_result = await verify_sequential(
                tp.proof,
                tp.statement,
                context_text=_build_claim_context(tp),
                section_title=tp.section_title or tp.section_path or "",
                local_citations=tp.local_citations,
                local_definitions=tp.local_definitions,
            )

            for step in (verify_result.steps or []):
                if step.verdict in ("gap", "critical_error"):
                    issues.append(IssueReport(
                        location=f"{location_prefix}, Step {step.step_num}",
                        issue_type=step.verdict,
                        description=step.reason,
                        fix_suggestion=(
                            f"Provide justification for: {step.text[:100]}"
                            if step.verdict == "gap"
                            else f"Correct the logical error: {step.reason[:100]}"
                        ),
                        confidence=0.75,
                    ))
        except Exception as e:
            logger.debug("_review_single_theorem verify failed for %s: %s", location_prefix, e)
            issues.append(IssueReport(
                location=location_prefix,
                issue_type="verification_error",
                description=f"步骤验证调用失败，无法确认证明正确性: {e}",
                fix_suggestion="请检查证明步骤格式是否符合预期",
                confidence=0.5,
            ))
    elif check_logic:
        verify_result, statement_issues = await _review_statement_without_proof(tp)
        issues.extend(statement_issues)

    # 引用核查
    citation_checks = []
    if check_citations:
        citation_checks = await _check_citations_in_proof(
            tp.proof or tp.statement,
            extra_terms=tp.local_citations,
        )
        for check in citation_checks:
            if check["status"] == "not_found":
                issues.append(IssueReport(
                    location=f"{location_prefix}, citation",
                    issue_type="citation_not_found",
                    description=f"引用 '{check['citation']}' 无法在 TheoremSearch 中找到",
                    fix_suggestion="核实引用是否正确，或提供完整引用信息",
                    confidence=0.6,
                ))

    verdict = _determine_verdict(issues)

    return TheoremReview(
        theorem=tp,
        verification=verify_result,
        citation_checks=citation_checks,
        issues=issues,
        verdict=verdict,
    )


async def review_claim(
    tp: TheoremProofPair,
    idx: int,
    *,
    claim_kind: str = "core_result",
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
) -> TheoremReview:
    """公开 claim 审查入口，供 agent 根据 claim 类型选择策略。"""
    kind = (claim_kind or tp.claim_kind or "core_result").strip().lower()
    strategy_logic = check_logic
    strategy_citations = check_citations

    if kind in {"background_fact", "citation_only"}:
        strategy_logic = False
        strategy_citations = True
    elif kind == "supporting_lemma":
        strategy_logic = check_logic
        strategy_citations = check_citations

    review = await _review_single_theorem(
        tp,
        idx,
        check_logic=strategy_logic,
        check_citations=strategy_citations,
        check_symbols=check_symbols,
    )
    review.theorem.claim_kind = tp.claim_kind or claim_kind
    review.theorem.review_confidence = _review_confidence_from_review(review)
    return review


async def review_arxiv(arxiv_id: str, *, max_theorems: int = 8) -> ReviewReport:
    """
    审查指定 arXiv 论文。

    max_theorems: 最多审查前 N 个定理-证明对（控制 token 消耗）
    """
    # 解析论文
    pairs = await parse_arxiv(arxiv_id)

    if not pairs:
        # 没有提取到结构化定理-证明对（如非定理类论文）：
        # 回退为"高层综述式审查"——verdict 用 "Partial"，并给出可操作的文字反馈。
        return ReviewReport(
            source=arxiv_id,
            overall_verdict="Partial",
            theorem_reviews=[],
            issues=[IssueReport(
                location="Parser",
                issue_type="parse_failed",
                description=(
                    "未能从论文中提取标准的 \\begin{theorem}/\\begin{lemma} 等定理-证明环境。"
                    "这通常意味着该论文是非数学类或纯 narrative 类工作，无法做逐命题核查。"
                ),
                fix_suggestion=(
                    "如需深度数学审查请确认论文确为定理类工作；或手动通过 tex_content 提交局部片段。"
                ),
                confidence=0.85,
            )],
            stats={"theorems_parsed": 0, "theorems_checked": 0, "citations_checked": 0},
        )

    # 只审查有证明的 pairs，最多 max_theorems 个
    to_review = [p for p in pairs if p.has_proof()][:max_theorems]
    if not to_review:
        # 若没有 pairs 有证明，取前几个（statement 审查）
        to_review = pairs[:max_theorems]

    # 并行审查（最多 3 个并行）
    semaphore = asyncio.Semaphore(3)

    async def _limited_review(tp, idx):
        async with semaphore:
            return await _review_single_theorem(tp, idx)

    reviews = await asyncio.gather(*[
        _limited_review(tp, i + 1) for i, tp in enumerate(to_review)
    ])

    all_issues = [issue for r in reviews for issue in r.issues]
    overall_verdict = _determine_verdict(all_issues)
    total_citations = sum(len(r.citation_checks) for r in reviews)

    return ReviewReport(
        source=arxiv_id,
        overall_verdict=overall_verdict,
        theorem_reviews=list(reviews),
        issues=all_issues,
        stats={
            "theorems_parsed": len(pairs),
            "theorems_checked": len(to_review),
            "citations_checked": total_citations,
            "issues_found": len(all_issues),
        },
    )


async def review_text(
    text: str,
    *,
    source: str = "inline",
    max_theorems: int = 8,
    progress: ProgressCb = None,
    result_cb: ResultCb = None,
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
    lang: str = "zh",
) -> ReviewReport:
    """
    审查用户直接提交的证明文本（替代 arXiv 入口）。

    自动三级降级：
      1. 先用 _extract_tex_environments 抽取 \\begin{theorem}/\\begin{proof} 结构 → 多定理拆解
      2. 0 命中 → 调 LLM 兜底解析（_llm_extract_from_text）
      3. 仍 0 命中 → **单证明降级**：把整段文本视为一个证明，配占位 statement，
         交给 _review_single_theorem 做逐步审查 + 引用核查

    入参限制：
      text: 非空；过长截断到 _MAX_REVIEW_TEXT (50000)

    可选回调（流式接入用）：
      progress(step, msg)   ：阶段状态帧（parse / parse_llm / fallback / review / theorem / done）
      result_cb(payload)    ：单个 TheoremReview 完成时增量推送 dict
    """
    if not text or not text.strip():
        raise ValueError("证明文本不能为空")

    cleaned = text.strip()
    if len(cleaned) > _MAX_REVIEW_TEXT:
        logger.info(
            "review_text input too long (%d chars), truncating to %d",
            len(cleaned), _MAX_REVIEW_TEXT,
        )
        cleaned = cleaned[:_MAX_REVIEW_TEXT]

    parse_msg = "正在解析输入文本…" if lang == "zh" else "Parsing input text..."
    await _emit(progress, "parse", parse_msg)

    # 路径 1：结构化抽取
    pairs: list[TheoremProofPair] = _extract_tex_environments(cleaned, source=source)

    # 路径 2：LLM 兜底（静默，不向用户暴露内部步骤）
    if not pairs:
        try:
            pairs = await _llm_extract_from_text(cleaned, source=source, lang=lang)
        except Exception as exc:
            logger.warning("review_text: LLM extract failed: %s: %s", type(exc).__name__, exc)
            pairs = []

    # 路径 3：单证明降级（整段文本视为一段证明）
    if not pairs:
        await _emit(progress, "fallback", "正在审查证明…")
        proof_body = cleaned[:_MAX_PROOF_FALLBACK]
        single = TheoremProofPair(
            env_type="proof",
            ref=None,
            statement=_FALLBACK_STATEMENT,
            proof=proof_body,
            source=source,
        )
        await _emit(progress, "theorem", "审查证明 1/1…")
        review = await _review_single_theorem(
            single, 1,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )
        await _emit(result_cb, {"kind": "theorem", "index": 1, "data": review.to_dict()})
        all_issues = list(review.issues)
        await _emit(progress, "done", "审查完成")
        return ReviewReport(
            source=source,
            overall_verdict=_determine_verdict(all_issues),
            theorem_reviews=[review],
            issues=all_issues,
            stats={
                "theorems_parsed": 0,
                "theorems_checked": 1,
                "citations_checked": len(review.citation_checks),
                "issues_found": len(all_issues),
                "fallback": "single_proof",
            },
        )

    # 多定理路径
    to_review = [p for p in pairs if p.has_proof()][:max_theorems]
    if not to_review:
        to_review = pairs[:max_theorems]

    total = len(to_review)
    await _emit(progress, "review", f"识别出 {total} 个定理，开始审查…")
    semaphore = asyncio.Semaphore(3)

    async def _limited_review(tp, idx):
        async with semaphore:
            await _emit(progress, "theorem", f"审查定理 {idx}/{total}…")
            r = await _review_single_theorem(
                tp, idx,
                check_logic=check_logic,
                check_citations=check_citations,
                check_symbols=check_symbols,
            )
            await _emit(result_cb, {"kind": "theorem", "index": idx, "data": r.to_dict()})
            return r

    reviews = await asyncio.gather(*[
        _limited_review(tp, i + 1) for i, tp in enumerate(to_review)
    ])

    all_issues = [issue for r in reviews for issue in r.issues]
    overall_verdict = _determine_verdict(all_issues)
    total_citations = sum(len(r.citation_checks) for r in reviews)

    await _emit(progress, "done", "审查完成，汇总结果…")

    return ReviewReport(
        source=source,
        overall_verdict=overall_verdict,
        theorem_reviews=list(reviews),
        issues=all_issues,
        stats={
            "theorems_parsed": len(pairs),
            "theorems_checked": len(to_review),
            "citations_checked": total_citations,
            "issues_found": len(all_issues),
        },
    )


async def review_paper_pages(
    page_texts: list[str],
    *,
    source: str,
    max_theorems: int = 8,
    progress: ProgressCb = None,
    result_cb: ResultCb = None,
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
    model: Optional[str] = None,
    lang: str = "zh",
) -> ReviewReport:
    """论文审查工作流：结构化分块 -> 上下文增强 -> claim 细审 -> 汇总。"""
    clean_pages = [(p or "").strip() for p in page_texts if (p or "").strip()]
    if not clean_pages:
        raise ValueError("论文内容不能为空")

    parse_pdf_msg = f"正在解析论文页面（{len(clean_pages)} 页）…" if lang == "zh" else f"Parsing paper pages ({len(clean_pages)} pages)..."
    await _emit(progress, "parse_pdf", parse_pdf_msg)
    document = build_structured_document(clean_pages, source=source)
    sections = document.sections
    if not sections:
        await _emit(progress, "fallback", "未能稳定识别论文结构，回退为整篇论文审查…")
        combined = "\n\n".join(
            f"[Page {idx}] {text}" for idx, text in enumerate(clean_pages, start=1)
        )
        report = await review_text(
            combined,
            source=source,
            max_theorems=max_theorems,
            progress=progress,
            result_cb=result_cb,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )
        report.stats.update({
            "paper_pages": len(clean_pages),
            "chunks_processed": 0,
            "sections_processed": 0,
            "structured_sections": 0,
            "statement_candidates": report.stats.get("statement_candidates", 0),
            "input_type": "paper_pages",
            "fallback": "paper_text",
        })
        return report
    await _emit(progress, "chunk", f"已解析为 {len(sections)} 个结构块，正在提取命题与上下文…")

    candidates: list[TheoremProofPair] = []
    candidates_with_proof: list[TheoremProofPair] = []
    candidates_without_proof: list[TheoremProofPair] = []
    seen: set[str] = set()
    reviews: list[TheoremReview] = []
    total_citations = 0
    sections_processed = 0

    async def _review_and_push(tp: TheoremProofPair) -> None:
        nonlocal total_citations
        idx = len(reviews) + 1
        loc = f"（{tp.section_title or tp.location_hint or tp.source}）" if (tp.section_title or tp.location_hint or tp.source) else ""
        await _emit(progress, "theorem", f"审查命题 {idx}/{max_theorems}{loc}…")
        review = await _review_single_theorem(
            tp,
            idx,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )
        # 计算置信度（与 review_claim 路径保持一致）
        review.theorem.review_confidence = _review_confidence_from_review(review)
        reviews.append(review)
        total_citations += len(review.citation_checks)
        await _emit(result_cb, {"kind": "theorem", "index": idx, "data": review.to_dict()})

    for idx, section in enumerate(sections, start=1):
        sections_processed = idx
        location = section.location_hint()
        await _emit(progress, "extract", f"提取命题 {idx}/{len(sections)}（{location}）…")
        extracted = await extract_statement_candidates_from_text(
            section.raw_text,
            source=source,
            location_hint=location,
            model=model,
            lang=lang,
        )

        if not extracted:
            lowered = section.raw_text.lower()
            title = section.section_title or ""
            title_is_claim = bool(_FORMAL_CLAIM_LABEL_RE.search(title)) and not _NON_THEOREM_TITLE_RE.match(title)
            body_has_claim_label = bool(_FORMAL_CLAIM_LABEL_RE.search(section.raw_text[:1200]))
            if (title_is_claim or body_has_claim_label) and not _NON_THEOREM_TITLE_RE.match(title):
                synthetic_statement = (
                    section.section_title
                    if title_is_claim and not section.section_title.startswith("section ")
                    else _short_excerpt(section.raw_text.split("\n\n", 1)[0], max_chars=200)
                )
                extracted = [TheoremProofPair(
                    env_type="theorem",
                    ref=section.section_title if section.section_title and not section.section_title.startswith("section ") else None,
                    statement=synthetic_statement,
                    proof=section.proof_excerpt or None,
                    source=source,
                    location_hint=location,
                    context_excerpt=section.raw_text[:3000],
                )]

        proof_first: list[TheoremProofPair] = []
        no_proof: list[TheoremProofPair] = []
        for pair in extracted:
            pair = _enrich_pair_from_section(pair, section, document=document)
            if not _is_reviewable_extracted_pair(pair):
                continue
            if pair.has_proof():
                proof_first.append(pair)
            else:
                no_proof.append(pair)

        for pair in [*proof_first, *no_proof]:
            key = _normalize_statement_key(pair.statement)
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(pair)
            if pair.has_proof():
                candidates_with_proof.append(pair)
            else:
                candidates_without_proof.append(pair)

    if not candidates:
        await _emit(progress, "fallback", "未识别到结构化命题，回退为整篇论文审查…")
        combined = "\n\n".join(
            f"[Page {idx}] {text}" for idx, text in enumerate(clean_pages, start=1)
        )
        report = await review_text(
            combined,
            source=source,
            max_theorems=max_theorems,
            progress=progress,
            result_cb=result_cb,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )
        report.stats.update({
            "paper_pages": len(clean_pages),
            "chunks_processed": len(sections),
            "sections_processed": len(sections),
            "structured_sections": len(sections),
            "statement_candidates": 0,
            "input_type": "paper_pages",
            "fallback": "paper_text",
        })
        return report

    # 全局优先：先审查有完整证明的命题，再补足无证明陈述（跨节选取，避免早停截断）
    to_review: list[TheoremProofPair] = []
    to_review.extend(candidates_with_proof[:max_theorems])
    if len(to_review) < max_theorems:
        for pair in candidates_without_proof:
            if len(to_review) >= max_theorems:
                break
            to_review.append(pair)

    if to_review:
        await _emit(
            progress,
            "review",
            f"已选定 {len(to_review)} 条命题（含证明 {sum(1 for p in to_review if p.has_proof())} 条），开始逐条审查…",
        )
    for pair in to_review:
        await _review_and_push(pair)

    all_issues = [issue for r in reviews for issue in r.issues]
    await _emit(progress, "done", "论文审查完成，正在汇总结果…")
    return ReviewReport(
        source=source,
        overall_verdict=_determine_verdict(all_issues),
        theorem_reviews=list(reviews),
        issues=all_issues,
        stats={
            "paper_pages": len(clean_pages),
            "chunks_processed": sections_processed,
            "sections_processed": sections_processed,
            "structured_sections": len(sections),
            "statement_candidates": len(candidates),
            "theorems_parsed": len(candidates),
            "theorems_checked": len(reviews),
            "claims_reviewed": len(reviews),
            "citations_checked": total_citations,
            "issues_found": len(all_issues),
            "input_type": "paper_pages",
            "scan_completed": sections_processed >= len(sections),
        },
    )


async def review_paper_images(
    images: list[str],
    *,
    source: str,
    max_theorems: int = 8,
    progress: ProgressCb = None,
    result_cb: ResultCb = None,
    check_logic: bool = True,
    check_citations: bool = True,
    check_symbols: bool = True,
    model: Optional[str] = None,
    lang: str = "zh",
) -> ReviewReport:
    """图片论文审查工作流：多模态抽取命题后逐条审查。"""
    parse_image_msg = f"正在解析图片输入（{len(images)} 张）…" if lang == "zh" else f"Parsing image input ({len(images)} images)..."
    await _emit(progress, "parse_image", parse_image_msg)
    candidates = await extract_statement_candidates_from_images(
        images,
        source=source,
        model=model,
        lang=lang,
    )
    if not candidates:
        raise ValueError("未能从图片中提取可审查的数学命题")

    seen: set[str] = set()
    deduped: list[TheoremProofPair] = []
    for pair in candidates:
        key = _normalize_statement_key(pair.statement)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(pair)

    reviews: list[TheoremReview] = []
    to_review = [p for p in deduped if p.has_proof()][:max_theorems] or deduped[:max_theorems]
    for idx, pair in enumerate(to_review, start=1):
        await _emit(progress, "theorem", f"审查图片命题 {idx}/{len(to_review)}…")
        review = await _review_single_theorem(
            pair,
            idx,
            check_logic=check_logic,
            check_citations=check_citations,
            check_symbols=check_symbols,
        )
        reviews.append(review)
        await _emit(result_cb, {"kind": "theorem", "index": idx, "data": review.to_dict()})

    all_issues = [issue for r in reviews for issue in r.issues]
    total_citations = sum(len(r.citation_checks) for r in reviews)
    await _emit(progress, "done", "图片审查完成，正在汇总结果…")
    return ReviewReport(
        source=source,
        overall_verdict=_determine_verdict(all_issues),
        theorem_reviews=reviews,
        issues=all_issues,
        stats={
            "images_processed": len(images),
            "statement_candidates": len(deduped),
            "theorems_parsed": len(deduped),
            "theorems_checked": len(reviews),
            "citations_checked": total_citations,
            "issues_found": len(all_issues),
            "input_type": "paper_images",
        },
    )
