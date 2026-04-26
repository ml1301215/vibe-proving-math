import base64
import json
import os
from pathlib import Path

import pytest

from modes.formalization.benchmark import (
    RetrievalBenchmarkCaseResult,
    RetrievalBenchmarkSummary,
    evaluate_live_retrieval_case,
    load_retrieval_cases,
    run_live_retrieval_benchmark,
)
from modes.formalization.models import FormalizationBlueprint, FormalizationCandidate, VerificationReport
from modes.formalization.orchestrator import MATHLIB_MATCH_THRESHOLD, run_formalization
from modes.formalization.tools import FormalizationTools


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "formalization_retrieval_cases.json"
RETRIEVAL_CASES = load_retrieval_cases(FIXTURE_PATH)


async def _collect_pipeline(async_gen) -> dict:
    final = None
    async for chunk in async_gen:
        if chunk.startswith("<!--vp-final:"):
            payload = chunk[len("<!--vp-final:"):-3]
            final = json.loads(base64.b64decode(payload.encode("ascii")).decode("utf-8"))
    assert final is not None
    return final


@pytest.mark.asyncio
@pytest.mark.parametrize("case", RETRIEVAL_CASES, ids=[case["id"] for case in RETRIEVAL_CASES])
async def test_retrieval_benchmark_mock_cases(case):
    observed = {"expanded_keywords": []}

    async def extract_keywords_case(statement: str) -> list[str]:
        return list(case["keywords"])

    async def fake_github_search(keywords: list[str], top_k: int = 6) -> list[dict]:
        observed["expanded_keywords"] = list(keywords)
        return list(case["github_candidates"])[:top_k]

    async def fake_theorem_search(*args, **kwargs):
        return []

    async def fake_external_search(statement: str, keywords: list[str], top_k: int = 4):
        return []

    async def retrieve_context_case(statement: str, *, keywords: list[str]):
        return await FormalizationTools().retrieve_context(
            statement,
            keywords=keywords,
            github_search=fake_github_search,
            external_search=fake_external_search,
            theorem_search=fake_theorem_search,
        )

    async def validate_match_case(statement: str, candidates: list[dict]):
        validate = case["validate"]
        if not validate["match"] or not candidates:
            return None, 0.0
        best = dict(candidates[min(validate.get("best_index", 0), len(candidates) - 1)])
        best["lean_name"] = validate.get("lean_name", "")
        best["match_explanation"] = f"fixture:{case['id']}"
        return best, float(validate["score"])

    async def plan_blueprint_case(statement: str, retrieval_hits: list, **kwargs):
        return FormalizationBlueprint(
            goal_summary=statement,
            target_shape=f"theorem {case['id']} : True",
            strategy=f"fallback-for-{case['id']}",
            revision=0,
        )

    async def generate_candidate_case(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code=f"theorem {case['id']} : True := by\n  trivial",
            theorem_statement=f"theorem {case['id']} : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation=f"generated-for-{case['id']}",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def verify_candidate_case(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    if case["expect_early_return"]:
        async def fail_plan_blueprint(*args, **kwargs):
            raise AssertionError(f"{case['id']} 应提前返回，不应再调用 blueprint")

        async def fail_generate_candidate(*args, **kwargs):
            raise AssertionError(f"{case['id']} 应提前返回，不应再生成候选")

        tools = FormalizationTools(
            extract_keywords=extract_keywords_case,
            retrieve_context=retrieve_context_case,
            validate_mathlib_match=validate_match_case,
            plan_blueprint=fail_plan_blueprint,
            generate_candidate=fail_generate_candidate,
        )
    else:
        tools = FormalizationTools(
            extract_keywords=extract_keywords_case,
            retrieve_context=retrieve_context_case,
            validate_mathlib_match=validate_match_case,
            plan_blueprint=plan_blueprint_case,
            generate_candidate=generate_candidate_case,
            verify_candidate=verify_candidate_case,
        )

    final = await _collect_pipeline(run_formalization(case["statement"], tools=tools))

    for term in case["expected_search_terms"]:
        assert term in observed["expanded_keywords"], f"{case['id']} 缺少扩展关键词 {term}"

    expected_status = "found_mathlib" if case["expect_early_return"] else "generated"
    assert final["status"] == expected_status
    if case["expect_early_return"]:
        assert final["match_score"] >= MATHLIB_MATCH_THRESHOLD
        assert final["source"] == "mathlib4"
        if case["expected_path_contains"]:
            assert case["expected_path_contains"] in final["lean_code"]
    else:
        assert final["source"] == "generated"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_retrieval_live_smoke_finds_candidate_for_some_direct_hit_case():
    if os.environ.get("VP_RUN_FORMALIZATION_RETRIEVAL_LIVE") != "1":
        pytest.skip("未开启 live retrieval smoke")
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("缺少 GITHUB_TOKEN")

    summary = await run_live_retrieval_benchmark(
        categories={"direct_hit"},
        limit=4,
        top_k=4,
    )

    assert len(summary.hit_cases) >= 1, f"live retrieval 未命中任何 direct_hit case:\n{summary.render_text()}"


def test_retrieval_fixture_has_balanced_categories():
    categories = {}
    for case in RETRIEVAL_CASES:
        categories[case["category"]] = categories.get(case["category"], 0) + 1

    assert len(RETRIEVAL_CASES) >= 12
    assert categories.get("direct_hit", 0) >= 5
    assert categories.get("ambiguous_hit", 0) >= 3
    assert categories.get("no_hit", 0) >= 3


def test_retrieval_fixture_respects_threshold_expectations():
    for case in RETRIEVAL_CASES:
        score = float(case["validate"]["score"])
        if case["expect_early_return"]:
            assert case["validate"]["match"] is True
            assert score >= MATHLIB_MATCH_THRESHOLD
        else:
            assert (not case["validate"]["match"]) or score < MATHLIB_MATCH_THRESHOLD


def test_retrieval_summary_groups_hits_and_optimization_cases():
    summary = RetrievalBenchmarkSummary(
        results=[
            RetrievalBenchmarkCaseResult(
                case_id="nat_add_zero",
                category="direct_hit",
                statement="对任意自然数 n，有 n + 0 = n",
                expected_early_return=True,
                candidate_count=4,
                match_score=1.0,
                matched_lean_name="Nat.add_zero",
                early_return=True,
                optimization_reason="已命中",
            ),
            RetrievalBenchmarkCaseResult(
                case_id="two_mul_le_add_sq",
                category="direct_hit",
                statement="对任意实数 a, b，有 a^2 + b^2 ≥ 2ab",
                expected_early_return=True,
                candidate_count=0,
                match_score=0.0,
                matched_lean_name="",
                early_return=False,
                optimization_reason="未检索到候选",
            ),
            RetrievalBenchmarkCaseResult(
                case_id="gauss_sum_ambiguous",
                category="ambiguous_hit",
                statement="对任意自然数 n，有 1 + 2 + ... + n = n(n+1)/2",
                expected_early_return=False,
                candidate_count=1,
                match_score=0.61,
                matched_lean_name="Finset.sum_range_succ",
                early_return=False,
                optimization_reason="有相关候选，但继续走生成更稳",
            ),
            RetrievalBenchmarkCaseResult(
                case_id="dvd_wrong_candidate",
                category="ambiguous_hit",
                statement="若自然数 m 整除 n，且 n 整除 k，则 m 整除 k",
                expected_early_return=False,
                candidate_count=1,
                match_score=0.96,
                matched_lean_name="dvd_trans",
                early_return=True,
                optimization_reason="能力提升命中（可接受）",
            ),
        ]
    )

    text = summary.render_text()

    assert "命中:" in text
    assert "待继续优化:" in text
    assert "符合预期地继续走生成:" in text
    assert "能力提升命中（可接受）:" in text
    assert "nat_add_zero" in text
    assert "two_mul_le_add_sq" in text
    assert "未检索到候选" in text
    assert "dvd_wrong_candidate" in text


@pytest.mark.asyncio
async def test_live_retrieval_benchmark_marks_timeout_case(monkeypatch):
    async def fake_evaluate(case: dict, *, top_k: int = 4):
        await __import__("asyncio").sleep(0.02)
        return RetrievalBenchmarkCaseResult(
            case_id=case["id"],
            category=case["category"],
            statement=case["statement"],
            expected_early_return=case["expect_early_return"],
        )

    monkeypatch.setattr("modes.formalization.benchmark.evaluate_live_retrieval_case", fake_evaluate)

    summary = await run_live_retrieval_benchmark(
        cases=[RETRIEVAL_CASES[0]],
        per_case_timeout=0.001,
    )

    assert summary.total == 1
    assert summary.needs_optimization_cases[0].optimization_reason.startswith("单题在线 benchmark 超时")
