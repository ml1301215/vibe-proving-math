from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import AsyncIterator, Optional

from modes.formalization.models import (
    LEAN_PLAYGROUND_URL,
    FormalizationAttempt,
    FormalizationCandidate,
    FormalizationBlueprint,
    FormalizeResult,
    RetrievalHit,
    VerificationReport,
)
from modes.formalization.tools import FormalizationTools

MATHLIB_MATCH_THRESHOLD = 0.72
_KEYWORD_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_KEYWORDS", "10"))
_RETRIEVAL_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_RETRIEVAL", "20"))
_VALIDATION_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_VALIDATION", "12"))
_BLUEPRINT_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_BLUEPRINT", "20"))
_GENERATE_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_GENERATE", "28"))
_REPAIR_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_REPAIR", "24"))
_VERIFY_STEP_TIMEOUT_SECONDS = float(os.environ.get("VP_FORMALIZE_TIMEOUT_VERIFY", "90"))
_BEAM_WIDTH = int(os.environ.get("VP_FORMALIZE_BEAM_WIDTH", "1") or "1")


def _default_hint(status: str, failure_mode: str, *, lang: str = "zh") -> str:
    if status in {"verified", "mathlib_verified"}:
        return "已通过验证，可继续补全证明细节。" if lang == "zh" else "Verification passed. You can refine the proof details."
    if failure_mode == "contains_sorry":
        return "当前代码已接近完成，但仍含 sorry；继续基于最新验证反馈补全缺失证明。" if lang == "zh" else "The code is close, but it still contains sorry; continue filling the missing proof from the latest verification feedback."
    if failure_mode == "mathlib_unavailable":
        return "本地缺少 Mathlib，请转在线 Lean Playground 或具备 Mathlib 的环境继续验证。" if lang == "zh" else "Mathlib is unavailable locally. Continue in the online Lean playground or a Mathlib-enabled environment."
    if failure_mode == "environment_unavailable":
        return "本地 Lean 环境不可用，建议先检查工具链安装。" if lang == "zh" else "Local Lean environment is unavailable. Check the toolchain installation."
    if failure_mode == "compile_timeout":
        return "本地编译超时，建议在线验证或先简化候选代码。" if lang == "zh" else "Compilation timed out. Try the online verifier or simplify the candidate."
    if failure_mode == "statement_mismatch":
        return "当前形式化方向可能偏离原命题，建议重新规划 blueprint。" if lang == "zh" else "The formalization may be drifting from the original statement. Re-plan the blueprint."
    return "可以继续追加优化，优先参考最新 verification trace 中的失败阶段与错误类型。" if lang == "zh" else "You can continue optimizing. Start from the latest verification trace and failure mode."


def _mathlib_result(best: dict, score: float, *, lang: str = "zh") -> FormalizeResult:
    source = str(best.get("source") or "mathlib4")
    explanation = best.get("match_explanation", "")
    blueprint = FormalizationBlueprint(
        goal_summary=best.get("lean_name") or best.get("path", ""),
        target_shape=best.get("snippet", "")[:200],
        strategy=(
            f"直接复用 {source} 检索出的已验证候选"
            if lang == "zh" else
            f"Reuse the verified candidate retrieved from {source}"
        ),
        notes=["retrieval-only result"],
    )
    candidate = FormalizationCandidate(
        lean_code=f"-- Source: {best['path']}\n-- {best.get('lean_name', '')}\n\n{best['snippet']}",
        theorem_statement=best.get("lean_name", ""),
        uses_mathlib=True,
        proof_status="complete",
        explanation=explanation,
        confidence=score,
        origin="mathlib4",
    )
    report = VerificationReport(
        status="mathlib_verified",
        error="",
        failure_mode="none",
        diagnostics=[],
        verifier=source,
        passed=True,
    )
    return FormalizeResult(
        status="found_mathlib",
        lean_code=candidate.lean_code,
        theorem_name=best.get("lean_name") or best.get("name", ""),
        source=source,
        source_url=best.get("html_url", ""),
        match_score=score,
        match_explanation=explanation,
        proof_status="complete",
        uses_mathlib=True,
        confidence=score,
        explanation=explanation,
        compilation=report.to_dict(),
        iterations=1,
        auto_optimized=False,
        attempt_history=[{
            "attempt": 1,
            "proof_status": "complete",
            "uses_mathlib": True,
            "compilation": report.to_dict(),
        }],
        blueprint=blueprint.to_dict(),
        selected_candidate=candidate.to_dict(),
        verification_trace=[{
            "attempt": 1,
            "action": "retrieval_match",
            "blueprint_revision": 0,
            "candidate": candidate.to_dict(),
            "verification": report.to_dict(),
        }],
        retrieval_context=[],
        failure_mode="none",
        next_action_hint=_default_hint("mathlib_verified", "none", lang=lang),
    )


