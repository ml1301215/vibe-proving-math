"""Formalization pipeline compatibility layer.

将原有单文件 pipeline 拆成：
- `models.py`：领域模型
- `tools.py`：检索 / 规划 / 生成 / 验证 / 修复工具
- `orchestrator.py`：多阶段编排

本文件保留旧入口与可 monkeypatch 的私有函数名，避免 `/formalize`
路由和既有测试一次性失效。
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

from modes.formalization.models import FormalizeResult, VerificationReport
from modes.formalization.orchestrator import run_formalization
from modes.formalization.tools import (
    FormalizationTools,
    _normalize_candidate_data,
    classify_failure_mode,
    extract_keywords as _extract_keywords_impl,
    generate_candidate as _generate_candidate_impl,
    plan_blueprint as _plan_blueprint_impl,
    repair_candidate as _repair_candidate_impl,
    retrieve_context as _retrieve_context_impl,
    search_github_mathlib as _search_github_mathlib_impl,
    seed_blueprint as _seed_blueprint_impl,
    should_replan as _should_replan_impl,
    validate_mathlib_match as _validate_match_impl,
    verify_candidate as _verify_candidate_impl,
)


async def _extract_keywords(statement: str) -> list[str]:
    return await _extract_keywords_impl(statement)


async def _search_github_mathlib(keywords: list[str], top_k: int = 6) -> list[dict]:
    return await _search_github_mathlib_impl(keywords, top_k=top_k)


async def _validate_match(statement: str, candidates: list[dict]) -> tuple[Optional[dict], float]:
    return await _validate_match_impl(statement, candidates)


async def _retrieve_context(statement: str, *, keywords: list[str]) -> tuple[list, list[dict]]:
    return await _retrieve_context_impl(
        statement,
        keywords=keywords,
        github_search=_search_github_mathlib,
    )


async def _plan_blueprint(
    statement: str,
    retrieval_hits: list,
    *,
    model: Optional[str] = None,
    lang: str = "zh",
    revision: int = 0,
    previous_blueprint=None,
    verification=None,
    failing_code: str = "",
):
    return await _plan_blueprint_impl(
        statement,
        retrieval_hits,
        model=model,
        lang=lang,
        revision=revision,
        previous_blueprint=previous_blueprint,
        verification=verification,
        failing_code=failing_code,
    )


async def _autoformalize(statement: str, model: Optional[str] = None, lang: str = "zh") -> dict:
    blueprint = _seed_blueprint_impl(statement, "", revision=0, lang=lang)
    candidate = await _generate_candidate_impl(
        statement,
        blueprint,
        [],
        model=model,
        lang=lang,
    )
    return candidate.to_dict()


async def _generate_candidate(
    statement: str,
    blueprint,
    retrieval_hits: list,
    *,
    model: Optional[str] = None,
    lang: str = "zh",
):
    return await _generate_candidate_impl(
        statement,
        blueprint,
        retrieval_hits,
        model=model,
        lang=lang,
    )


async def _repair_formalization(
    statement: str,
    lean_code: str,
    compile_error: str,
    *,
    model: Optional[str] = None,
    lang: str = "zh",
) -> dict:
    blueprint = _seed_blueprint_impl(statement, lean_code, revision=0, lang=lang)
    candidate = _normalize_candidate_data(
        {
            "lean_code": lean_code,
            "theorem_statement": "",
            "uses_mathlib": "import Mathlib" in lean_code,
            "proof_status": "partial" if "sorry" in lean_code else "complete",
            "explanation": "基于当前 Lean 代码执行修复",
            "confidence": 0.0,
        },
        fallback_code=lean_code,
        origin="seed",
        blueprint_revision=0,
    )
    verification = VerificationReport(
        status="error",
        error=compile_error,
        failure_mode="compile_error",
        diagnostics=[compile_error] if compile_error else [],
        passed=False,
    )
    repaired = await _repair_candidate_impl(
        statement,
        blueprint,
        candidate,
        verification,
        model=model,
        lang=lang,
    )
    return repaired.to_dict()


async def _try_compile_lean(lean_code: str) -> dict:
    return (await _verify_candidate_impl(lean_code)).to_dict()


async def _repair_candidate(
    statement: str,
    blueprint,
    candidate,
    verification,
    *,
    model: Optional[str] = None,
    lang: str = "zh",
):
    data = await _repair_formalization(
        statement,
        candidate.lean_code,
        verification.error,
        model=model,
        lang=lang,
    )
    return _normalize_candidate_data(
        data,
        fallback_code=candidate.lean_code,
        fallback_explanation=candidate.explanation,
        origin="repaired",
        blueprint_revision=getattr(blueprint, "revision", 0),
    )


async def _verify_candidate_compat(lean_code: str) -> VerificationReport:
    raw = await _try_compile_lean(lean_code)
    status = raw.get("status", "error")
    error = raw.get("error", "")
    return VerificationReport(
        status=status,
        error=error,
        failure_mode=raw.get("failure_mode") or classify_failure_mode(status, error),
        diagnostics=raw.get("diagnostics") or ([error] if error else []),
        verifier=raw.get("verifier", "local_lean"),
        passed=bool(raw.get("passed", status in {"verified", "mathlib_verified"})),
    )


def _should_replan(verification, *, attempt: int, max_iters: int, previous_failure_modes: list[str]) -> bool:
    return _should_replan_impl(
        verification,
        attempt=attempt,
        max_iters=max_iters,
        previous_failure_modes=previous_failure_modes,
    )


async def formalize_stream(
    statement: str,
    lang: str = "zh",
    model: Optional[str] = None,
    max_iters: int = 4,
    current_code: Optional[str] = None,
    compile_error: Optional[str] = None,
    skip_search: bool = False,
) -> AsyncIterator[str]:
    tools = FormalizationTools(
        extract_keywords=_extract_keywords,
        search_github_mathlib=_search_github_mathlib,
        validate_mathlib_match=_validate_match,
        retrieve_context=_retrieve_context,
        plan_blueprint=_plan_blueprint,
        generate_candidate=_generate_candidate,
        repair_candidate=_repair_candidate,
        verify_candidate=_verify_candidate_compat,
        should_replan=_should_replan,
        seed_blueprint=_seed_blueprint_impl,
    )
    async for chunk in run_formalization(
        statement,
        lang=lang,
        model=model,
        max_iters=max_iters,
        current_code=current_code,
        compile_error=compile_error,
        skip_search=skip_search,
        tools=tools,
    ):
        yield chunk
