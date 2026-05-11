"""技能：search_theorems —— 搜索相关定理并过滤/格式化结果。

参考：Rethlas `search-math-results/SKILL.md`
实现：直接调用 TheoremSearch POST /search，返回结构化结果。

输入：
    query        (str)  自然语言数学问题或关键词
    top_k        (int)  返回条数，默认 8
    min_sim      (float) 最低相似度阈值，默认 0.0

输出：
    List[TheoremMatch]  按 similarity 降序排列
    TheoremMatch: {
        name: str
        body: str         定理正文
        slogan: str       一句话描述
        similarity: float
        score: float
        link: str         来源链接（可能为空）
        paper_title: str
        paper_authors: list[str]
    }
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, asdict
from typing import Optional

from core.theorem_search import search_theorems as _raw_search
from core.matlas_search import search_matlas as _matlas_search
from core.text_sanitize import strip_non_math_latex


# ── 数据清洗（去除 LaTeX 排版残留与噪声）────────────────────────────────────────
_LATEX_NOISE_PATTERNS = [
    re.compile(r"\\verb\|[^|]*\|"),                 # \verb|...|
    re.compile(r"\\verb\+[^+]*\+"),                 # \verb+...+
    re.compile(r"\\verb!([^!]*)!"),                 # \verb!...!
    # 只删除文档结构相关的环境，保留数学环境（如equation, align, sequence等）
    re.compile(r"\\begin\{(?:document|abstract|center|flushleft|flushright|minipage|figure|table|tabular|verbatim|comment)\*?\}"),
    re.compile(r"\\end\{(?:document|abstract|center|flushleft|flushright|minipage|figure|table|tabular|verbatim|comment)\*?\}"),
    re.compile(r"\\(?:label|cite|ref|footnote|index)\{[^}]*\}"),
    re.compile(r"%[^\n]*"),                          # LaTeX 行内注释
]
_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINE_RE = re.compile(r"\n{3,}")


def _clean_latex_noise(text: str) -> str:
    """去除 \\verb 标记、文档结构环境残留、注释等无意义 LaTeX 噪声。

    保留数学环境命令（如 \\begin{equation}, \\sequence 等），
    只删除文档结构相关的环境（如 \\begin{document}, \\begin{abstract} 等）。
    """
    if not text:
        return text
    out = text
    for pat in _LATEX_NOISE_PATTERNS:
        out = pat.sub(" ", out)
    out = _WHITESPACE_RE.sub(" ", out)
    out = _NEWLINE_RE.sub("\n\n", out).strip()
    return out


def _safe_float(v, default: float = 0.0) -> float:
    """安全将值转为 float，处理 None / 非数字字符串（如 "N/A"）。"""
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


@dataclass
class TheoremMatch:
    name: str
    body: str
    slogan: str
    similarity: float
    score: float
    link: str
    paper_title: str
    paper_authors: list[str]
    source: str = "theorem_search"

    def to_dict(self) -> dict:
        data = asdict(self)
        # 定理陈述里经常含裸 LaTeX。不要在后端剥离数学命令，否则前端会显示残缺陈述。
        # 标题和论文元数据仍做轻量清洗，避免文档环境噪声。
        data["name"] = strip_non_math_latex(data["name"])
        data["paper_title"] = strip_non_math_latex(data["paper_title"])
        data["paper_authors"] = [strip_non_math_latex(a) for a in self.paper_authors]
        return data

    def to_citation(self) -> str:
        """生成引用文本，用于注入 LLM prompt。"""
        auth = ", ".join(self.paper_authors[:2])
        if len(self.paper_authors) > 2:
            auth += " et al."
        title_part = f'"{self.paper_title}"' if self.paper_title else "Unknown Paper"
        link_part = f" ({self.link})" if self.link else ""
        return f"[{self.name}] {self.slogan or self.body[:120]}... — {auth}, {title_part}{link_part}"


async def search_theorems(
    query: str,
    *,
    top_k: int = 8,
    min_sim: float = 0.0,
) -> list[TheoremMatch]:
    """搜索定理并返回结构化 TheoremMatch 列表。"""
    raw = await _raw_search(query, top_k=top_k, min_similarity=min_sim)
    results: list[TheoremMatch] = []

    for r in raw:
        if not isinstance(r, dict):
            continue  # 跳过非 dict 条目，防止上游数据污染导致崩溃
        paper = r.get("paper") or {}
        if not isinstance(paper, dict):
            paper = {}
        tm = TheoremMatch(
            name=_clean_latex_noise(r.get("name", "")),
            body=_clean_latex_noise(r.get("body", "")),
            slogan=_clean_latex_noise(r.get("slogan", "")),
            similarity=_safe_float(r.get("similarity")),
            score=_safe_float(r.get("score")),
            link=r.get("link") or paper.get("link", ""),
            paper_title=_clean_latex_noise(paper.get("title", "")),
            paper_authors=paper.get("authors") if isinstance(paper.get("authors"), list) else [],
            source="theorem_search",
        )
        results.append(tm)

    matlas_raw = await _matlas_search(query, top_k=max(top_k, 10))
    for idx, r in enumerate(matlas_raw):
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or r.get("name") or "Matlas result").strip()
        entity_name = str(r.get("entity_name") or "").strip()
        statement = str(r.get("statement") or r.get("body") or r.get("abstract") or "").strip()
        raw_authors = r.get("authors")
        if isinstance(raw_authors, list):
            authors = [str(a) for a in raw_authors]
        elif isinstance(raw_authors, str):
            authors = [a.strip() for a in raw_authors.split(",") if a.strip()]
        else:
            authors = []
        year = str(r.get("year") or "").strip()
        doi = str(r.get("doi") or "").strip()
        url = str(r.get("url") or r.get("link") or "").strip()
        if doi and not url:
            url = f"https://doi.org/{doi}"
        slogan_parts = [p for p in (year, doi) if p]
        tm = TheoremMatch(
            name=_clean_latex_noise(entity_name or title),
            body=_clean_latex_noise(statement),
            slogan=_clean_latex_noise(" · ".join(slogan_parts)),
            similarity=_safe_float(r.get("similarity") or r.get("score"), max(0.0, 0.72 - idx * 0.015)),
            score=_safe_float(r.get("score") or r.get("similarity"), max(0.0, 0.72 - idx * 0.015)),
            link=url,
            paper_title=_clean_latex_noise(title),
            paper_authors=authors,
            source="matlas",
        )
        if tm.body or tm.name:
            results.append(tm)

    # 排序：先按 similarity 降序，再按 query 词命中加权
    q_lower = (query or "").lower()
    q_terms = [t for t in re.split(r"\W+", q_lower) if len(t) > 2]

    def _bonus(tm: TheoremMatch) -> float:
        if not q_terms:
            return 0.0
        haystack = (tm.name + " " + tm.slogan + " " + tm.body[:300]).lower()
        hits = sum(1 for t in q_terms if t in haystack)
        return 0.05 * hits  # 词命中加 5% 加权

    # 写回 score = similarity + bonus，并以 score 降序，让 results 顺序和 score 字段一致
    for tm in results:
        source_bonus = 0.02 if tm.source == "theorem_search" else 0.0
        tm.score = round(tm.similarity + _bonus(tm) + source_bonus, 6)
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]


def format_theorems_for_prompt(matches: list[TheoremMatch], *, max_chars: int = 3000) -> str:
    """将搜索结果格式化为注入 LLM prompt 的参考文本。"""
    if not matches:
        return "（未找到相关定理）"

    lines = ["【相关定理参考（TheoremSearch / Matlas 检索）】"]
    total = 0
    for i, m in enumerate(matches, 1):
        citation = m.to_citation()
        line = f"{i}. {citation}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)
