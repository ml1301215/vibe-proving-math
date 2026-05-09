from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import httpx

from core.llm import chat_json, lang_sys_suffix
from core.config import formalization_cfg
from modes.formalization.external_search import search_external_mathlib
from modes.formalization.models import (
    FormalizationBlueprint,
    FormalizationCandidate,
    RetrievalHit,
    VerificationReport,
)
from modes.formalization.prompts import (
    BLUEPRINT_SYSTEM,
    FORMALIZE_SYSTEM,
    KEYWORD_SYSTEM,
    REPAIR_SYSTEM,
    REPLAN_SYSTEM,
    VALIDATE_SYSTEM,
)
from modes.formalization.verifier import classify_failure_mode, verify_candidate
from skills.search_theorems import search_theorems as search_lean_theorems

logger = logging.getLogger("modes.formalization")

GITHUB_SEARCH_URL = "https://api.github.com/search/code"
MATHLIB4_REPO = "leanprover-community/mathlib4"
_HEURISTIC_FAST_MATCH_THRESHOLD = 0.92
_LEGACY_MATHLIB_IMPORT_PREFIXES = (
    "Mathlib.",
    "Data.",
    "Tactic.",
    "Algebra.",
    "Analysis.",
    "Topology.",
    "NumberTheory.",
    "LinearAlgebra.",
    "Geometry.",
    "RingTheory.",
    "MeasureTheory.",
    "Combinatorics.",
    "Probability.",
    "GroupTheory.",
    "Order.",
    "SetTheory.",
    "FieldTheory.",
    "CategoryTheory.",
    "Logic.",
    "ModelTheory.",
    "Computability.",
)
_KEYWORD_ALIAS_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("自然数", "natural number", "natural numbers", "nat"), ("nat",)),
    (("实数", "real number", "real numbers", "real"), ("real",)),
    (("整数", "integer", "integers", "int"), ("int",)),
    (("整除", "divides", "divisible", "dvd", "∣"), ("dvd", "dvd_trans")),
    (("交换律", "commutative", "commutativity"), ("comm", "add_comm", "mul_comm")),
    (("结合律", "associative", "associativity"), ("assoc", "mul_assoc", "add_assoc")),
    (("平方非负", "square nonnegative", "square is nonnegative"), ("sq_nonneg",)),
)

def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _resolve_formalization_model(stage: str, override: Optional[str] = None) -> str:
    if override:
        return str(override).strip()
    return ""


def _extract_theorem_statement(lean_code: str) -> str:
    if not lean_code:
        return ""
    m = re.search(r"^\s*theorem\s+.+$", lean_code, flags=re.MULTILINE)
    return m.group(0).strip() if m else ""


def _deterministic_repair_candidate(
    candidate: FormalizationCandidate,
    verification: VerificationReport,
) -> Optional[FormalizationCandidate]:
    theorem_statement = candidate.theorem_statement or _extract_theorem_statement(candidate.lean_code)
    if not theorem_statement:
        return None

    square_ineq = re.search(
        r"theorem\s+([A-Za-z0-9_']+)\s+\(([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*ℝ\)\s*:\s*"
        r"\2\s*\^\s*2\s*\+\s*\3\s*\^\s*2\s*[≥>=]+\s*2\s*\*\s*\2\s*\*\s*\3",
        theorem_statement,
    )
    if square_ineq and verification.failure_mode in {"tactic_error", "compile_error", "unsolved_goals"}:
        theorem_name, var_a, var_b = square_ineq.groups()
        repaired_code = (
            "import Mathlib\n\n"
            f"theorem {theorem_name} ({var_a} {var_b} : ℝ) : {var_a} ^ 2 + {var_b} ^ 2 ≥ 2 * {var_a} * {var_b} := by\n"
            f"  have h : ({var_a} - {var_b}) ^ 2 ≥ 0 := sq_nonneg ({var_a} - {var_b})\n"
            "  nlinarith\n"
        )
        return _normalize_candidate_data(
            {
                "lean_code": repaired_code,
                "theorem_statement": theorem_statement,
                "uses_mathlib": True,
                "proof_status": "complete",
                "explanation": "使用平方非负模板对二次不等式进行稳健修复。",
                "confidence": max(candidate.confidence, 0.9),
            },
            fallback_code=candidate.lean_code,
            fallback_explanation=candidate.explanation,
            origin="repaired",
            blueprint_revision=candidate.blueprint_revision,
        )

    return None


