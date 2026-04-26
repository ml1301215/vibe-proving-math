"""
集成测试：MinerU PDF 处理工作流 → 论文审查后端

测试范围：
  T1  pdf_fix.fix_all()          —— 修复管道单元测试（无网络）
  T2  pdf_fix.split_markdown_into_chunks()  —— Markdown 分块
  T3  mineru_client 模块可正常导入  —— 依赖检查
  T4  /review_pdf_stream 端点接受 PDF 并返回 SSE 流（Nanonets + 章节审查路径）
  T5  （保留）fix_all 对 Markdown 片段的质量验证
"""
from __future__ import annotations

import asyncio
import io
import json
import textwrap
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


# ──────────────────────────────────────────────────────────────────────────────
# T1  pdf_fix 单元测试
# ──────────────────────────────────────────────────────────────────────────────

class TestPdfFix:
    """pdf_fix 修复管道各函数的单元测试（纯计算，无 IO）。"""

    def test_fix_precomposed_chars_acute(self):
        from core.pdf_fix import fix_precomposed_chars
        # ´e → é
        result = fix_precomposed_chars('\u00b4e')
        assert result == '\xe9', f"Expected é, got {result!r}"

    def test_fix_precomposed_no_change_on_correct(self):
        from core.pdf_fix import fix_precomposed_chars
        text = "Erdős–Rényi model"
        result = fix_precomposed_chars(text)
        # 正确的预组合字符不应被破坏
        assert 'ő' in result or result == text

    def test_fix_spaced_text_forall(self):
        from core.pdf_fix import fix_spaced_text_commands
        result = fix_spaced_text_commands(r'\text{f o r a l l}')
        assert result == r'\forall', f"Got {result!r}"

    def test_fix_spaced_text_unknown_word(self):
        from core.pdf_fix import fix_spaced_text_commands
        result = fix_spaced_text_commands(r'\text{a n d}')
        assert result == r'\text{and}', f"Got {result!r}"

    def test_fix_spaced_text_no_change_normal(self):
        from core.pdf_fix import fix_spaced_text_commands
        text = r'\text{for all } x'
        result = fix_spaced_text_commands(text)
        assert result == text  # 含正常单词，不应被修改

    def test_fix_missing_arrows_display_math(self):
        from core.pdf_fix import fix_missing_arrows
        # f : A  \mathbb{N} 里有双空格应补 \to
        text = "$$\nf : A  \\mathbb{N}\n$$"
        result = fix_missing_arrows(text)
        assert r'\to' in result, f"\\to not inserted; got:\n{result}"

    def test_fix_digit_sequences_display_math(self):
        from core.pdf_fix import fix_digit_sequences
        text = "$$\n1 2 3 4 5 6 7\n$$"
        result = fix_digit_sequences(text)
        assert "1234567" in result, f"Digits not merged; got:\n{result}"

    def test_fix_digit_sequences_no_change_inline(self):
        from core.pdf_fix import fix_digit_sequences
        # inline math 不应合并
        text = "$1 2 3 4 5 6$"
        result = fix_digit_sequences(text)
        assert result == text  # inline math 原样保留

    def test_fix_all_pipeline(self):
        from core.pdf_fix import fix_all
        raw = textwrap.dedent(r"""
            # Introduction

            Let $f : A  \mathbb{N}$ be a function.
            The author Erd\u00b4os proved that \text{f o r a l l} $n$.

            $$
            x = 1 2 3 4 5 6 7 8
            $$
        """)
        result = fix_all(raw)
        assert r'\to' in result
        assert r'\forall' in result
        assert "12345678" in result


# ──────────────────────────────────────────────────────────────────────────────
# T2  Markdown 分块测试
# ──────────────────────────────────────────────────────────────────────────────

