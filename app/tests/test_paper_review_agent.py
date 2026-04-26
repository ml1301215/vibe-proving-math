from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))


def _collect_sse_events(resp) -> list[dict]:
    import json

    events = []
    for line in resp.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        if raw == "[DONE]":
            events.append({"kind": "done"})
            break
        obj = json.loads(raw)
        if "status" in obj:
            events.append({"kind": "status", "step": obj.get("step"), "status": obj["status"]})
        elif "result" in obj:
            events.append({"kind": "result", "data": obj["result"]})
        elif "final" in obj:
            events.append({"kind": "final", "data": obj["final"]})
        elif "error" in obj:
            events.append({"kind": "error", "data": obj["error"]})
    return events


@pytest.mark.asyncio
async def test_classify_claims_tool_distinguishes_background_and_core():
    from modes.research.agent.models import AgentClaim
    from modes.research.agent.tools import classify_claims_tool
    from modes.research.parser import TheoremProofPair

    claims = [
        AgentClaim(
            claim_id=1,
            section_id=1,
            pair=TheoremProofPair(
                env_type="theorem",
                ref="Theorem 1",
                statement="Every finite cyclic group is abelian.",
                proof="Proof sketch",
                source="paper.pdf",
            ),
        ),
        AgentClaim(
            claim_id=2,
            section_id=1,
            pair=TheoremProofPair(
                env_type="remark",
                ref=None,
                statement="Recall that every finite set and its fixed-point set under an involution have the same parity.",
                proof=None,
                source="paper.pdf",
            ),
        ),
    ]

    out = classify_claims_tool(claims)
    assert out[0].claim_kind == "core_result"
    assert out[1].claim_kind == "background_fact"


@pytest.mark.asyncio
async def test_classify_claims_tool_downgrades_definitions():
    from modes.research.agent.models import AgentClaim
    from modes.research.agent.tools import classify_claims_tool
    from modes.research.parser import TheoremProofPair

    claims = [
        AgentClaim(
            claim_id=1,
            section_id=1,
            pair=TheoremProofPair(
                env_type="definition",
                ref="Definition 1",
                statement="Let $(\\Omega, \\mathcal{F}, \\mathbb{P})$ be a probability space.",
                proof=None,
                source="paper.pdf",
            ),
        )
    ]

    out = classify_claims_tool(claims)
    assert out[0].claim_kind == "background_fact"


@pytest.mark.asyncio
async def test_parse_pdf_primary_tool_uses_docling_pages_and_quality_gate(monkeypatch):
    from modes.research.agent import tools as T

    monkeypatch.setattr(
        T,
        "_docling_extract_page_texts",
        lambda _: [
            "Theorem 1. Let G be a finite group. Assume H is a subgroup. Proof. We proceed by induction on the order of G.",
            "x",
        ],
    )

    ctx = await T.parse_pdf_primary_tool(b"%PDF-1.4", source="paper.pdf")

    assert ctx.parser_source == "docling"
    assert ctx.page_texts[0].startswith("Theorem 1.")
    assert 2 in ctx.low_confidence_pages
    assert 0.0 <= ctx.quality_score <= 1.0


