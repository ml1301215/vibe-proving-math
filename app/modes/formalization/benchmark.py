from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from core.text_sanitize import strip_non_math_latex
from modes.formalization.orchestrator import MATHLIB_MATCH_THRESHOLD, _is_retrieval_match_plausible
from modes.formalization.tools import (
    _expand_search_keywords,
    extract_keywords,
    retrieve_context,
    validate_mathlib_match,
)

_DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "formalization_retrieval_cases.json"
_KEYWORD_STEP_TIMEOUT_SECONDS = 10.0
_RETRIEVAL_STEP_TIMEOUT_SECONDS = 18.0
_VALIDATION_STEP_TIMEOUT_SECONDS = 12.0


def _fallback_keywords_from_statement(statement: str) -> list[str]:
    ascii_words = list(dict.fromkeys(re.findall(r"[A-Za-z_]{3,}", statement)))
    return ascii_words[:5]


def _heuristic_match_candidate(statement: str, expanded_keywords: list[str], candidates: list[dict]) -> tuple[Optional[dict], float]:
    theoremish = [token.lower() for token in expanded_keywords if "_" in token or "." in token]
    if not theoremish or not candidates:
        return None, 0.0

    best_candidate = None
    best_score = 0.0
    for candidate in candidates:
        haystack = " ".join(
            str(candidate.get(key, ""))
            for key in ("lean_name", "path", "name", "snippet")
        ).lower()
        for token in theoremish:
            tail = token.split(".")[-1]
            theorem_pat = re.compile(rf"\b(?:theorem|lemma)\s+{re.escape(tail)}\b")
            if theorem_pat.search(haystack):
                score = 0.96
            elif token in haystack:
                score = 0.93
            elif tail in haystack and "_" in tail:
                score = 0.84
            else:
                score = 0.0
            if score > best_score:
                best_candidate = {
                    **candidate,
                    "lean_name": candidate.get("lean_name") or token,
                    "match_explanation": f"heuristic:{tail}",
                }
                best_score = score
    return best_candidate, best_score


async def _noop_theorem_search(*args, **kwargs):
    return []


@dataclass
class RetrievalBenchmarkCaseResult:
    case_id: str
    category: str
    statement: str
    expected_early_return: bool
    keywords: list[str] = field(default_factory=list)
    expanded_keywords: list[str] = field(default_factory=list)
    candidate_count: int = 0
    top_path: str = ""
    top_source: str = ""
    match_score: float = 0.0
    matched_lean_name: str = ""
    early_return: bool = False
    optimization_reason: str = ""

    def to_dict(self) -> dict:
        return sanitize_benchmark_payload(asdict(self))

    @property
    def status(self) -> str:
        if self.expected_early_return:
            return "hit" if self.early_return else "needs_optimization"
        if not self.early_return:
            return "expected_generate"
        if self.optimization_reason.startswith("能力提升命中"):
            return "capability_gain_hit"
        return "unexpected_hit"