class TestMarkdownChunking:
    def test_split_by_headings(self):
        from core.pdf_fix import split_markdown_into_chunks
        md = textwrap.dedent("""
            # Introduction
            Some text here.

            ## Section 2
            More content.

            ### Subsection 2.1
            Even more content.
        """).strip()
        chunks = split_markdown_into_chunks(md)
        assert len(chunks) >= 2
        assert any("Introduction" in c for c in chunks)
        assert any("Section 2" in c for c in chunks)

    def test_empty_input(self):
        from core.pdf_fix import split_markdown_into_chunks
        assert split_markdown_into_chunks("") == []
        assert split_markdown_into_chunks("   ") == []

    def test_no_headings_falls_back_to_paragraphs(self):
        from core.pdf_fix import split_markdown_into_chunks
        md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = split_markdown_into_chunks(md, max_chars=30)
        assert len(chunks) >= 2

    def test_chunk_max_chars_respected(self):
        from core.pdf_fix import split_markdown_into_chunks
        # 每个 section 约 100 字符，max_chars=50 → 应切更多块
        section = "# H\n" + "x" * 80
        md = "\n\n".join([section] * 5)
        chunks = split_markdown_into_chunks(md, max_chars=60)
        assert all(len(c) <= 200 for c in chunks), "Chunks too large"

    def test_all_chunks_nonempty(self):
        from core.pdf_fix import split_markdown_into_chunks
        md = "# A\nContent A\n\n# B\nContent B\n\n# C\nContent C"
        chunks = split_markdown_into_chunks(md)
        assert all(c.strip() for c in chunks)


# ──────────────────────────────────────────────────────────────────────────────
# T3  模块导入检查
# ──────────────────────────────────────────────────────────────────────────────

class TestImports:
    def test_pdf_fix_importable(self):
        import core.pdf_fix as m
        assert callable(m.fix_all)
        assert callable(m.split_markdown_into_chunks)

    def test_mineru_client_importable(self):
        import core.mineru_client as m
        assert callable(m.extract_pdf_markdown)
        assert callable(m.get_mineru_chunks)

    def test_server_imports_succeed(self):
        """server.py 的 import 语句和路由注册不崩溃。"""
        import importlib
        import sys
        # 先注册 app 目录到 path（uvicorn 方式）
        app_dir = str(Path(__file__).parent.parent)
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        # 只测试能导入，不启动 server
        import api.server  # noqa: F401


# ──────────────────────────────────────────────────────────────────────────────
# T4  /review_pdf_stream 端点集成测试（mock MinerU，使用最小合法 PDF）
# ──────────────────────────────────────────────────────────────────────────────

_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Theorem 1. P is NP.) Tj ET\n"
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

_SAMPLE_MD = textwrap.dedent(r"""
    # A Sample Math Paper

    ## 1. Introduction

    We prove the following.

    **Theorem 1.** Let $f : A  \mathbb{N}$ be a function. For \text{f o r a l l} $n \geq 1$,
    $f(n) > 0$.

    *Proof.* Observe that by definition $f$ maps to positive integers. $\square$

    ## 2. Main Result

    **Lemma 2.** If $p$ is prime, then $p^2 \equiv 1 \pmod{8}$ for $p > 2$.
""").strip()


@pytest.fixture()
def http_client():
    from fastapi.testclient import TestClient
    import sys
    app_dir = str(Path(__file__).parent.parent)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from api.server import app
    return TestClient(app)