@pytest.mark.asyncio
async def test_parse_pdf_fallback_tool_replaces_low_conf_pages(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.agent import tools as T
    from modes.research.agent.models import AgentReviewContext

    page_texts = ["good page", "x"]
    structured = R.build_structured_document(page_texts, source="paper.pdf")
    sections = T._sections_from_document(
        structured,
        parser_source="pipeline",
        low_confidence_pages=[2],
        quality_score=0.4,
    )
    context = AgentReviewContext(
        source="paper.pdf",
        pdf_bytes=b"%PDF-1.4",
        page_texts=list(page_texts),
        structured_document=structured,
        sections=sections,
        parser_source="pipeline",
        quality_score=0.4,
        low_confidence_pages=[2],
    )

    monkeypatch.setenv("MATHPIX_APP_ID", "demo")
    monkeypatch.setenv("MATHPIX_APP_KEY", "demo")

    async def fake_mathpix(pdf_bytes, *, source, page_num):
        assert page_num == 2
        return "Recovered theorem page from OCR."

    monkeypatch.setattr(T, "_try_mathpix_page_ocr", fake_mathpix)

    out = await T.parse_pdf_fallback_tool(context, pages_to_retry=[2])

    assert out.fallback_pages == [2]
    assert out.page_texts[1] == "Recovered theorem page from OCR."
    assert out.parser_source == "mathpix"
    assert 2 not in out.low_confidence_pages


def test_alignment_layer_matches_citation_markers():
    from modes.research.agent.alignment import align_grobid_citations, build_parsed_pages_from_texts

    pages = build_parsed_pages_from_texts(
        ["Theorem. By [12], the result follows."],
        parser_source="pipeline",
    )
    aligned = align_grobid_citations(
        pages,
        {"[12]": {"title": "Sample reference", "doi": "10.1/demo", "callout": "[12]"}},
    )

    assert aligned
    assert aligned[0].page_num == 1
    assert aligned[0].alignment_score >= 1.0
    assert aligned[0].title == "Sample reference"


def test_quality_metrics_detect_broken_formula_and_noise():
    from modes.research.agent.alignment import build_parsed_pages_from_texts
    from modes.research.agent.quality import evaluate_document_quality

    parsed_pages = build_parsed_pages_from_texts(
        ["IV\nx", "Theorem 1. Let $x^2 + y^2 = z^2 and continue"],
        parser_source="pipeline",
    )
    quality_score, low_conf_pages, page_scores = evaluate_document_quality(parsed_pages)

    assert low_conf_pages
    assert page_scores[2].formula_break_ratio > 0
    assert 0.0 <= quality_score <= 1.0


@pytest.mark.asyncio
async def test_resolve_citations_tool_enriches_claims_from_grobid(monkeypatch):
    from modes.research.agent import tools as T
    from modes.research.agent.models import AgentClaim, AgentReviewContext
    from modes.research.parser import TheoremProofPair
    from modes.research import reviewer as R

    structured = R.build_structured_document(["Theorem. By [1], the result follows."], source="paper.pdf")
    sections = T._sections_from_document(
        structured,
        parser_source="pipeline",
        low_confidence_pages=[],
        quality_score=0.9,
    )
    context = AgentReviewContext(
        source="paper.pdf",
        pdf_bytes=b"%PDF-1.4",
        page_texts=["Theorem. By [1], the result follows."],
        structured_document=structured,
        sections=sections,
    )
    claim = AgentClaim(
        claim_id=1,
        section_id=1,
        pair=TheoremProofPair(
            env_type="theorem",
            ref="Theorem 1",
            statement="A theorem.",
            proof="By [1], done.",
            source="paper.pdf",
            local_citations=["[1]"],
        ),
    )

    async def fake_grobid(pdf_bytes, *, source):
        return {"[1]": {"title": "Parity theorem", "doi": "10.1000/demo"}}

    monkeypatch.setattr(T, "_try_grobid_fulltext", fake_grobid)

    mapping = await T.resolve_citations_tool(context, [claim])

    assert mapping["[1]"]["title"] == "Parity theorem"
    assert "Parity theorem" in claim.pair.local_citations
    assert "10.1000/demo" in claim.pair.local_citations


@pytest.mark.asyncio
async def test_run_paper_review_agent_emits_extended_stats(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.agent import orchestrator as O
    from modes.research.agent.models import AgentClaim, AgentReviewContext, AgentSection
    from modes.research.parser import TheoremProofPair

    page_texts = ["Theorem 1. Every prime p > 2 is odd. Proof.", "Background fact."]
    structured = R.build_structured_document(page_texts, source="paper.pdf")
    sections = [
        AgentSection(
            unit_id=unit.unit_id,
            section_title=unit.section_title,
            section_path=unit.section_path,
            page_start=unit.page_start,
            page_end=unit.page_end,
            raw_text=unit.raw_text,
            parser_source="docling",
            quality_score=0.91,
            context_before=unit.context_before,
            context_after=unit.context_after,
            local_definitions=list(unit.local_definitions),
            local_citations=list(unit.local_citations),
        )
        for unit in structured.sections
    ]
    context = AgentReviewContext(
        source="paper.pdf",
        pdf_bytes=b"%PDF-1.4",
        page_texts=page_texts,
        structured_document=structured,
        sections=sections,
        parser_source="docling",
        quality_score=0.91,
        low_confidence_pages=[2],
        fallback_pages=[2],
    )

    async def fake_parse_primary(*args, **kwargs):
        return context

    async def fake_parse_fallback(ctx, **kwargs):
        return ctx

    async def fake_extract_batches(ctx, **kwargs):
        yield [
            AgentClaim(
                claim_id=1,
                section_id=sections[0].unit_id,
                claim_kind="core_result",
                parser_source="docling",
                quality_score=0.91,
                pair=TheoremProofPair(
                    env_type="theorem",
                    ref="Theorem 1",
                    statement="Every prime $p > 2$ is odd.",
                    proof="Proof sketch",
                    source="paper.pdf",
                    location_hint="section 1 (page 1)",
                    page_span="page 1",
                    parser_source="docling",
                    quality_score=0.91,
                ),
            )
        ]

    async def fake_resolve(ctx, claims):
        return {"[1]": {"title": "Example Reference"}}

    async def fake_verify(claim, *, idx, **kwargs):
        review = R.TheoremReview(
            theorem=claim.pair,
            verification=None,
            citation_checks=[],
            issues=[],
            verdict="Correct",
        )
        claim.review_confidence = 0.88
        review.theorem.review_confidence = 0.88
        return claim, review

    progress_steps = []
    results = []

    async def on_progress(step, msg):
        progress_steps.append(step)

    async def on_result(payload):
        results.append(payload)

    monkeypatch.setattr(O, "parse_pdf_primary_tool", fake_parse_primary)
    monkeypatch.setattr(O, "parse_pdf_fallback_tool", fake_parse_fallback)
    monkeypatch.setattr(O, "extract_claim_batches_tool", fake_extract_batches)
    monkeypatch.setattr(O, "resolve_citations_tool", fake_resolve)
    monkeypatch.setattr(O, "verify_claim_tool", fake_verify)

    report = await O.run_paper_review_agent(
        b"%PDF-1.4",
        source="paper.pdf",
        max_theorems=2,
        progress=on_progress,
        result_cb=on_result,
    )

    assert "parse_pdf" in progress_steps
    assert results and results[0]["kind"] == "theorem"
    assert report.stats["agent_mode"] is True
    assert report.stats["claims_classified"] == 1
    assert report.stats["fallback_pages"] == 1
    assert report.stats["citation_map_size"] == 1
    assert report.theorem_reviews[0].to_dict()["parser_source"] == "docling"
    assert report.theorem_reviews[0].to_dict()["claim_kind"] == "core_result"


def test_review_pdf_stream_uses_nanonets_section_pipeline(monkeypatch):
    import io as _io

    from api.server import app
    from modes.research.section_reviewer import SectionReviewFinalReport
    from modes.research import section_reviewer as SR

    _minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hi) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000274 00000 n \n"
        b"0000000368 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n441\n%%EOF"
    )

    async def fake_run_pdf_nanonets_section_review(pdf_bytes, **kwargs):
        await kwargs["progress"]("nanonets", "正在通过 Nanonets OCR 解析 PDF…")
        await kwargs["result_cb"]({
            "kind": "section",
            "index": 1,
            "data": {
                "section_title": "Main",
                "page_range": "1",
                "main_claims": [
                    {
                        "role": "theorem",
                        "statement": "Test claim.",
                        "proof_present": True,
                        "verification_status": "verified",
                        "verdict": "Correct",
                        "source_quote": "Test claim.",
                    }
                ],
                "proofs_found": [],
                "logic_issues": [],
                "citation_issues": [],
                "confidence": 0.8,
                "source_quotes": [],
            },
        })
        return SectionReviewFinalReport(
            source="test_paper.pdf",
            overall_verdict="Correct",
            issues=[],
            stats={"parser_source": "nanonets", "sections_checked": 1},
            parse_failed=False,
            paper_title="T",
            sections_reviewed=1,
            scan_completed=True,
        )

    monkeypatch.setattr(SR, "run_pdf_nanonets_section_review", fake_run_pdf_nanonets_section_review)

    client = TestClient(app)
    fh = _io.BytesIO(_minimal_pdf)
    with client.stream(
        "POST",
        "/review_pdf_stream",
        files={"file": ("test_paper.pdf", fh, "application/pdf")},
        data={"mode": "agent", "max_theorems": "3", "lang": "zh"},
    ) as resp:
        assert resp.status_code == 200, resp.text
        events = _collect_sse_events(resp)

    assert any(e["kind"] == "status" and e.get("step") == "nanonets" for e in events)
    final = next(e["data"] for e in events if e["kind"] == "final")
    result = next(e["data"] for e in events if e["kind"] == "result")
    assert final.get("mode") == "nanonets_section"
    assert final["stats"]["parser_source"] == "nanonets"
    assert result["kind"] == "section"