def _get_github_token() -> str:
    return str(formalization_cfg().get("github_token") or "").strip()


def _normalize_search_keyword(token: str) -> str:
    token = str(token or "").strip()
    if not token:
        return ""
    token = token.replace("-", "_")
    token = re.sub(r"[^A-Za-z0-9_.]+", "_", token)
    token = re.sub(r"_+", "_", token).strip("_.")
    return token.lower()


def _expand_search_keywords(statement: str, keywords: list[str]) -> list[str]:
    stmt = (statement or "").strip()
    stmt_lower = stmt.lower()
    stmt_compact = re.sub(r"\s+", "", stmt_lower)
    expanded: list[str] = []
    seen: set[str] = set()
    raw_keywords = [_normalize_search_keyword(keyword) for keyword in (keywords or [])]
    raw_keywords = [keyword for keyword in raw_keywords if keyword]
    statement_aliases: list[str] = []
    priority_aliases: list[str] = []

    def push(token: str) -> None:
        normalized = _normalize_search_keyword(token)
        if not normalized or normalized in seen:
            return
        expanded.append(normalized)
        seen.add(normalized)

    theoremish_raw = [keyword for keyword in raw_keywords if "_" in keyword or "." in keyword]
    other_raw = [keyword for keyword in raw_keywords if keyword not in theoremish_raw]

    for needles, aliases in _KEYWORD_ALIAS_RULES:
        if any(needle in stmt_lower for needle in needles):
            statement_aliases.extend(aliases)

    if (
        ("^2" in stmt_compact and "≥2" in stmt_compact and "ab" in stmt_compact)
        or ("^2" in stmt_compact and ">=2" in stmt_compact and "ab" in stmt_compact)
    ):
        priority_aliases.extend(("two_mul_le_add_sq", "sq_nonneg", "add_sq", "pow_two"))

    if any(
        pattern in stmt_compact
        for pattern in ("a+b=b+a", "x+y=y+x", "m+n=n+m", "n+m=m+n")
    ):
        priority_aliases.extend(("add_comm", "nat.add_comm"))

    if any(
        pattern in stmt_compact
        for pattern in ("n+0=n", "a+0=a", "m+0=m")
    ):
        priority_aliases.extend(("add_zero", "nat.add_zero"))

    if stmt.count("∣") >= 2 or ("divides" in stmt_lower and "then" in stmt_lower):
        priority_aliases.extend(("dvd_trans", "dvd"))

    if any(
        pattern in stmt_compact
        for pattern in ("(a-b)^2≥0", "(a-b)^2>=0", "(x-y)^2≥0", "(x-y)^2>=0")
    ):
        priority_aliases.extend(("sq_nonneg", "pow_two"))

    if any(
        pattern in stmt_compact
        for pattern in ("x^2≥0", "x^2>=0", "a^2≥0", "a^2>=0", "n^2≥0", "n^2>=0")
    ):
        priority_aliases.extend(("sq_nonneg", "pow_two"))

    if ("1 + 2 + ... + n" in stmt_lower) or ("1 + 2 + ⋯ + n" in stmt_lower) or ("1 + 2 + \\cdots + n" in stmt_lower):
        priority_aliases.extend(("sum_range", "gauss_sum", "sum_range_id"))

    if "∑" in stmt or "sum" in stmt_lower:
        statement_aliases.extend(("sum", "finset"))

    if "nat" in statement_aliases:
        for keyword in theoremish_raw:
            if (
                "." not in keyword
                and keyword not in {"dvd_trans"}
                and "number" not in keyword
                and keyword not in {"natural_number", "real_number", "integer_number"}
            ):
                push(f"nat.{keyword}")

    for alias in priority_aliases:
        push(alias)

    for keyword in theoremish_raw:
        push(keyword)

    for alias in statement_aliases:
        push(alias)

    for keyword in other_raw:
        push(keyword)

    if not expanded:
        for word in re.findall(r"[A-Za-z_]{3,}", stmt):
            push(word)

    derived_tokens = list(expanded)
    for token in derived_tokens:
        for dotted_part in token.split("."):
            if dotted_part and dotted_part != token:
                push(dotted_part)
        underscored_parts = [part for part in token.split("_") if part]
        if len(underscored_parts) >= 2:
            push("_".join(underscored_parts[-2:]))
        if underscored_parts:
            push(underscored_parts[-1])

    return expanded[:10]


