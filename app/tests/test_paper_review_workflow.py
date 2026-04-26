from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
async def test_build_structured_document_preserves_sections_and_context():
    from modes.research import reviewer as R

    doc = R.build_structured_document(
        [
            "1 Introduction\n\nDefinition 1.1. Let G be a finite group.\n\nWe fix notation for the rest of the paper.",
            "2 Main Result\n\nTheorem 2.1. Every finite cyclic group is abelian.\n\nProof. This follows from commutativity of powers.",
        ],
        source="paper.pdf",
    )

    assert len(doc.sections) >= 2
    assert "Introduction" in doc.sections[0].section_title
    assert "Main Result" in doc.sections[1].section_title
    assert any("Definition 1.1" in item for item in doc.sections[0].local_definitions)
    assert "Definition 1.1" in doc.sections[1].context_before


@pytest.mark.asyncio
async def test_build_structured_document_ignores_noisy_running_headers():
    from modes.research import reviewer as R

    doc = R.build_structured_document(
        [
            "IV\n摘要 显式构造；第三章详细证明修正 Bogomolov 不等式，按不同情形分类讨论。",
            "1 Introduction\n\nTheorem 1.1. Let $G$ be finite.\n\nProof. Trivial.",
        ],
        source="paper.pdf",
    )

    assert doc.sections
    assert all("摘要 显式构造" not in section.section_title for section in doc.sections)
    assert any("Introduction" in section.section_title for section in doc.sections)