def test_health_reports_paper_review_agent_tools(monkeypatch):
    from api.server import app
    from modes.research.agent import tools as T

    async def fake_health():
        return {
            "docling": {"status": "ok"},
            "grobid": {"status": "configured"},
            "mathpix": {"status": "disabled"},
            "mistral_ocr": {"status": "disabled"},
        }

    monkeypatch.setattr(T, "check_agent_tool_health", fake_health)

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "paper_review_agent" in body["dependencies"]
    assert body["dependencies"]["paper_review_agent"]["docling"]["status"] == "ok"


def test_grobid_base_url_can_use_public_demo(monkeypatch):
    from modes.research.agent import tools as T

    monkeypatch.delenv("VP_GROBID_URL", raising=False)
    monkeypatch.setenv("VP_GROBID_USE_PUBLIC_DEMO", "1")

    url = T._grobid_base_url()
    assert "hf.space" in url


@pytest.mark.asyncio
async def test_agent_health_treats_public_grobid_demo_as_configured(monkeypatch):
    from modes.research.agent import tools as T

    monkeypatch.delenv("VP_GROBID_URL", raising=False)
    monkeypatch.setenv("VP_GROBID_USE_PUBLIC_DEMO", "1")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            raise httpx.ConnectTimeout("timeout")

    import httpx
    monkeypatch.setattr(T.httpx, "AsyncClient", DummyClient)

    health = await T.check_agent_tool_health()
    assert health["grobid"]["status"] == "configured"
    assert health["grobid"]["source"] == "public_demo"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "lll_elementary_2026_arxiv.pdf",
        "szemeredi_finitary_2004_arxiv.pdf",
        "proof_course_notes_2026_arxiv.pdf",
        "green_tao_primes_ap_2008_annals.pdf",
        "sphere_packing_24_2017_annals.pdf",
    ],
)
@pytest.mark.slow
@pytest.mark.asyncio
async def test_primary_parser_handles_fixture_corpus(monkeypatch, fixture_name):
    from modes.research.agent import tools as T

    fixture = Path(__file__).resolve().parent / "fixtures" / "paper_review_pdfs" / fixture_name
    if not fixture.is_file():
        pytest.skip(
            f"未找到 PDF fixture: {fixture_name}。"
            "开源仓库不包含版权论文 PDF；请将文件放入 tests/fixtures/paper_review_pdfs/ 后使用 pytest -m slow 运行。"
        )

    # 在 pytest 中避免真实跑 Docling 的多线程推理，防止 Windows/PyTorch 底层崩溃。
    monkeypatch.setattr(T, "_docling_extract_page_texts", lambda _: None)

    ctx = await T.parse_pdf_primary_tool(fixture.read_bytes(), source=fixture_name)

    assert ctx.page_texts
    assert ctx.sections
    assert ctx.parsed_pages
    assert "page_quality" in ctx.parser_details
