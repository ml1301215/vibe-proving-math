from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from modes.research.agent.models import ParsedPage

_BROKEN_MATH_PATTERNS = [
    re.compile(r"\$[^$\n]{0,200}$"),
    re.compile(r"\\begin\{[a-zA-Z*]+\}(?![\s\S]*?\\end\{[a-zA-Z*]+\})"),
    re.compile(r"\\\([^\)]{0,200}$"),
    re.compile(r"\\\[[^\]]{0,200}$"),
]


@dataclass
class PageQuality:
    page_num: int
    score: float
    text_coverage_ratio: float
    weird_char_ratio: float
    heading_noise_ratio: float
    formula_break_ratio: float
    average_page_confidence: float
    low_confidence: bool
    reasons: list[str]


def _count_weird_chars(text: str) -> int:
    weird_chars = "���������������"
    return sum(ch in weird_chars for ch in text)


def _formula_break_ratio(text: str) -> float:
    if not text:
        return 1.0
    hits = sum(1 for pat in _BROKEN_MATH_PATTERNS if pat.search(text))
    open_dollars = text.count("$")
    if open_dollars % 2 == 1:
        hits += 1
    return min(hits / 3.0, 1.0)


def _heading_noise_ratio(page: ParsedPage) -> float:
    candidates = [*page.headers, *page.footers]
    if not candidates:
        return 0.0
    noisy = 0
    for line in candidates:
        stripped = (line or "").strip().lower()
        if not stripped:
            noisy += 1
        elif re.fullmatch(r"(?:page\s+)?\d{1,4}", stripped):
            noisy += 1
        elif re.fullmatch(r"[ivxlcdm]{1,8}", stripped):
            noisy += 1
    return noisy / max(len(candidates), 1)


def evaluate_page_quality(page: ParsedPage) -> PageQuality:
    text = (page.text or "").strip()
    length = len(text)
    text_coverage_ratio = min(length / 1200.0, 1.0) if length > 0 else 0.0
    weird_char_ratio = _count_weird_chars(text) / max(length, 1)
    heading_noise_ratio = _heading_noise_ratio(page)
    formula_break_ratio = _formula_break_ratio(text)
    avg_conf = float(page.confidence if page.confidence is not None else 1.0)

    score = 1.0
    reasons: list[str] = []

    if text_coverage_ratio < 0.15:
        score -= 0.38
        reasons.append("text_coverage_low")
    if weird_char_ratio > 0.01:
        score -= 0.34
        reasons.append("weird_chars_high")
    if heading_noise_ratio > 0.4:
        score -= 0.12
        reasons.append("heading_noise_high")
    if formula_break_ratio > 0.25:
        score -= 0.24
        reasons.append("formula_break_high")
    if avg_conf < 0.55:
        score -= 0.28
        reasons.append("parser_confidence_low")

    score = max(0.0, min(score, 1.0))
    return PageQuality(
        page_num=page.page_num,
        score=round(score, 3),
        text_coverage_ratio=round(text_coverage_ratio, 3),
        weird_char_ratio=round(weird_char_ratio, 4),
        heading_noise_ratio=round(heading_noise_ratio, 3),
        formula_break_ratio=round(formula_break_ratio, 3),
        average_page_confidence=round(avg_conf, 3),
        low_confidence=score < 0.58,
        reasons=reasons,
    )


def evaluate_document_quality(parsed_pages: list[ParsedPage]) -> tuple[float, list[int], dict[int, PageQuality]]:
    if not parsed_pages:
        return 0.0, [], {}
    page_scores = {page.page_num: evaluate_page_quality(page) for page in parsed_pages}
    quality_score = round(sum(item.score for item in page_scores.values()) / len(page_scores), 3)
    low_conf_pages = [page_num for page_num, item in page_scores.items() if item.low_confidence]
    return quality_score, low_conf_pages, page_scores