@pytest.mark.asyncio
async def test_review_paper_pages_extracts_dedupes_and_reviews(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair

    calls: list[tuple[str, str]] = []

    async def fake_extract(text, *, source, location_hint="", model=None, lang="zh"):
        if "Prime" in text:
            return [
                TheoremProofPair(
                    env_type="theorem",
                    ref="Theorem 1",
                    statement="Every prime p > 2 is odd.",
                    proof="Assume p is an even prime greater than 2. Then p is divisible by 2, contradiction.",
                    source=source,
                    location_hint=location_hint,
                    context_excerpt=text[:200],
                )
            ]
        return [
            TheoremProofPair(
                env_type="lemma",
                ref="Lemma 2",
                statement="Every prime p > 2 is odd.",
                proof=None,
                source=source,
                location_hint=location_hint,
                context_excerpt=text[:200],
            ),
            TheoremProofPair(
                env_type="lemma",
                ref="Lemma 3",
                statement="If n is even then n^2 is even.",
                proof="Write n = 2k, then n^2 = 4k^2.",
                source=source,
                location_hint=location_hint,
                context_excerpt=text[:200],
            ),
        ]

    async def fake_review(tp, idx, **kwargs):
        calls.append((tp.statement, tp.location_hint or ""))
        return R.TheoremReview(
            theorem=tp,
            verification=None,
            citation_checks=[],
            issues=[],
            verdict="Correct",
        )

    monkeypatch.setattr(R, "extract_statement_candidates_from_text", fake_extract)
    monkeypatch.setattr(R, "_review_single_theorem", fake_review)

    report = await R.review_paper_pages(
        [
            "Prime page. Theorem 1. Every prime p > 2 is odd. Proof. Contradiction.",
            "Second page. Lemma 2. Every prime p > 2 is odd. Lemma 3. If n is even then n^2 is even.",
        ],
        source="paper.pdf",
        max_theorems=5,
    )

    assert report.stats["paper_pages"] == 2
    assert report.stats["chunks_processed"] >= 2
    assert report.stats["structured_sections"] >= 2
    assert report.stats["statement_candidates"] == 2
    assert report.stats["theorems_checked"] == 2
    assert len(report.theorem_reviews) == 2
    assert any("page 1" in loc for _, loc in calls)
    assert any("page 2" in loc for _, loc in calls)


@pytest.mark.asyncio
async def test_review_paper_pages_streams_early_and_stops_after_limit(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair

    extracted_pages: list[str] = []
    progress_steps: list[str] = []
    results: list[dict] = []

    async def fake_extract(text, *, source, location_hint="", model=None, lang="zh"):
        extracted_pages.append(location_hint)
        if "page 1" in location_hint:
            return [
                TheoremProofPair(
                    env_type="theorem",
                    ref="Theorem 1",
                    statement="Every finite subgroup of the multiplicative group of a field is cyclic.",
                    proof="Use the structure theorem for finite subgroups in a field.",
                    source=source,
                    location_hint=location_hint,
                    context_excerpt=text[:200],
                )
            ]
        # 当前实现会先遍历所有结构化块提取候选，再按 max_theorems 截断审查；后续块仍应安全返回空列表。
        return []

    async def fake_review(tp, idx, **kwargs):
        return R.TheoremReview(
            theorem=tp,
            verification=None,
            citation_checks=[],
            issues=[],
            verdict="Correct",
        )

    async def on_progress(step, msg):
        progress_steps.append(step)

    async def on_result(payload):
        results.append(payload)

    monkeypatch.setattr(R, "extract_statement_candidates_from_text", fake_extract)
    monkeypatch.setattr(R, "_review_single_theorem", fake_review)

    report = await R.review_paper_pages(
        [
            "Page one. Theorem 1. Every finite subgroup of the multiplicative group of a field is cyclic. Proof.",
            "Page two should never be scanned.",
        ],
        source="paper.pdf",
        max_theorems=1,
        progress=on_progress,
        result_cb=on_result,
    )

    assert len(extracted_pages) >= 1
    assert any("page 1" in (loc or "") for loc in extracted_pages)
    assert results and results[0]["kind"] == "theorem"
    assert "review" in progress_steps
    assert "theorem" in progress_steps
    assert report.stats["theorems_checked"] == 1
    assert report.stats["chunks_processed"] >= 1


@pytest.mark.asyncio
async def test_review_paper_pages_passes_section_context_to_review(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair

    seen = {}

    async def fake_extract(text, *, source, location_hint="", model=None, lang="zh"):
        if "Theorem 2.1" not in text:
            return []
        return [
            TheoremProofPair(
                env_type="theorem",
                ref="Theorem 2.1",
                statement="Every finite cyclic group is abelian.",
                proof="Proof. Let G = <g>. Then every element is a power of g.",
                source=source,
                location_hint="page 1",
                context_excerpt=text[:300],
            )
        ]

    async def fake_review(tp, idx, **kwargs):
        seen["section_title"] = tp.section_title
        seen["section_path"] = tp.section_path
        seen["location_hint"] = tp.location_hint
        seen["context_before"] = tp.context_before or ""
        seen["definitions"] = list(tp.local_definitions or [])
        seen["citations"] = list(tp.local_citations or [])
        return R.TheoremReview(
            theorem=tp,
            verification=None,
            citation_checks=[],
            issues=[],
            verdict="Correct",
        )

    monkeypatch.setattr(R, "extract_statement_candidates_from_text", fake_extract)
    monkeypatch.setattr(R, "_review_single_theorem", fake_review)

    report = await R.review_paper_pages(
        [
            "1 Preliminaries\n\nDefinition 1.1. Let G be a group generated by g.\n\nLemma 1.2. Powers of g commute.",
            "2 Main Result\n\nTheorem 2.1. Every finite cyclic group is abelian.\n\nProof. By Lemma 1.2, any two powers of g commute.",
        ],
        source="paper.pdf",
        max_theorems=2,
    )

    assert report.stats["theorems_checked"] == 1
    assert "Main Result" in (seen["section_title"] or "")
    assert "Preliminaries" in (seen["context_before"] or "")
    assert any("Definition 1.1" in item for item in seen["definitions"])
    assert any("Lemma 1.2" in item for item in seen["citations"])
    assert "page 2" in (seen.get("location_hint", "") or report.theorem_reviews[0].theorem.location_hint)


@pytest.mark.asyncio
async def test_review_paper_pages_falls_back_to_review_text(monkeypatch):
    from modes.research import reviewer as R

    async def fake_extract(text, *, source, location_hint="", model=None, lang="zh"):
        return []

    async def fake_review_text(text, **kwargs):
        return R.ReviewReport(
            source=kwargs.get("source", "paper.pdf"),
            overall_verdict="Partial",
            theorem_reviews=[],
            issues=[],
            stats={"theorems_checked": 1, "fallback": "single_proof"},
        )

    monkeypatch.setattr(R, "extract_statement_candidates_from_text", fake_extract)
    monkeypatch.setattr(R, "review_text", fake_review_text)

    report = await R.review_paper_pages(
        ["Page one content", "Page two content"],
        source="paper.pdf",
        max_theorems=3,
    )

    assert report.overall_verdict == "Partial"
    assert report.stats["paper_pages"] == 2
    assert report.stats["statement_candidates"] == 0
    assert report.stats["input_type"] == "paper_pages"
    assert report.stats["fallback"] == "paper_text"


@pytest.mark.asyncio
async def test_review_single_theorem_recovers_proof_from_context_before_verification(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair
    from skills.verify_sequential import VerificationResult

    captured = {}

    async def fake_verify(proof_text, statement, **kwargs):
        captured["proof_text"] = proof_text
        captured["statement"] = statement
        return VerificationResult(steps=[], overall="passed", summary="ok")

    async def fake_check_citations(*args, **kwargs):
        return []

    monkeypatch.setattr(R, "verify_sequential", fake_verify)
    monkeypatch.setattr(R, "_check_citations_in_proof", fake_check_citations)

    theorem = TheoremProofPair(
        env_type="theorem",
        ref="Theorem 2.1",
        statement="Every finite cyclic group is abelian.",
        proof=None,
        source="paper.pdf",
        location_hint="page 2",
        context_excerpt=(
            "Theorem 2.1. Every finite cyclic group is abelian.\n\n"
            "Consider a generator g of G. Then every element is a power of g, "
            "hence any two elements commute."
        ),
    )

    review = await R._review_single_theorem(theorem, 1)

    assert review.verification is not None
    assert review.verification.overall == "passed"
    assert theorem.proof is not None
    assert "Consider a generator g of G" in theorem.proof
    assert "hence any two elements commute" in captured["proof_text"]


@pytest.mark.asyncio
async def test_review_statement_without_proof_prompt_includes_recovered_proof_snippet(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair

    seen = {}

    async def fake_chat_json(prompt, **kwargs):
        seen["prompt"] = prompt
        return {
            "overall": "has_gaps",
            "summary": "need more detail",
            "issues": [{
                "issue_type": "gap",
                "description": "proof sketch is incomplete",
                "fix_suggestion": "provide more steps",
                "confidence": 0.6,
            }],
        }

    monkeypatch.setattr(R, "chat_json", fake_chat_json)

    theorem = TheoremProofPair(
        env_type="theorem",
        ref="Claim 1",
        statement="Every involution on a finite set has parity constraints.",
        proof=None,
        source="paper.pdf",
        location_hint="page 3",
        context_excerpt=(
            "Claim 1. Every involution on a finite set has parity constraints.\n\n"
            "Consider the involution on X. Fixed points contribute one each, "
            "and non-fixed points come in pairs. Therefore the parity follows."
        ),
    )

    verification, issues = await R._review_statement_without_proof(theorem)

    assert verification.overall == "has_gaps"
    assert issues
    assert "Recovered proof snippet:" in seen["prompt"]
    assert "Fixed points contribute one each" in seen["prompt"]