def _build_mathlib_search_queries(keywords: list[str], *, max_queries: int = 3) -> list[str]:
    normalized = [_normalize_search_keyword(keyword) for keyword in keywords if _normalize_search_keyword(keyword)]
    if not normalized:
        return []

    queries: list[str] = []
    seen: set[str] = set()
    theoremish = [token for token in normalized if "_" in token or "." in token]
    atomic = [token for token in normalized if token not in theoremish]
    domain = [token for token in atomic if token in {"nat", "real", "int", "dvd", "finset", "sum"}]

    def add_query(parts: list[str]) -> None:
        query = " ".join(part for part in parts if part).strip()
        if not query or query in seen:
            return
        queries.append(query)
        seen.add(query)

    if theoremish:
        exact = theoremish[0]
        quoted = f"\"{exact}\""
        add_query([quoted])
        if "." in exact:
            tail = exact.split(".")[-1]
            add_query([quoted, f"\"{tail}\"", *domain[:1]])
        else:
            add_query([quoted, *domain[:2]])
    add_query(theoremish[:2] + domain[:2] if theoremish else atomic[:3])
    add_query(normalized[:4])

    return queries[:max_queries]


def _candidate_name_fragments(lean_name: str) -> list[str]:
    lean_name = str(lean_name or "").strip()
    if not lean_name:
        return []

    fragments: list[str] = []
    seen: set[str] = set()
    for raw in [lean_name, *lean_name.split(".")]:
        item = raw.strip()
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        fragments.append(item)
        seen.add(lowered)
    return fragments


def _select_mathlib_candidate(candidates: list[dict], lean_name: str) -> dict:
    if not candidates:
        return {}

    fragments = _candidate_name_fragments(lean_name)
    if not fragments:
        return dict(candidates[0])

    best_candidate = candidates[0]
    best_score = -1
    tail = fragments[-1].lower()
    theorem_pat = re.compile(rf"\b(?:theorem|lemma)\s+{re.escape(tail)}\b")

    for candidate in candidates:
        haystack = " ".join(
            str(candidate.get(key, ""))
            for key in ("path", "name", "snippet")
        ).lower()
        score = 0
        if theorem_pat.search(str(candidate.get("snippet", "")).lower()):
            score += 5
        for fragment in fragments:
            lowered = fragment.lower()
            if lowered and lowered in haystack:
                score += 2 if lowered == tail else 1
        if score > best_score:
            best_candidate = candidate
            best_score = score

    return dict(best_candidate)


def _heuristic_match_candidate(statement: str, candidates: list[dict]) -> tuple[Optional[dict], float]:
    if not candidates:
        return None, 0.0

    expanded_keywords = _expand_search_keywords(statement, [])
    theoremish_tokens = [
        token.lower() for token in expanded_keywords
        if "_" in token or "." in token
    ]
    if not theoremish_tokens:
        return None, 0.0

    best_candidate: Optional[dict] = None
    best_score = 0.0
    statement_lower = (statement or "").lower()
    need_nat = any(token in statement_lower for token in ("自然数", "natural number", "ℕ", " nat"))
    need_real = any(token in statement_lower for token in ("实数", "real number", "ℝ", " real"))
    need_int = any(token in statement_lower for token in ("整数", "integer", "ℤ", " int"))
    divides_count = statement.count("∣") + statement_lower.count("divides")

    for candidate in candidates[:8]:
        haystack = " ".join(
            str(candidate.get(key, ""))
            for key in ("lean_name", "path", "name", "snippet")
        ).lower()
        snippet = str(candidate.get("snippet", "")).lower()
        for token in theoremish_tokens:
            tail = token.split(".")[-1]
            if tail == "dvd_trans" and divides_count < 2:
                continue
            if need_nat and not (re.search(r"\bnat\b", haystack) or "ℕ" in haystack):
                continue
            if need_real and not (re.search(r"\breal\b", haystack) or "ℝ" in haystack):
                continue
            if need_int and not (re.search(r"\bint\b", haystack) or "ℤ" in haystack):
                continue
            theorem_pat = re.compile(rf"\b(?:theorem|lemma)\s+{re.escape(tail)}\b")
            if theorem_pat.search(snippet):
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