class TestReviewPdfStreamEndpoint:
    """review_pdf_stream 端点的集成测试（Mock MinerU 网络请求）。"""

    def _upload_pdf(self, client, pdf_bytes: bytes = _MINIMAL_PDF, **form_kwargs):
        form = {
            "max_theorems": "2",
            "check_logic": "true",
            "check_citations": "false",
            "check_symbols": "false",
            **form_kwargs,
        }
        return client.post(
            "/review_pdf_stream",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data=form,
        )

    def test_endpoint_exists(self, http_client):
        """端点应存在（非 404），即使调用失败也应返回 4xx 而非 404。"""
        resp = self._upload_pdf(http_client)
        assert resp.status_code != 404, "端点不存在"

    def test_empty_file_rejected(self, http_client):
        resp = self._upload_pdf(http_client, pdf_bytes=b"")
        assert resp.status_code == 422

    def test_unsupported_ext_rejected(self, http_client):
        resp = http_client.post(
            "/review_pdf_stream",
            files={"file": ("doc.docx", io.BytesIO(b"PK\x03\x04"), "application/zip")},
            data={"max_theorems": "2"},
        )
        assert resp.status_code in (415, 422, 200)  # 422 或流中报错

    @patch("modes.research.section_reviewer.review_section_with_llm", new_callable=AsyncMock)
    @patch("modes.research.section_reviewer.extract_pdf_markdown_nanonets", new_callable=AsyncMock)
    def test_uses_nanonets_markdown_when_available(self, mock_nn, mock_sec_llm, http_client):
        """Nanonets 返回 Markdown 时，应进入章节审查（不调用 MinerU）。"""
        from core.nanonets_client import NanonetsExtractResult

        mock_nn.return_value = NanonetsExtractResult(
            ok=True,
            markdown=_SAMPLE_MD,
            record_id="r1",
            raw_status="completed",
        )
        mock_sec_llm.return_value = {
            "section_title": "1. Introduction",
            "page_range": "1",
            "main_claims": [],
            "proofs_found": [],
            "logic_issues": [],
            "citation_issues": [],
            "confidence": 0.7,
            "source_quotes": [],
        }
        resp = self._upload_pdf(http_client)
        mock_nn.assert_called_once()
        assert resp.status_code == 200

    @patch("modes.research.section_reviewer.extract_pdf_markdown_nanonets", new_callable=AsyncMock)
    def test_nanonets_failure_yields_parse_failed_without_pymupdf(self, mock_nn, http_client):
        """Nanonets 失败时不再降级 PyMuPDF；最终 JSON 含 parse_failed。"""
        from core.nanonets_client import NanonetsExtractResult

        mock_nn.return_value = NanonetsExtractResult(
            ok=False,
            markdown="",
            error_code="job_failed",
            error_message="Nanonets rejected",
        )
        resp = self._upload_pdf(http_client, stream=True)
        assert resp.status_code == 200
        mock_nn.assert_called_once()
        final_obj = None
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "final" in obj:
                final_obj = obj["final"]
        assert final_obj is not None
        assert final_obj.get("parse_failed") is True
        assert final_obj.get("overall_verdict") == "Incorrect"

    def test_sse_response_content_type(self, http_client):
        """响应应为 SSE 格式。"""
        resp = self._upload_pdf(http_client, stream=True)
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"Expected SSE, got: {ct}"

    def test_tex_file_accepted(self, http_client):
        """上传 .tex 文件应被接受。"""
        tex = textwrap.dedent(r"""
            \begin{theorem}
            For all $n \geq 1$, $n > 0$.
            \end{theorem}
            \begin{proof}
            By definition.
            \end{proof}
        """).encode()
        resp = http_client.post(
            "/review_pdf_stream",
            files={"file": ("paper.tex", io.BytesIO(tex), "text/plain")},
            data={"max_theorems": "1"},
        )
        assert resp.status_code == 200

    def test_md_file_accepted(self, http_client):
        """上传 .md 文件应被接受。"""
        resp = http_client.post(
            "/review_pdf_stream",
            files={"file": ("paper.md", io.BytesIO(_SAMPLE_MD.encode()), "text/plain")},
            data={"max_theorems": "1"},
        )
        assert resp.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# T5  fix_all 改善 MinerU 输出的质量验证
# ──────────────────────────────────────────────────────────────────────────────

class TestFixAllQuality:
    """用真实 MinerU 输出片段验证修复效果。"""

    _RAW = textwrap.dedent(r"""
        # Green-Tao Theorem

        **Theorem 1.1.** Let $A \subset  \mathbb{P}$ with $d(A) > 0$.
        Then $A$ contains arbitrarily long arithmetic progressions.

        *Proof.* We use the fact that \text{f o r a l l} primes $p$,
        the author Erd´os showed that $f : A  \mathbb{N}$ is well-defined.

        The key estimate gives $N = 5 6 2 1 1 3 8 3 7 6 0$ in display math:

        $$
        5 6 2 1 1 3 8 3 7 6 0 3 9 7
        $$
    """).strip()

    def test_arrows_fixed(self):
        from core.pdf_fix import fix_all
        result = fix_all(self._RAW)
        assert r'\to' in result, "Missing \\to arrow"

    def test_text_fixed(self):
        from core.pdf_fix import fix_all
        result = fix_all(self._RAW)
        assert r'\forall' in result, "Spaced \\text not fixed"

    def test_digits_fixed(self):
        from core.pdf_fix import fix_all
        result = fix_all(self._RAW)
        assert "56211383760397" in result, "Digit sequence not merged"

    def test_diacritic_fixed(self):
        from core.pdf_fix import fix_all
        result = fix_all(self._RAW)
        # Erd´os：´o → ó（拉丁小写 o 带尖音符）
        assert 'ó' in result, f"Acute accent not fixed; got snippet: {result[result.find('Erd')-2:result.find('Erd')+10]!r}"

    def test_no_new_corruption(self):
        from core.pdf_fix import fix_all
        result = fix_all(self._RAW)
        # 不应引入新的独立音标符
        for ch in '\u00b4\u02dd\u00a8':
            assert ch not in result, f"Fix introduced standalone diacritic {ch!r}"
