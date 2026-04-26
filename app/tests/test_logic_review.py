"""逻辑审查与引用提取冒烟测试。

覆盖：
- 引用提取：[n]、Author(Year)
- gap 路径：LLM 返回 gap 时 verification.overall 应为 has_gaps
- review_confidence：review_paper_pages 路径应设置非 None/0 置信度
- 逻辑召回：_review_single_theorem 对含 critical_error 的 LLM 响应应给出 Incorrect
"""
from __future__ import annotations

import pytest

from modes.research import reviewer as rv
from modes.research.parser import TheoremProofPair
from skills.verify_sequential import VerificationResult, StepVerdict
from modes.research.reviewer import TheoremReview, IssueReport


def test_extract_citation_terms_bracket_numbers() -> None:
    text = "As shown in [1] and [12, 13]; see also Theorem 2.1 and Lemma 3.2."
    terms = rv._extract_citation_terms(text, limit=20)
    assert any(t.startswith("[") for t in terms), terms
    assert any("1]" in t or t == "[1]" for t in terms), terms


def test_extract_citation_terms_author_year() -> None:
    text = "This follows Tao (2005) and the work of Green et al."
    terms = rv._extract_citation_terms(text, limit=20)
    joined = " ".join(terms).lower()
    assert "tao" in joined or "2005" in joined or "green" in joined


@pytest.mark.asyncio
async def test_review_statement_without_proof_respects_llm_gaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 返回 gap 时，verification 不得标记为 passed（无英文引号结尾）。"""

    async def fake_chat_json(*args, **kwargs):  # noqa: ANN002, ANN003
        return {
            "overall": "has_gaps",
            "summary": "The step from n>1 to composite is not justified.",
            "issues": [
                {
                    "issue_type": "gap",
                    "description": "Concluding n is composite from n^2>n is invalid without further hypotheses.",
                    "fix_suggestion": "State and prove intermediate lemmas.",
                    "confidence": 0.8,
                }
            ],
        }

    monkeypatch.setattr(rv, "chat_json", fake_chat_json)

    tp = TheoremProofPair(
        env_type="theorem",
        ref="Test",
        statement="For every integer n>1, we have n^2>n, hence n is composite.",
        proof=None,
        source="synthetic",
        location_hint="unit-test",
    )
    verification, issues = await rv._review_statement_without_proof(tp)
    assert verification.overall == "has_gaps"
    assert len(issues) >= 1
    assert issues[0].issue_type == "gap"


@pytest.mark.asyncio
async def test_review_single_theorem_detects_critical_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """_review_single_theorem 对含 critical_error 的逻辑审查应返回 Incorrect verdict。

    使用经典错误证明：声称所有正整数均为素数（归纳跳步）。
    """

    async def fake_verify_sequential(proof_text: str, statement: str, **kwargs):
        return VerificationResult(
            steps=[
                StepVerdict(step_num=1, text="Base: 1 is prime.", verdict="critical_error",
                            reason="1 is not a prime by definition."),
                StepVerdict(step_num=2, text="Induction step is vacuously satisfied.", verdict="gap",
                            reason="Vacuous induction does not establish the claim."),
            ],
            overall="critical_error",
            summary="The base case is wrong: 1 is not prime.",
        )

    monkeypatch.setattr(rv, "verify_sequential", fake_verify_sequential)

    tp = TheoremProofPair(
        env_type="theorem",
        ref="Bad Theorem",
        statement="Every positive integer is prime.",
        proof="Proof by induction: 1 is prime (base case). If n is prime, n+1 is prime (inductive step). QED.",
        source="synthetic-flawed",
        location_hint="unit-test-error",
    )
    review = await rv._review_single_theorem(tp, 1, check_logic=True, check_citations=False, check_symbols=False)
    assert review.verdict == "Incorrect", f"Expected Incorrect, got {review.verdict}"
    assert any(i.issue_type == "critical_error" for i in review.issues)
    # 置信度由 _review_confidence_from_review 计算，Incorrect → 0.15
    conf = rv._review_confidence_from_review(review)
    assert conf < 0.5, f"Expected low confidence for Incorrect verdict, got {conf}"


@pytest.mark.asyncio
async def test_review_confidence_set_in_review_and_push() -> None:
    """确认 review_paper_pages 路径设置 review_confidence（非 None/0）。

    直接测试 _review_confidence_from_review 与 TheoremReview 的交互。
    """
    # Correct + passed verification → 0.92
    tp = TheoremProofPair(
        env_type="theorem", ref="T1",
        statement="$2+2=4$.", proof="Trivially by definition.",
        source="synthetic",
    )
    verify = VerificationResult(steps=[], overall="passed", summary="trivial")
    review = TheoremReview(theorem=tp, verification=verify, citation_checks=[], issues=[], verdict="Correct")
    conf = rv._review_confidence_from_review(review)
    assert conf == 0.92, f"Expected 0.92 for Correct+passed, got {conf}"

    # Incorrect → 0.15
    review_bad = TheoremReview(
        theorem=tp,
        verification=VerificationResult(steps=[], overall="critical_error", summary="wrong"),
        citation_checks=[],
        issues=[IssueReport("T1", "critical_error", "err", "fix", 0.9)],
        verdict="Incorrect",
    )
    conf_bad = rv._review_confidence_from_review(review_bad)
    assert conf_bad == 0.15, f"Expected 0.15 for Incorrect, got {conf_bad}"