def _normalize_lean_code_text(lean_code: str) -> str:
    code = (lean_code or "").strip()
    if not code:
        return ""
    fenced = re.match(r"^```(?:lean)?\s*([\s\S]*?)\s*```$", code)
    if fenced:
        code = fenced.group(1).strip()
    if "\\r\\n" in code:
        code = code.replace("\\r\\n", "\n")
    if "\\n" in code:
        code = code.replace("\\n", "\n")
    if "\\t" in code:
        code = code.replace("\\t", "\t")
    lines = code.splitlines()
    mathlib_import_seen = False
    normalized_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import "):
            imported_modules = [part.strip() for part in stripped[len("import "):].split() if part.strip()]
            if any(
                module == "Mathlib" or module.startswith(_LEGACY_MATHLIB_IMPORT_PREFIXES)
                for module in imported_modules
            ):
                if not mathlib_import_seen:
                    normalized_lines.append("import Mathlib")
                    mathlib_import_seen = True
                continue
        normalized_lines.append(line)
    code = "\n".join(normalized_lines)
    return code.strip()


def _infer_proof_status(lean_code: str) -> str:
    code = (lean_code or "").strip()
    if not code:
        return "statement_only"
    if re.search(r"\bsorry\b", code):
        return "partial"
    if ":= by" in code or re.search(r"^\s*by\s*$", code, flags=re.MULTILINE):
        return "complete"
    return "statement_only"


def _normalize_candidate_data(
    data: Optional[dict],
    *,
    fallback_code: str = "",
    fallback_explanation: str = "",
    origin: str = "generated",
    blueprint_revision: int = 0,
) -> FormalizationCandidate:
    data = data or {}
    lean_code = _normalize_lean_code_text(data.get("lean_code") or fallback_code or "")
    theorem_statement = (data.get("theorem_statement") or _extract_theorem_statement(lean_code)).strip()
    uses_mathlib = bool(data.get("uses_mathlib", False) or re.search(r"^\s*import\s+Mathlib", lean_code, flags=re.MULTILINE))
    proof_status = (data.get("proof_status") or _infer_proof_status(lean_code)).strip()
    if proof_status not in {"complete", "partial", "statement_only"}:
        proof_status = _infer_proof_status(lean_code)
    explanation = (data.get("explanation") or fallback_explanation).strip()
    confidence = _safe_float(data.get("confidence", 0.0))
    return FormalizationCandidate(
        lean_code=lean_code,
        theorem_statement=theorem_statement,
        uses_mathlib=uses_mathlib,
        proof_status=proof_status,
        explanation=explanation,
        confidence=confidence,
        origin=origin,
        blueprint_revision=blueprint_revision,
    )


def _normalize_blueprint_data(data: Optional[dict], *, revision: int = 0) -> FormalizationBlueprint:
    data = data or {}
    return FormalizationBlueprint(
        goal_summary=(data.get("goal_summary") or "").strip(),
        target_shape=(data.get("target_shape") or "").strip(),
        definitions=[str(x).strip() for x in (data.get("definitions") or []) if str(x).strip()],
        planned_imports=[str(x).strip() for x in (data.get("planned_imports") or []) if str(x).strip()],
        intermediate_lemmas=[str(x).strip() for x in (data.get("intermediate_lemmas") or []) if str(x).strip()],
        strategy=(data.get("strategy") or "").strip(),
        notes=[str(x).strip() for x in (data.get("notes") or []) if str(x).strip()],
        revision=revision,
    )


def seed_blueprint(statement: str, current_code: str = "", *, revision: int = 0, lang: str = "zh") -> FormalizationBlueprint:
    theorem_statement = _extract_theorem_statement(current_code)
    note = "从现有 Lean 代码继续优化" if lang == "zh" else "Continuing from existing Lean code"
    return FormalizationBlueprint(
        goal_summary=statement.strip(),
        target_shape=theorem_statement or statement.strip(),
        definitions=[],
        planned_imports=["Mathlib"] if re.search(r"^\s*import\s+Mathlib", current_code or "", flags=re.MULTILINE) else [],
        intermediate_lemmas=[],
        strategy=note,
        notes=[note],
        revision=revision,
    )


