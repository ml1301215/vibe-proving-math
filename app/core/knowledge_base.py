"""Per-project 知识库 —— PDF/LaTeX/文本解析、分块、持久化、语义检索、LATRACE集成。

存储布局：
    data/kb/{project_id}/
        index.json          文档元数据索引
        {doc_id}.json       分块内容

检索策略：BM25-like 关键词加权，无需外部向量服务。
LATRACE 集成：上传时将文档摘要写入记忆，对话时自动检索相关段落。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path
from typing import Optional

_DATA_ROOT = Path(__file__).parent.parent / "data" / "kb"


# ── 文本清洗 ──────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """按段落优先、固定窗口兜底的分块策略。"""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 1 <= chunk_size:
            buf = (buf + " " + para).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= chunk_size:
                buf = para
            else:
                # 长段落强制切
                for i in range(0, len(para), chunk_size - overlap):
                    piece = para[i: i + chunk_size]
                    if piece:
                        chunks.append(piece)
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if len(c) > 40]


# ── LaTeX 解析 ────────────────────────────────────────────────────────────────

_LATEX_STRIP = re.compile(
    r"\\(?:begin|end)\{[^}]+\}"          # \begin{...} \end{...}
    r"|\\(?:label|cite|ref|bibitem|bibliography|bibliographystyle|usepackage"
    r"|documentclass|maketitle|tableofcontents|listoffigures|newcommand"
    r"|renewcommand|setcounter|vspace|hspace|noindent|indent|clearpage"
    r"|newpage|thispagestyle|pagestyle)\s*(?:\{[^}]*\}|\[[^\]]*\])*"
    r"|%[^\n]*"                           # 行注释
    r"|\\[a-zA-Z]+"                       # 其余 \cmd（保留数学内容）
)
_MATH_FENCE = re.compile(r"\$\$[\s\S]*?\$\$|\$[^$\n]*\$|\\\[[^\]]*\\\]|\\\([^)]*\\\)")


def extract_latex_text(content: bytes) -> tuple[str, int]:
    """提取 .tex 文件中的可读文本（保留数学公式、去除排版命令）。
    返回 (text, estimated_page_count)。
    """
    raw = content.decode("utf-8", errors="replace")

    # 保护数学公式：先用占位符替换
    math_blocks: list[str] = []
    def _protect(m: re.Match) -> str:
        math_blocks.append(m.group(0))
        return f"__MATH_{len(math_blocks)-1}__"
    protected = _MATH_FENCE.sub(_protect, raw)

    # 去除 LaTeX 命令
    cleaned = _LATEX_STRIP.sub(" ", protected)

    # 还原数学公式
    for i, block in enumerate(math_blocks):
        cleaned = cleaned.replace(f"__MATH_{i}__", block)

    text = _clean_text(cleaned)
    # 粗略估计页数：每 3000 字约 1 页
    page_count = max(1, len(text) // 3000)
    return text, page_count


# ── PDF 解析 ──────────────────────────────────────────────────────────────────

def _page_text_from_dict(page) -> str:
    """用 dict 模式拼接 span，尽量保留行结构；小字号 span 标为上标便于后续 LaTeX 化。"""
    try:
        td = page.get_text("dict")
    except Exception:
        return page.get_text("text") or ""

    lines_out: list[str] = []
    for block in td.get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            if not spans:
                continue
            max_sz = max((float(s.get("size") or 0) for s in spans), default=0.0) or 11.0
            parts: list[str] = []
            for s in spans:
                t = s.get("text") or ""
                if not t:
                    continue
                sz = float(s.get("size") or max_sz)
                fl = int(s.get("flags", 0))
                # PyMuPDF: flags bit0 常为 superscript；小字号 span 亦视为上标/角标
                tiny = max_sz > 1.0 and sz < max_sz * 0.86 and len(t.strip()) <= 8
                if (fl & 1) or tiny:
                    parts.append("^" + t.strip())
                elif fl & 2:
                    parts.append("_" + t.strip())
                else:
                    parts.append(t)
            lines_out.append("".join(parts))
    return "\n".join(lines_out)


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """用 PyMuPDF 提取 PDF 每一页文本（dict 模式优先，失败则纯 text）。"""
    import fitz  # pymupdf

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        out: list[str] = []
        for page in doc:
            raw = _page_text_from_dict(page)
            if not raw.strip():
                raw = page.get_text("text") or ""
            out.append(_clean_text(raw))
        return out
    finally:
        doc.close()


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    """用 pymupdf 提取 PDF 全文，返回 (text, page_count)。"""
    page_texts = extract_pdf_pages(pdf_bytes)
    return _clean_text("\n\n".join(page_texts)), len(page_texts)


def extract_text_file(content: bytes, filename: str) -> str:
    """纯文本 / Markdown 文件解析。"""
    try:
        return _clean_text(content.decode("utf-8", errors="replace"))
    except Exception:
        return ""


# ── BM25-lite 检索 ────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z一-鿿]{2,}", text.lower())


def _bm25_score(query_tokens: list[str], chunk: str, avg_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    tokens = _tokenize(chunk)
    if not tokens:
        return 0.0
    tf_map: dict[str, int] = {}
    for t in tokens:
        tf_map[t] = tf_map.get(t, 0) + 1
    dl = len(tokens)
    score = 0.0
    for qt in query_tokens:
        tf = tf_map.get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1 + 1)  # 简化：单文档内无 IDF，保持 >0
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(avg_len, 1)))
        score += idf * tf_norm
    return score


# ── KnowledgeBase ─────────────────────────────────────────────────────────────

class KnowledgeBase:
    """单个 project 的知识库实例。"""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._dir = _DATA_ROOT / project_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index: dict = self._load_index()

    # ── 持久化 ────────────────────────────────────────────────────────────────

    def _load_index(self) -> dict:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text("utf-8"))
            except Exception:
                pass
        return {"documents": {}}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── 写入 ──────────────────────────────────────────────────────────────────

    def add_document(
        self,
        filename: str,
        text: str,
        *,
        page_count: int = 0,
        file_size: int = 0,
    ) -> str:
        """分块并存储文档，返回 doc_id。若同名文档已存在则替换。"""
        # 同名覆盖
        existing_id = next(
            (did for did, meta in self._index["documents"].items() if meta["filename"] == filename),
            None,
        )
        doc_id = existing_id or uuid.uuid4().hex[:12]

        chunks = _chunk_text(text)
        doc_path = self._dir / f"{doc_id}.json"
        doc_path.write_text(
            json.dumps({"doc_id": doc_id, "filename": filename, "chunks": chunks}, ensure_ascii=False),
            encoding="utf-8",
        )

        self._index["documents"][doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "page_count": page_count,
            "file_size": file_size,
            "chunk_count": len(chunks),
            "char_count": len(text),
            "uploaded_at": int(time.time()),
        }
        self._save_index()
        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self._index["documents"]:
            return False
        doc_path = self._dir / f"{doc_id}.json"
        if doc_path.exists():
            doc_path.unlink()
        del self._index["documents"][doc_id]
        self._save_index()
        return True

    # ── 检索 ──────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5, max_chars: int = 3000) -> list[dict]:
        """检索与 query 最相关的段落，返回 [{doc_id, filename, chunk, score}]。"""
        if not self._index["documents"]:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # 收集所有 chunks 并计算平均长度
        all_chunks: list[tuple[str, str, str]] = []  # (doc_id, filename, chunk)
        for doc_id, meta in self._index["documents"].items():
            doc_path = self._dir / f"{doc_id}.json"
            if not doc_path.exists():
                continue
            try:
                doc = json.loads(doc_path.read_text("utf-8"))
                for chunk in doc.get("chunks", []):
                    all_chunks.append((doc_id, meta["filename"], chunk))
            except Exception:
                continue

        if not all_chunks:
            return []

        avg_len = sum(len(_tokenize(c)) for _, _, c in all_chunks) / len(all_chunks)

        scored = [
            {
                "doc_id": doc_id,
                "filename": fname,
                "chunk": chunk,
                "score": _bm25_score(query_tokens, chunk, avg_len),
            }
            for doc_id, fname, chunk in all_chunks
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 去重：同一文档不超过 2 段，控制 token 消耗
        result: list[dict] = []
        doc_count: dict[str, int] = {}
        total_chars = 0
        for item in scored:
            if item["score"] <= 0:
                break
            cnt = doc_count.get(item["doc_id"], 0)
            if cnt >= 2:
                continue
            if total_chars + len(item["chunk"]) > max_chars:
                break
            result.append(item)
            doc_count[item["doc_id"]] = cnt + 1
            total_chars += len(item["chunk"])
            if len(result) >= top_k:
                break
        return result

    def format_for_prompt(self, results: list[dict], *, constrained: bool = False) -> str:
        """将检索结果格式化为注入 prompt 的上下文。

        constrained=True 时加入"仅基于知识库回答"的约束指令，
        适用于用户明确要求限制在知识库范围内回答的场景。
        """
        if not results:
            return ""
        lines = []
        if constrained:
            lines.append(
                "IMPORTANT: Answer ONLY based on the following knowledge base excerpts. "
                "If the answer cannot be found in the excerpts, say so explicitly rather than guessing.\n"
            )
        lines.append("【项目知识库 — 相关内容】")
        for r in results:
            lines.append(f"\n[来源：{r['filename']}]")
            lines.append(r["chunk"])
        return "\n".join(lines)

    def list_documents(self) -> list[dict]:
        return sorted(
            self._index["documents"].values(),
            key=lambda x: x.get("uploaded_at", 0),
            reverse=True,
        )

    @property
    def has_documents(self) -> bool:
        return bool(self._index["documents"])


# ── 工厂 ──────────────────────────────────────────────────────────────────────
_kb_cache: dict[str, KnowledgeBase] = {}


def get_kb(project_id: str) -> KnowledgeBase:
    if project_id not in _kb_cache:
        _kb_cache[project_id] = KnowledgeBase(project_id)
    return _kb_cache[project_id]