def _merge_retrieval_hits(existing: list[RetrievalHit], incoming: list[RetrievalHit]) -> list[RetrievalHit]:
    merged: list[RetrievalHit] = []
    seen: set[tuple[str, str, str]] = set()
    for hit in [*existing, *incoming]:
        key = (hit.kind, hit.title, hit.source_url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
    merged.sort(key=lambda item: item.score, reverse=True)
    return merged


def _merge_candidates(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for candidate in [*existing, *incoming]:
        key = (
            str(candidate.get("path", "")).lower(),
            str(candidate.get("lean_name") or candidate.get("name", "")).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
    return merged


def _needs_retrieval_refresh(verification: VerificationReport) -> bool:
    return verification.failure_mode in {
        "missing_symbol",
        "statement_mismatch",
        "unsolved_goals",
        "tactic_error",
        "contains_sorry",
    }


def _is_retrieval_match_plausible(statement: str, candidate: dict, score: float) -> bool:
    if not candidate:
        return False
    if score < MATHLIB_MATCH_THRESHOLD:
        return False
    stmt = statement or ""
    stmt_lower = stmt.lower()
    haystack = " ".join(
        str(candidate.get(key, ""))
        for key in ("lean_name", "name", "path", "snippet")
    ).lower()
    lean_name = str(candidate.get("lean_name") or "").lower()

    if any(token in stmt_lower for token in ("整数", "integer", "ℤ", " int")) and ("real" in haystack or "ℝ" in haystack or "field" in haystack):
        return False

    tail = lean_name.split(".")[-1] if lean_name else ""
    if tail and tail not in haystack:
        return False

    divides_count = stmt.count("∣") + stmt.count("|") + stmt.count("整除") + stmt_lower.count("divides")
    if "dvd_trans" in lean_name and divides_count < 2:
        return False

    if "two_mul_le_add_sq" in lean_name and any(token in stmt_lower for token in ("整数", "integer", "ℤ", " int")):
        if "int" not in haystack and "ℤ" not in haystack:
            return False

    has_gauss_pattern = (
        ("1 + 2 + ... + n" in stmt_lower)
        or ("1+2+...+n" in stmt_lower)
        or ("1 + 2 + ⋯ + n" in stmt)
        or ("1 + 2 + \\cdots + n" in stmt)
        or ("n(n+1)/2" in stmt_lower)
        or ("n * (n + 1) / 2" in stmt_lower)
    )

    # 高斯求和类命题通常包含 /2 结构；sum_range 泛定理虽然相关，但不是最终结论。
    if ("/2" in stmt_lower or " / 2" in stmt_lower) and "gauss" in stmt_lower:
        if "gauss" not in haystack and "/ 2" not in haystack:
            return False
    if has_gauss_pattern and "sum_range" in lean_name and "gauss" not in haystack:
        return False
    if ("∑" in stmt or "sum" in stmt_lower) and ("/2" in stmt_lower or " / 2" in stmt_lower):
        if "sum_range" in lean_name and "gauss" not in haystack:
            return False
    return True


def _fallback_candidate_from_blueprint(statement: str, blueprint: FormalizationBlueprint) -> FormalizationCandidate:
    theorem_name = "auto_formalized"
    theorem_statement = (blueprint.target_shape or "").strip()
    if theorem_statement.startswith("theorem "):
        theorem_header = theorem_statement
        if ":= by" not in theorem_header:
            theorem_header = theorem_header + " := by"
    else:
        theorem_header = f"theorem {theorem_name} : Prop := by"
    fallback_code = f"{theorem_header}\n  sorry"
    return FormalizationCandidate(
        lean_code=fallback_code,
        theorem_statement=theorem_statement or theorem_header,
        uses_mathlib=True,
        proof_status="partial",
        explanation="生成阶段超时，使用最小占位候选继续迭代",
        confidence=0.15,
        origin="generated",
        blueprint_revision=blueprint.revision,
    )


def _verification_priority(verification: VerificationReport) -> int:
    if verification.passed:
        return 0
    order = {
        "contains_sorry": 1,
        "unsolved_goals": 2,
        "tactic_error": 3,
        "compile_error": 4,
        "missing_symbol": 5,
        "statement_mismatch": 6,
        "compile_timeout": 7,
        "mathlib_unavailable": 8,
        "environment_unavailable": 9,
        "none": 10,
    }
    return order.get(verification.failure_mode, 20)


async def run_formalization(
    statement: str,
    *,
    lang: str = "zh",
    model: Optional[str] = None,
    max_iters: int = 4,
    current_code: Optional[str] = None,
    compile_error: Optional[str] = None,
    skip_search: bool = False,
    tools: Optional[FormalizationTools] = None,
) -> AsyncIterator[str]:
    tools = tools or FormalizationTools()
    max_iters = max(1, min(int(max_iters or 1), 8))
    beam_width = max(1, min(int(_BEAM_WIDTH or 1), 3))

    def _status(step: str, msg: str) -> str:
        return f"<!--vp-status:{step}|{msg}-->"

    def _final(result: FormalizeResult) -> str:
        payload = base64.b64encode(json.dumps(result.to_dict(), ensure_ascii=False).encode()).decode()
        return f"<!--vp-final:{payload}-->"

    async def _verify_with_timeout(candidate_item: FormalizationCandidate) -> VerificationReport:
        try:
            verification_item = await asyncio.wait_for(
                tools.verify_candidate(candidate_item.lean_code),
                timeout=_VERIFY_STEP_TIMEOUT_SECONDS,
            )
        except Exception:
            verification_item = VerificationReport(
                status="timeout",
                error="verification timeout",
                failure_mode="compile_timeout",
                diagnostics=[],
                passed=False,
            )
        if verification_item.status == "verified" and candidate_item.uses_mathlib:
            verification_item = VerificationReport(
                status="mathlib_verified",
                error="",
                failure_mode="none",
                diagnostics=[],
                verifier=verification_item.verifier,
                passed=True,
            )
        return verification_item

    async def _select_best_verified_candidate(
        candidate_pool: list[FormalizationCandidate],
    ) -> tuple[FormalizationCandidate, VerificationReport]:
        best_candidate = candidate_pool[0]
        best_verification = await _verify_with_timeout(best_candidate)
        best_key = (_verification_priority(best_verification), -best_candidate.confidence)
        for candidate_item in candidate_pool[1:]:
            verification_item = await _verify_with_timeout(candidate_item)
            key = (_verification_priority(verification_item), -candidate_item.confidence)
            if key < best_key:
                best_candidate = candidate_item
                best_verification = verification_item
                best_key = key
        return best_candidate, best_verification

    retrieval_hits: list[RetrievalHit] = []
    retrieval_candidates: list[dict] = []
    blueprint: FormalizationBlueprint
    candidate: FormalizationCandidate
    candidate_pool: list[FormalizationCandidate]
    attempts: list[FormalizationAttempt] = []
    failure_modes: list[str] = []

    seed_code = (current_code or "").strip()
    candidate_action = "seed" if seed_code else "generate"
    if seed_code:
        yield _status(
            "repair",
            "继续基于当前 Lean 代码迭代修复…" if lang == "zh" else "Continuing iterative repair from the current Lean code…",
        )
        blueprint = tools.seed_blueprint(statement, seed_code, revision=0, lang=lang)
        candidate = FormalizationCandidate(
            lean_code=seed_code,
            theorem_statement="",
            uses_mathlib="import Mathlib" in seed_code,
            proof_status="partial" if "sorry" in seed_code else "complete",
            explanation="基于现有代码继续自动修复" if lang == "zh" else "Continuing from existing code",
            confidence=0.0,
            origin="seed",
            blueprint_revision=0,
        )
        candidate_pool = [candidate]
    else:
        keywords: list[str] = []
        if not skip_search:
            yield _status(
                "search",
                "正在分析命题，提取搜索关键词…" if lang == "zh" else "Analyzing statement, extracting keywords…",
            )
            try:
                keywords = await asyncio.wait_for(
                    tools.extract_keywords(statement),
                    timeout=_KEYWORD_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                keywords = []
            kw_display = "、".join(keywords) if lang == "zh" else ", ".join(keywords)
            yield _status("search", f"关键词：{kw_display}" if lang == "zh" else f"Keywords: {kw_display}")
            yield _status(
                "search",
                "正在做混合检索（mathlib + theorem search）…" if lang == "zh" else "Running hybrid retrieval (mathlib + theorem search)…",
            )
            try:
                retrieval_hits, retrieval_candidates = await asyncio.wait_for(
                    tools.retrieve_context(statement, keywords=keywords),
                    timeout=_RETRIEVAL_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                retrieval_hits, retrieval_candidates = [], []
            if retrieval_candidates:
                yield _status(
                    "validate",
                    f"找到 {len(retrieval_candidates)} 个候选，正在验证匹配度…"
                    if lang == "zh" else
                    f"Found {len(retrieval_candidates)} candidates, validating match quality…",
                )
                try:
                    best, score = await asyncio.wait_for(
                        tools.validate_mathlib_match(statement, retrieval_candidates),
                        timeout=_VALIDATION_STEP_TIMEOUT_SECONDS,
                    )
                except Exception:
                    best, score = None, 0.0
                if best and _is_retrieval_match_plausible(statement, best, score):
                    yield _status(
                        "found",
                        f"检索命中可直接复用的定理（置信度 {score:.0%}）"
                        if lang == "zh" else
                        f"Found a reusable theorem candidate (confidence {score:.0%})",
                    )
                    yield _final(_mathlib_result(best, score, lang=lang))
                    return
                if best and score >= MATHLIB_MATCH_THRESHOLD:
                    yield _status(
                        "validate",
                        "候选与原命题语义不完全一致，转入生成-验证流程"
                        if lang == "zh" else
                        "Candidate does not align semantically enough; continuing generation-verification flow",
                    )
        yield _status(
            "blueprint",
            "正在规划形式化 Blueprint…" if lang == "zh" else "Planning the formalization blueprint…",
        )
        try:
            blueprint = await asyncio.wait_for(
                tools.plan_blueprint(
                    statement,
                    retrieval_hits,
                    model=model,
                    lang=lang,
                    revision=0,
                ),
                timeout=_BLUEPRINT_STEP_TIMEOUT_SECONDS,
            )
        except Exception:
            blueprint = tools.seed_blueprint(statement, revision=0, lang=lang)
        yield _status(
            "generate",
            "正在根据 Blueprint 生成 Lean 候选…" if lang == "zh" else "Generating a Lean candidate from the blueprint…",
        )
        try:
            candidate = await asyncio.wait_for(
                tools.generate_candidate(
                    statement,
                    blueprint,
                    retrieval_hits,
                    model=model,
                    lang=lang,
                ),
                timeout=_GENERATE_STEP_TIMEOUT_SECONDS,
            )
        except Exception:
            candidate = _fallback_candidate_from_blueprint(statement, blueprint)
        candidate_pool = [candidate]
        if beam_width > 1:
            for _ in range(beam_width - 1):
                try:
                    extra_candidate = await asyncio.wait_for(
                        tools.generate_candidate(
                            statement,
                            blueprint,
                            retrieval_hits,
                            model=model,
                            lang=lang,
                        ),
                        timeout=_GENERATE_STEP_TIMEOUT_SECONDS,
                    )
                except Exception:
                    extra_candidate = _fallback_candidate_from_blueprint(statement, blueprint)
                candidate_pool.append(extra_candidate)
        candidate_action = "generate"

    last_verification = VerificationReport(
        status="unavailable",
        error=(compile_error or "").strip(),
        failure_mode="compile_error" if compile_error else "none",
        diagnostics=[compile_error] if compile_error else [],
        passed=False,
    )

    for attempt_idx in range(1, max_iters + 1):
        yield _status(
            "compile",
            (f"第 {attempt_idx} 轮：正在验证 Lean 候选…"
             if lang == "zh" else
             f"Attempt {attempt_idx}: verifying the Lean candidate…"),
        )
        candidate, verification = await _select_best_verified_candidate(candidate_pool)
        last_verification = verification
        failure_modes.append(verification.failure_mode)
        attempts.append(
            FormalizationAttempt(
                attempt=attempt_idx,
                action=candidate_action,
                blueprint_revision=blueprint.revision,
                candidate=candidate,
                verification=verification,
            )
        )

        if verification.passed:
            yield _status("compile", "✓ Lean 4 编译通过" if lang == "zh" else "✓ Lean 4 compilation passed")
            break
        if verification.status == "timeout":
            yield _status("compile", "编译超时，请稍后重试或在线验证" if lang == "zh" else "Compile timeout")
            break
        if verification.status == "unavailable":
            yield _status("compile", "本地 Lean 未就绪" if lang == "zh" else "Lean not available locally")
            break
        if verification.status == "mathlib_skip":
            yield _status(
                "compile",
                "本地环境缺少 Mathlib，无法继续自动编译修复；请转在线 Playground 复核"
                if lang == "zh" else
                "Local Mathlib environment is unavailable; verify in the online playground",
            )
            break

        yield _status(
            "compile",
            "编译有错误，正在决定是修复候选还是重写 Blueprint…"
            if lang == "zh" else
            "Compile errors found; deciding whether to repair the candidate or re-plan the blueprint…",
        )
        if (not skip_search) and _needs_retrieval_refresh(verification):
            yield _status(
                "search",
                "根据最新验证反馈重新检索相关定理与证明线索…"
                if lang == "zh" else
                "Refreshing theorem retrieval from the latest verification feedback…",
            )
            refresh_prompt = (
                f"{statement}\n\nLatest verification feedback:\n{verification.error or ' '.join(verification.diagnostics[:2])}\n\n"
                f"Current theorem statement:\n{candidate.theorem_statement}"
            )
            try:
                refresh_keywords = await asyncio.wait_for(
                    tools.extract_keywords(refresh_prompt),
                    timeout=_KEYWORD_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                refresh_keywords = []
            try:
                extra_hits, extra_candidates = await asyncio.wait_for(
                    tools.retrieve_context(statement, keywords=refresh_keywords),
                    timeout=_RETRIEVAL_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                extra_hits, extra_candidates = [], []
            retrieval_hits = _merge_retrieval_hits(retrieval_hits, extra_hits)
            retrieval_candidates = _merge_candidates(retrieval_candidates, extra_candidates)
            if extra_candidates:
                try:
                    best, score = await asyncio.wait_for(
                        tools.validate_mathlib_match(statement, retrieval_candidates[:8]),
                        timeout=_VALIDATION_STEP_TIMEOUT_SECONDS,
                    )
                except Exception:
                    best, score = None, 0.0
                if best and _is_retrieval_match_plausible(statement, best, score):
                    yield _status(
                        "found",
                        f"根据修复反馈补充检索后，找到可直接复用的定理（置信度 {score:.0%}）"
                        if lang == "zh" else
                        f"After retrieval refresh, found a reusable theorem (confidence {score:.0%})",
                    )
                    yield _final(_mathlib_result(best, score, lang=lang))
                    return
        if attempt_idx >= max_iters:
            yield _status(
                "repair",
                "已达到自动修复轮次上限，可继续追加优化" if lang == "zh" else "Reached auto-repair limit; you can continue optimizing",
            )
            break

        if tools.should_replan(
            verification,
            attempt=attempt_idx,
            max_iters=max_iters,
            previous_failure_modes=failure_modes,
        ):
            yield _status(
                "blueprint",
                (f"第 {blueprint.revision + 1} 次蓝图修订：根据验证反馈重写策略…"
                 if lang == "zh" else
                 f"Blueprint revision {blueprint.revision + 1}: revising strategy from verification feedback…"),
            )
            try:
                blueprint = await asyncio.wait_for(
                    tools.plan_blueprint(
                        statement,
                        retrieval_hits,
                        model=model,
                        lang=lang,
                        revision=blueprint.revision + 1,
                        previous_blueprint=blueprint,
                        verification=verification,
                        failing_code=candidate.lean_code,
                    ),
                    timeout=_BLUEPRINT_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                blueprint = tools.seed_blueprint(
                    statement,
                    candidate.lean_code,
                    revision=blueprint.revision + 1,
                    lang=lang,
                )
            yield _status(
                "generate",
                (f"第 {attempt_idx + 1} 轮：根据新 Blueprint 重新生成候选…"
                 if lang == "zh" else
                 f"Attempt {attempt_idx + 1}: regenerating a candidate from the revised blueprint…"),
            )
            try:
                candidate = await asyncio.wait_for(
                    tools.generate_candidate(
                        statement,
                        blueprint,
                        retrieval_hits,
                        model=model,
                        lang=lang,
                    ),
                    timeout=_GENERATE_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                candidate = _fallback_candidate_from_blueprint(statement, blueprint)
            candidate_pool = [candidate]
            if beam_width > 1:
                for _ in range(beam_width - 1):
                    try:
                        extra_candidate = await asyncio.wait_for(
                            tools.generate_candidate(
                                statement,
                                blueprint,
                                retrieval_hits,
                                model=model,
                                lang=lang,
                            ),
                            timeout=_GENERATE_STEP_TIMEOUT_SECONDS,
                        )
                    except Exception:
                        extra_candidate = _fallback_candidate_from_blueprint(statement, blueprint)
                    candidate_pool.append(extra_candidate)
            candidate_action = "replan"
        else:
            yield _status(
                "repair",
                (f"第 {attempt_idx + 1} 轮：AI 正根据编译错误优化 Lean 代码…"
                 if lang == "zh" else
                 f"Attempt {attempt_idx + 1}: repairing Lean code from compiler feedback…"),
            )
            try:
                candidate = await asyncio.wait_for(
                    tools.repair_candidate(
                        statement,
                        blueprint,
                        candidate,
                        verification,
                        model=model,
                        lang=lang,
                    ),
                    timeout=_REPAIR_STEP_TIMEOUT_SECONDS,
                )
            except Exception:
                candidate = FormalizationCandidate(
                    lean_code=candidate.lean_code,
                    theorem_statement=candidate.theorem_statement,
                    uses_mathlib=candidate.uses_mathlib,
                    proof_status=candidate.proof_status,
                    explanation=(candidate.explanation or "") + "；repair 超时，保留上一版候选",
                    confidence=candidate.confidence,
                    origin="repaired",
                    blueprint_revision=blueprint.revision,
                )
            candidate_pool = [candidate]
            if beam_width > 1:
                for _ in range(beam_width - 1):
                    try:
                        extra_candidate = await asyncio.wait_for(
                            tools.repair_candidate(
                                statement,
                                blueprint,
                                candidate,
                                verification,
                                model=model,
                                lang=lang,
                            ),
                            timeout=_REPAIR_STEP_TIMEOUT_SECONDS,
                        )
                    except Exception:
                        extra_candidate = candidate
                    candidate_pool.append(extra_candidate)
            candidate_action = "repair"

    final_attempts = [a for a in attempts if a.verification]
    verification_trace = [a.to_dict() for a in final_attempts]
    attempt_history = [
        {
            "attempt": a.attempt,
            "proof_status": a.candidate.proof_status,
            "uses_mathlib": a.candidate.uses_mathlib,
            "compilation": a.verification.to_dict(),
        }
        for a in final_attempts
    ]

    result = FormalizeResult(
        status="generated",
        lean_code=candidate.lean_code,
        theorem_name=candidate.theorem_statement,
        source="generated",
        source_url=LEAN_PLAYGROUND_URL,
        proof_status=candidate.proof_status,
        uses_mathlib=candidate.uses_mathlib,
        confidence=candidate.confidence,
        explanation=candidate.explanation,
        compilation=last_verification.to_dict(),
        iterations=max(1, len(attempt_history)),
        auto_optimized=max(1, len(attempt_history)) > 1,
        attempt_history=attempt_history,
        error=last_verification.error,
        blueprint=blueprint.to_dict(),
        selected_candidate=candidate.to_dict(),
        verification_trace=verification_trace,
        retrieval_context=[hit.to_dict() for hit in retrieval_hits[:8]],
        failure_mode=last_verification.failure_mode,
        next_action_hint=_default_hint(last_verification.status, last_verification.failure_mode, lang=lang),
    )
    yield _final(result)