async def extract_keywords(statement: str) -> list[str]:
    try:
        raw = await chat_json(
            f"Mathematical statement:\n{statement}",
            system=KEYWORD_SYSTEM,
            model=_resolve_formalization_model("keywords"),
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        keywords = [k.strip() for k in data.get("keywords", []) if str(k).strip()][:5]
        return _expand_search_keywords(statement, keywords)[:5]
    except Exception as e:
        logger.warning("keyword extraction failed: %s", e)
        words = [w for w in re.findall(r"[A-Za-z]{4,}", statement)]
        return _expand_search_keywords(statement, list(dict.fromkeys(words))[:5])[:5]


async def search_github_mathlib(keywords: list[str], top_k: int = 6) -> list[dict]:
    if not keywords:
        return []

    token = _get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3.text-match+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    queries = _build_mathlib_search_queries(keywords)
    if not queries:
        return []

    try:
        out: list[dict] = []
        seen: set[tuple[str, str]] = set()
        async with httpx.AsyncClient(timeout=15.0) as client:
            for raw_query in queries:
                q = f"{raw_query} repo:{MATHLIB4_REPO} language:Lean"
                resp = await client.get(
                    GITHUB_SEARCH_URL,
                    params={"q": q, "per_page": top_k},
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning("GitHub search returned %d", resp.status_code)
                    if resp.status_code == 401:
                        return []
                    continue
                data = resp.json()
                items = data.get("items", [])
                for item in items[:top_k]:
                    matches = item.get("text_matches", [])
                    snippet = " … ".join(m.get("fragment", "") for m in matches[:2] if m.get("fragment"))
                    candidate = {
                        "name": item.get("name", ""),
                        "path": item.get("path", ""),
                        "html_url": item.get("html_url", ""),
                        "snippet": snippet[:800],
                        "source": "github_mathlib",
                    }
                    key = (candidate["path"], candidate["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(candidate)
                    if len(out) >= top_k:
                        return out[:top_k]
        return out
    except Exception as e:
        logger.warning("GitHub search error: %s", e)
        return []


async def validate_mathlib_match(statement: str, candidates: list[dict]) -> tuple[Optional[dict], float]:
    if not candidates:
        return None, 0.0
    heuristic_best, heuristic_score = _heuristic_match_candidate(statement, candidates)
    if heuristic_best and heuristic_score >= _HEURISTIC_FAST_MATCH_THRESHOLD:
        return heuristic_best, heuristic_score
    cand_text = "\n\n".join(
        f"[{i + 1}] File: {c['path']}\nSnippet:\n{c['snippet']}"
        for i, c in enumerate(candidates[:4])
    )
    user_msg = (
        f"Natural language statement:\n{statement}\n\n"
        f"Lean 4 / Mathlib candidates:\n{cand_text}\n\n"
        "Which candidate, if any, is a correct formalization of the statement? "
        "Output JSON. If none match well, set match=false."
    )
    try:
        raw = await chat_json(
            user_msg,
            system=VALIDATE_SYSTEM,
            model=_resolve_formalization_model("validate"),
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not data.get("match", False):
            return None, 0.0
        score = _safe_float(data.get("score", 0.0))
        lean_name = data.get("lean_name", "")
        best = _select_mathlib_candidate(candidates, lean_name)
        best["lean_name"] = lean_name
        best["match_explanation"] = data.get("explanation", "")
        return best, score
    except Exception as e:
        logger.warning("match validation failed: %s", e)
        if heuristic_best:
            return heuristic_best, heuristic_score
        return None, 0.0


async def retrieve_context(
    statement: str,
    *,
    keywords: list[str],
    github_top_k: int = 6,
    external_top_k: int = 4,
    theorem_top_k: int = 5,
    github_search: Optional[Callable[[list[str], int], Awaitable[list[dict]]]] = None,
    external_search: Optional[Callable[[str, list[str], int], Awaitable[list[dict]]]] = None,
    theorem_search: Optional[Callable[..., Awaitable[list]]] = None,
) -> tuple[list[RetrievalHit], list[dict]]:
    expanded_keywords = _expand_search_keywords(statement, keywords)
    github_search_impl = github_search or search_github_mathlib
    external_search_impl = external_search or search_external_mathlib
    theorem_search_impl = theorem_search or search_lean_theorems
    github_candidates, external_candidates = await asyncio.gather(
        github_search_impl(expanded_keywords, top_k=github_top_k),
        external_search_impl(statement, expanded_keywords, top_k=external_top_k),
    )
    all_candidates: list[dict] = []
    seen_candidate_keys: set[tuple[str, str]] = set()

    for candidate in [*github_candidates, *external_candidates]:
        key = (
            str(candidate.get("path", "")).lower(),
            str(candidate.get("lean_name") or candidate.get("name", "")).lower(),
        )
        if key in seen_candidate_keys:
            continue
        seen_candidate_keys.add(key)
        all_candidates.append(candidate)

    hits: list[RetrievalHit] = []
    for c in all_candidates:
        hits.append(
            RetrievalHit(
                kind=f"{c.get('source', 'github')}_mathlib",
                title=c.get("path", "") or c.get("name", ""),
                body=c.get("snippet", ""),
                source=str(c.get("source", "mathlib4")),
                source_url=c.get("html_url", ""),
                score=float(c.get("score", 0.0) or 0.0),
                metadata={
                    "lean_name": c.get("lean_name", ""),
                    **dict(c.get("metadata", {}) or {}),
                },
            )
        )
    try:
        theorem_hits = await theorem_search_impl(statement, top_k=theorem_top_k, min_sim=0.0)
    except Exception as e:
        logger.warning("search_theorems failed during retrieval: %s", e)
        theorem_hits = []
    for hit in theorem_hits:
        hits.append(
            RetrievalHit(
                kind="theorem_search",
                title=hit.name,
                body=hit.body or hit.slogan,
                source=hit.paper_title or "TheoremSearch",
                source_url=hit.link,
                score=hit.score or hit.similarity,
                metadata={"similarity": hit.similarity},
            )
        )
    hits.sort(key=lambda x: x.score, reverse=True)
    return hits, all_candidates


def _format_retrieval_context(retrieval_hits: list[RetrievalHit], *, max_chars: int = 4000) -> str:
    if not retrieval_hits:
        return "No retrieval context available."
    lines = ["Retrieval context:"]
    total = 0
    for idx, hit in enumerate(retrieval_hits, 1):
        line = (
            f"[{idx}] kind={hit.kind} title={hit.title}\n"
            f"source={hit.source}\n"
            f"body={hit.body[:500]}\n"
        )
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


async def plan_blueprint(
    statement: str,
    retrieval_hits: list[RetrievalHit],
    *,
    model: Optional[str] = None,
    lang: str = "zh",
    revision: int = 0,
    previous_blueprint: Optional[FormalizationBlueprint] = None,
    verification: Optional[VerificationReport] = None,
    failing_code: str = "",
) -> FormalizationBlueprint:
    if previous_blueprint is None:
        user_msg = (
            f"Natural language statement:\n{statement}\n\n"
            f"{_format_retrieval_context(retrieval_hits)}"
        )
        system = BLUEPRINT_SYSTEM + lang_sys_suffix(lang)
    else:
        user_msg = (
            f"Natural language statement:\n{statement}\n\n"
            f"Previous blueprint:\n{json.dumps(previous_blueprint.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"{_format_retrieval_context(retrieval_hits)}\n\n"
            f"Verification report:\n{json.dumps((verification or VerificationReport(status='error')).to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"Failing Lean code:\n```lean\n{failing_code}\n```"
        )
        system = REPLAN_SYSTEM + lang_sys_suffix(lang)
    try:
        raw = await chat_json(
            user_msg,
            system=system,
            model=_resolve_formalization_model("blueprint", model),
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        return _normalize_blueprint_data(data, revision=revision)
    except Exception as e:
        logger.warning("plan blueprint failed: %s", e)
        strategy = "回退到最小形式化蓝图" if lang == "zh" else "Fallback to minimal blueprint"
        return FormalizationBlueprint(
            goal_summary=statement.strip(),
            target_shape=statement.strip(),
            definitions=[],
            planned_imports=[],
            intermediate_lemmas=[],
            strategy=strategy,
            notes=[str(e)],
            revision=revision,
        )


async def generate_candidate(
    statement: str,
    blueprint: FormalizationBlueprint,
    retrieval_hits: list[RetrievalHit],
    *,
    model: Optional[str] = None,
    lang: str = "zh",
) -> FormalizationCandidate:
    user_msg = (
        f"Natural language statement:\n{statement}\n\n"
        f"Blueprint:\n{json.dumps(blueprint.to_dict(), ensure_ascii=False, indent=2)}\n\n"
        f"{_format_retrieval_context(retrieval_hits)}"
    )
    try:
        raw = await chat_json(
            user_msg,
            system=FORMALIZE_SYSTEM + lang_sys_suffix(lang),
            model=_resolve_formalization_model("generate", model),
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        return _normalize_candidate_data(data, origin="generated", blueprint_revision=blueprint.revision)
    except Exception as e:
        logger.warning("generate candidate failed: %s", e)
        return _normalize_candidate_data(
            {
                "lean_code": f"-- Formalization failed: {e}\ntheorem statement : False := by\n  sorry",
                "theorem_statement": "theorem statement : False",
                "uses_mathlib": False,
                "proof_status": "statement_only",
                "explanation": f"自动形式化失败：{e}",
                "confidence": 0.0,
            },
            origin="generated",
            blueprint_revision=blueprint.revision,
        )


async def repair_candidate(
    statement: str,
    blueprint: FormalizationBlueprint,
    candidate: FormalizationCandidate,
    verification: VerificationReport,
    *,
    model: Optional[str] = None,
    lang: str = "zh",
) -> FormalizationCandidate:
    deterministic = _deterministic_repair_candidate(candidate, verification)
    if deterministic is not None:
        return deterministic

    user_msg = (
        f"Natural language statement:\n{statement}\n\n"
        f"Blueprint:\n{json.dumps(blueprint.to_dict(), ensure_ascii=False, indent=2)}\n\n"
        f"Current Lean 4 code:\n```lean\n{candidate.lean_code}\n```\n\n"
        f"Latest verification report:\n```json\n{json.dumps(verification.to_dict(), ensure_ascii=False, indent=2)}\n```"
    )
    try:
        raw = await chat_json(
            user_msg,
            system=REPAIR_SYSTEM + lang_sys_suffix(lang),
            model=_resolve_formalization_model("repair", model),
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        return _normalize_candidate_data(
            data,
            fallback_code=candidate.lean_code,
            fallback_explanation="根据编译错误自动修复 Lean 代码",
            origin="repaired",
            blueprint_revision=blueprint.revision,
        )
    except Exception as e:
        logger.warning("repair candidate failed: %s", e)
        return _normalize_candidate_data(
            {
                "lean_code": candidate.lean_code,
                "theorem_statement": candidate.theorem_statement,
                "uses_mathlib": candidate.uses_mathlib,
                "proof_status": candidate.proof_status,
                "explanation": f"自动修复失败：{e}",
                "confidence": candidate.confidence,
            },
            fallback_code=candidate.lean_code,
            fallback_explanation=candidate.explanation,
            origin="repaired",
            blueprint_revision=blueprint.revision,
        )


def should_replan(
    verification: VerificationReport,
    *,
    attempt: int,
    max_iters: int,
    previous_failure_modes: list[str],
) -> bool:
    if verification.failure_mode in {"statement_mismatch", "unsolved_goals"}:
        return True
    if attempt >= max_iters - 1:
        return False
    if len(previous_failure_modes) >= 2 and previous_failure_modes[-1] == previous_failure_modes[-2]:
        return verification.failure_mode in {"missing_symbol", "tactic_error", "compile_error", "contains_sorry"}
    return False


@dataclass
class FormalizationTools:
    extract_keywords: Callable[[str], Awaitable[list[str]]] = extract_keywords
    search_github_mathlib: Callable[[list[str], int], Awaitable[list[dict]]] = search_github_mathlib
    validate_mathlib_match: Callable[[str, list[dict]], Awaitable[tuple[Optional[dict], float]]] = validate_mathlib_match
    retrieve_context: Callable[..., Awaitable[tuple[list[RetrievalHit], list[dict]]]] = retrieve_context
    plan_blueprint: Callable[..., Awaitable[FormalizationBlueprint]] = plan_blueprint
    generate_candidate: Callable[..., Awaitable[FormalizationCandidate]] = generate_candidate
    repair_candidate: Callable[..., Awaitable[FormalizationCandidate]] = repair_candidate
    verify_candidate: Callable[[str], Awaitable[VerificationReport]] = verify_candidate
    should_replan: Callable[..., bool] = should_replan
    seed_blueprint: Callable[..., FormalizationBlueprint] = seed_blueprint
