from __future__ import annotations

import json
from fastapi.testclient import TestClient

from api.server import app


def _collect_sse_events(resp) -> list[dict]:
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


_MINIMAL_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\n"
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


def test_review_pdf_stream_accepts_pdf_fixture(monkeypatch):
    from modes.research.section_reviewer import SectionReviewFinalReport
    from modes.research import section_reviewer as SR

    async def fake_run_pdf_nanonets_section_review(_pdf_bytes, **kwargs):
        await kwargs["progress"]("nanonets_ok", "Nanonets 解析完成（42 字符）…")
        await kwargs["result_cb"]({
            "kind": "section",
            "index": 1,
            "data": {
                "section_title": "1. Introduction",
                "page_range": "1",
                "main_claims": [],
                "proofs_found": [],
                "logic_issues": [],
                "citation_issues": [],
                "confidence": 0.9,
                "source_quotes": [],
            },
        })
        return SectionReviewFinalReport(
            source="test_paper.pdf",
            overall_verdict="Correct",
            issues=[],
            stats={"parser_source": "nanonets", "sections_checked": 1, "markdown_chars": 42},
            parse_failed=False,
            paper_title="Sample",
            sections_reviewed=1,
            scan_completed=True,
        )

    monkeypatch.setattr(SR, "run_pdf_nanonets_section_review", fake_run_pdf_nanonets_section_review)

    client = TestClient(app)
    import io as _io

    fh = _io.BytesIO(_MINIMAL_PDF_BYTES)
    with client.stream(
        "POST",
        "/review_pdf_stream",
        files={"file": ("test_paper.pdf", fh, "application/pdf")},
        data={"max_theorems": "4", "lang": "zh"},
    ) as resp:
        assert resp.status_code == 200, resp.text
        events = _collect_sse_events(resp)

    kinds = [e["kind"] for e in events]
    assert "status" in kinds
    assert "result" in kinds
    assert "final" in kinds
    assert "done" in kinds
    final = next(e["data"] for e in events if e["kind"] == "final")
    assert final["overall_verdict"] == "Correct"
    assert final["stats"]["sections_checked"] == 1
    assert final.get("mode") == "nanonets_section"


def test_review_stream_accepts_image_payloads(monkeypatch):
    from modes.research import reviewer as R
    from modes.research.parser import TheoremProofPair

    async def fake_review_paper_images(images, **kwargs):
        assert images and images[0].startswith("data:image/png;base64,")
        await kwargs["progress"]("parse_image", "正在解析图片输入（1 张）…")
        await kwargs["result_cb"]({
            "kind": "theorem",
            "index": 1,
            "data": R.TheoremReview(
                theorem=TheoremProofPair(
                    env_type="claim",
                    ref="Claim 1",
                    statement="The diagram commutes.",
                    proof=None,
                    source="image_upload",
                    location_hint="image",
                ),
                verification=None,
                citation_checks=[],
                issues=[],
                verdict="Partial",
            ).to_dict(),
        })
        return R.ReviewReport(
            source="image_upload",
            overall_verdict="Partial",
            theorem_reviews=[],
            issues=[],
            stats={"images_processed": 1, "theorems_checked": 1},
        )

    monkeypatch.setattr(R, "review_paper_images", fake_review_paper_images)

    client = TestClient(app)
    with client.stream(
        "POST",
        "/review_stream",
        json={"proof_text": "", "images": ["data:image/png;base64,AAAA"]},
    ) as resp:
        assert resp.status_code == 200, resp.text
        events = _collect_sse_events(resp)

    final = next(e["data"] for e in events if e["kind"] == "final")
    assert final["overall_verdict"] == "Partial"
    assert final["stats"]["images_processed"] == 1