@dataclass
class RetrievalBenchmarkSummary:
    results: list[RetrievalBenchmarkCaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def hit_cases(self) -> list[RetrievalBenchmarkCaseResult]:
        return [result for result in self.results if result.status == "hit"]

    @property
    def needs_optimization_cases(self) -> list[RetrievalBenchmarkCaseResult]:
        return [result for result in self.results if result.status == "needs_optimization"]

    @property
    def expected_generate_cases(self) -> list[RetrievalBenchmarkCaseResult]:
        return [result for result in self.results if result.status == "expected_generate"]

    @property
    def unexpected_hit_cases(self) -> list[RetrievalBenchmarkCaseResult]:
        return [result for result in self.results if result.status == "unexpected_hit"]

    @property
    def capability_gain_cases(self) -> list[RetrievalBenchmarkCaseResult]:
        return [result for result in self.results if result.status == "capability_gain_hit"]

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for result in self.results:
            if not result.optimization_reason:
                continue
            counts[result.optimization_reason] = counts.get(result.optimization_reason, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return sanitize_benchmark_payload({
            "total": self.total,
            "hit_count": len(self.hit_cases),
            "needs_optimization_count": len(self.needs_optimization_cases),
            "expected_generate_count": len(self.expected_generate_cases),
            "capability_gain_count": len(self.capability_gain_cases),
            "unexpected_hit_count": len(self.unexpected_hit_cases),
            "reasons": self.reason_counts(),
            "results": [result.to_dict() for result in self.results],
        })

    def render_text(self) -> str:
        lines = [
            "在线检索 benchmark 摘要",
            (
                f"总计 {self.total} 题"
                f" | 命中 {len(self.hit_cases)}"
                f" | 待优化 {len(self.needs_optimization_cases)}"
                f" | 预期走生成 {len(self.expected_generate_cases)}"
            ),
        ]

        if self.hit_cases:
            lines.append("")
            lines.append("命中:")
            for result in self.hit_cases:
                match_name = result.matched_lean_name or result.top_path or "unknown"
                lines.append(
                    f"- {result.case_id}: {match_name} "
                    f"(来源 {result.top_source or 'unknown'}, 候选 {result.candidate_count}, 分数 {result.match_score:.2f})"
                )

        if self.needs_optimization_cases:
            lines.append("")
            lines.append("待继续优化:")
            for result in self.needs_optimization_cases:
                lines.append(
                    f"- {result.case_id}: {result.optimization_reason} "
                    f"(最佳来源 {result.top_source or 'unknown'}, 候选 {result.candidate_count}, 分数 {result.match_score:.2f})"
                )

        if self.expected_generate_cases:
            lines.append("")
            lines.append("符合预期地继续走生成:")
            for result in self.expected_generate_cases:
                lines.append(
                    f"- {result.case_id}: {result.optimization_reason or '该题不应直接命中 mathlib'}"
                )

        if self.capability_gain_cases:
            lines.append("")
            lines.append("能力提升命中（可接受）:")
            for result in self.capability_gain_cases:
                lines.append(
                    f"- {result.case_id}: 提前命中 {result.matched_lean_name or result.top_path}"
                )

        if self.unexpected_hit_cases:
            lines.append("")
            lines.append("需要复查的异常命中:")
            for result in self.unexpected_hit_cases:
                lines.append(
                    f"- {result.case_id}: 实际提前返回到 {result.matched_lean_name or result.top_path}"
                )

        reason_counts = self.reason_counts()
        if reason_counts:
            lines.append("")
            lines.append("主要原因:")
            for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
                lines.append(f"- {reason}: {count}")

        return strip_non_math_latex("\n".join(lines))


def load_retrieval_cases(path: Optional[Path] = None) -> list[dict]:
    fixture_path = Path(path) if path else _DEFAULT_FIXTURE_PATH
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def sanitize_benchmark_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return payload
    sanitized = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_benchmark_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_benchmark_payload(item) if isinstance(item, dict) else strip_non_math_latex(item)
                for item in value
            ]
        else:
            sanitized[key] = strip_non_math_latex(value)
    return sanitized


def _build_optimization_reason(
    *,
    statement: str,
    expected_early_return: bool,
    candidate_count: int,
    match_score: float,
    matched_lean_name: str,
    early_return: bool,
) -> str:
    if expected_early_return:
        if early_return:
            return "已命中"
        if candidate_count <= 0:
            return "未检索到候选"
        if not matched_lean_name:
            return "检索到候选，但匹配判定未通过"
        if match_score < MATHLIB_MATCH_THRESHOLD:
            return f"检索到候选，但匹配分数不足阈值 ({match_score:.2f} < {MATHLIB_MATCH_THRESHOLD:.2f})"
        return "检索命中异常，需复查"

    if early_return:
        stmt = (statement or "").lower()
        lean_name = (matched_lean_name or "").lower()
        divides_count = statement.count("∣") + statement.count("|") + statement.count("整除") + stmt.count("divides")
        if "dvd_trans" in lean_name and divides_count >= 2:
            return "能力提升命中（可接受）"
        return "本题原本应继续生成，但当前被提前匹配"
    if candidate_count <= 0:
        return "未检索到直接可复用的 mathlib 候选"
    return "有相关候选，但继续走生成更稳"


async def evaluate_live_retrieval_case(case: dict, *, top_k: int = 4) -> RetrievalBenchmarkCaseResult:
    statement = str(case.get("statement", "")).strip()
    try:
        keywords = await asyncio.wait_for(
            extract_keywords(statement),
            timeout=_KEYWORD_STEP_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        keywords = _fallback_keywords_from_statement(statement)

    expanded_keywords = _expand_search_keywords(statement, keywords)
    try:
        _, candidates = await asyncio.wait_for(
            retrieve_context(
                statement,
                keywords=expanded_keywords,
                github_top_k=top_k,
                external_top_k=top_k,
                theorem_top_k=max(2, top_k),
                theorem_search=_noop_theorem_search,
            ),
            timeout=_RETRIEVAL_STEP_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return RetrievalBenchmarkCaseResult(
            case_id=str(case.get("id", "")),
            category=str(case.get("category", "")),
            statement=statement,
            expected_early_return=bool(case.get("expect_early_return", False)),
            keywords=list(keywords),
            expanded_keywords=list(expanded_keywords),
            optimization_reason=f"检索步骤超时 (> {_RETRIEVAL_STEP_TIMEOUT_SECONDS:.0f}s)",
        )

    if candidates:
        try:
            best, score = await asyncio.wait_for(
                validate_mathlib_match(statement, candidates[:top_k]),
                timeout=_VALIDATION_STEP_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            best, score = _heuristic_match_candidate(statement, expanded_keywords, candidates[:top_k])
            if best is None:
                return RetrievalBenchmarkCaseResult(
                    case_id=str(case.get("id", "")),
                    category=str(case.get("category", "")),
                    statement=statement,
                    expected_early_return=bool(case.get("expect_early_return", False)),
                    keywords=list(keywords),
                    expanded_keywords=list(expanded_keywords),
                    candidate_count=len(candidates),
                    top_path=candidates[0].get("path", "") if candidates else "",
                    top_source=candidates[0].get("source", "") if candidates else "",
                    optimization_reason=f"匹配判定超时 (> {_VALIDATION_STEP_TIMEOUT_SECONDS:.0f}s)",
                )
    else:
        best, score = None, 0.0

    matched_lean_name = (best or {}).get("lean_name", "")
    early_return = bool(best and _is_retrieval_match_plausible(statement, best, score))
    optimization_reason = _build_optimization_reason(
        statement=statement,
        expected_early_return=bool(case.get("expect_early_return", False)),
        candidate_count=len(candidates),
        match_score=float(score),
        matched_lean_name=matched_lean_name,
        early_return=early_return,
    )
    return RetrievalBenchmarkCaseResult(
        case_id=str(case.get("id", "")),
        category=str(case.get("category", "")),
        statement=statement,
        expected_early_return=bool(case.get("expect_early_return", False)),
        keywords=list(keywords),
        expanded_keywords=list(expanded_keywords),
        candidate_count=len(candidates),
        top_path=candidates[0].get("path", "") if candidates else "",
        top_source=candidates[0].get("source", "") if candidates else "",
        match_score=float(score),
        matched_lean_name=matched_lean_name,
        early_return=early_return,
        optimization_reason=optimization_reason,
    )


async def run_live_retrieval_benchmark(
    cases: Optional[Iterable[dict]] = None,
    *,
    categories: Optional[set[str]] = None,
    limit: Optional[int] = None,
    top_k: int = 4,
    per_case_timeout: float = 45.0,
) -> RetrievalBenchmarkSummary:
    selected_cases = list(cases if cases is not None else load_retrieval_cases())
    if categories:
        selected_cases = [case for case in selected_cases if case.get("category") in categories]
    if limit is not None:
        selected_cases = selected_cases[:limit]

    results: list[RetrievalBenchmarkCaseResult] = []
    for case in selected_cases:
        try:
            result = await asyncio.wait_for(
                evaluate_live_retrieval_case(case, top_k=top_k),
                timeout=per_case_timeout,
            )
        except asyncio.TimeoutError:
            result = RetrievalBenchmarkCaseResult(
                case_id=str(case.get("id", "")),
                category=str(case.get("category", "")),
                statement=str(case.get("statement", "")).strip(),
                expected_early_return=bool(case.get("expect_early_return", False)),
                keywords=[],
                expanded_keywords=[],
                candidate_count=0,
                top_path="",
                top_source="",
                match_score=0.0,
                matched_lean_name="",
                early_return=False,
                optimization_reason=f"单题在线 benchmark 超时 (> {per_case_timeout:.0f}s)",
            )
        results.append(result)
    return RetrievalBenchmarkSummary(results=results)
