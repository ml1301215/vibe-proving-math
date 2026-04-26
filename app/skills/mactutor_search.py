"""技能：mactutor_search —— 搜索并抓取 MacTutor History of Mathematics 内容。

来源：mathshistory.st-andrews.ac.uk（CC BY-SA 4.0）
用于：learning pipeline 数学背景模块的史料补充

主要接口：
  get_mactutor_context(statement, max_chars=2500)
      → (content_text: str, source_url: str)
        content_text 为提炼后的原文摘录（供 LLM 作素材），
        source_url   为来源页面 URL（用于末尾归因）

内部流程：
  1. 从命题提取 2-4 个英文搜索词（避免中文查询 MacTutor 不支持）
  2. 搜索 MacTutor，优先选 HistTopics 页（理论主题文章），其次 Biographies
  3. 抓取 top-1 页面，解析正文段落，截取前 max_chars 字符
  4. 超时 / 网络错误时静默返回 ("", "")，pipeline 降级为纯 LLM
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("skills.mactutor")

BASE_URL    = "https://mathshistory.st-andrews.ac.uk"
SEARCH_URL  = BASE_URL + "/Search/"
ATTRIBUTION = "MacTutor History of Mathematics, University of St Andrews"

_HEADERS = {
    "User-Agent": "vibe_proving/1.0 (+https://github.com/vibe-proving; research use; CC BY-SA 4.0)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


# ── 关键词提取（轻量，无需 LLM） ─────────────────────────────────────────────

_MATH_STOPWORDS = {
    "prove", "proof", "show", "let", "given", "for", "all", "any", "every",
    "there", "exists", "such", "that", "then", "implies", "if", "and", "or",
    "not", "true", "false", "integer", "number", "real", "complex",
    "theorem", "lemma", "corollary", "proposition", "statement", "claim",
    "is", "are", "be", "has", "have", "the", "an", "a", "in", "on", "of",
    "with", "when", "where", "which", "this", "we", "can", "define",
}

# 常见中文数学术语→英文关键词（用于中文命题的 MacTutor 搜索）
_ZH_MATH_TERMS: list[tuple[str, list[str]]] = [
    ("素数", ["prime numbers"]),
    ("质数", ["prime numbers"]),
    ("无穷多", ["infinitely many"]),
    ("循环群", ["cyclic group"]),
    ("有限域", ["finite field"]),
    ("有限群", ["finite group"]),
    ("群论", ["group theory"]),
    ("环论", ["ring theory"]),
    ("域论", ["field theory"]),
    ("代数基本定理", ["fundamental theorem algebra"]),
    ("微积分基本定理", ["fundamental theorem calculus"]),
    ("费马大定理", ["Fermat last theorem"]),
    ("费马小定理", ["Fermat little theorem"]),
    ("欧拉", ["Euler"]),
    ("高斯", ["Gauss"]),
    ("黎曼", ["Riemann"]),
    ("费马", ["Fermat"]),
    ("欧几里得", ["Euclid"]),
    ("柯西", ["Cauchy"]),
    ("拉格朗日", ["Lagrange"]),
    ("泰勒", ["Taylor"]),
    ("傅里叶", ["Fourier"]),
    ("积分", ["integration calculus"]),
    ("微分", ["differentiation calculus"]),
    ("连续", ["continuity"]),
    ("收敛", ["convergence series"]),
    ("数论", ["number theory"]),
    ("拓扑", ["topology"]),
    ("线性代数", ["linear algebra"]),
    ("矩阵", ["matrix"]),
    ("行列式", ["determinant"]),
    ("特征值", ["eigenvalue"]),
    ("概率", ["probability"]),
    ("统计", ["statistics"]),
    ("复分析", ["complex analysis"]),
    ("实分析", ["real analysis"]),
    ("测度论", ["measure theory"]),
]


def _extract_search_terms(statement: str, n: int = 4) -> list[str]:
    """从命题中提取适合 MacTutor 搜索的英文词汇。"""
    words = re.findall(r"[A-Za-z][a-z]{2,}", statement)
    filtered = [w.lower() for w in words if w.lower() not in _MATH_STOPWORDS]
    seen: dict[str, int] = {}
    for w in filtered:
        seen[w] = seen.get(w, 0) + 1
    ranked = sorted(seen, key=lambda x: -seen[x])

    caps = [w for w in words if w[0].isupper() and w.lower() not in _MATH_STOPWORDS]
    caps_dedup = list(dict.fromkeys(c.lower() for c in caps))

    result = caps_dedup + [w for w in ranked if w not in caps_dedup]

    # 中文命题：从术语表提取英文关键词补充
    if not result or len(result) < 2:
        zh_terms: list[str] = []
        for zh, en_list in _ZH_MATH_TERMS:
            if zh in statement:
                zh_terms.extend(en_list)
        result = zh_terms + [r for r in result if r not in zh_terms]

    return result[:n] if result else ["mathematics history"]


# ── 搜索 MacTutor ─────────────────────────────────────────────────────────────

def _score_result(url: str, title: str) -> int:
    """给搜索结果打优先级分：HistTopics > Biographies > 其他。"""
    path = url.lower()
    if "/histtopics/" in path:
        return 2
    if "/biographies/" in path:
        return 1
    return 0


async def search_mactutor(query: str, top_k: int = 4) -> list[dict]:
    """搜索 MacTutor，返回 [{title, url, score}]，按相关性排序。"""
    params = {
        "query": query,
        "form": "resultsonly",
        "num_ranks": str(top_k * 2),
    }
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT) as client:
            resp = await client.get(SEARCH_URL, params=params)
        if resp.status_code != 200:
            logger.debug("MacTutor search returned %d", resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        # MacTutor 现在同时使用相对路径（/HistTopics/...）和绝对 URL
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(BASE_URL):
                full_url = href
            elif href.startswith("/"):
                full_url = BASE_URL + href
            else:
                continue
            if not any(seg in full_url for seg in ("/HistTopics/", "/Biographies/", "/Extras/")):
                continue
            title = a.get_text(" ", strip=True)
            if len(title) < 3:
                continue
            score = _score_result(full_url, title)
            results.append({"title": title, "url": full_url, "score": score})
        # 去重并按 score 降序
        seen_urls: set[str] = set()
        deduped = []
        for r in sorted(results, key=lambda x: -x["score"]):
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                deduped.append(r)
        return deduped[:top_k]
    except Exception as e:
        logger.debug("MacTutor search error: %s", e)
        return []


# ── 抓取并解析页面 ────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """清理多余空白和行尾空格。"""
    text = re.sub(r"\s*\n\s*\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_main_text(soup: BeautifulSoup, max_chars: int) -> str:
    """从 MacTutor 页面提取主正文段落。"""
    # 移除导航、页脚、脚注、图注
    for tag in soup.find_all(["nav", "footer", "script", "style",
                               "figcaption", "figure", "aside"]):
        tag.decompose()
    # 移除 class 含 "nav" / "menu" / "breadcrumb" / "sidebar" 的 div（两步走防止树变更破坏迭代）
    to_remove = []
    for div in soup.find_all("div", class_=True):
        try:
            classes = " ".join(div.get("class") or [])
            if any(k in classes.lower() for k in ("nav", "menu", "breadcrumb", "sidebar", "footer", "header")):
                to_remove.append(div)
        except Exception:
            pass
    for div in to_remove:
        try:
            div.decompose()
        except Exception:
            pass

    # 尝试锁定主内容区
    main = (soup.find("main") or
            soup.find("div", id=re.compile(r"main|content|article", re.I)) or
            soup.find("article") or
            soup.body)
    if not main:
        return ""

    paragraphs: list[str] = []
    total = 0

    # MacTutor HistTopics pages store content in <span class="markup">, not <p>
    markup_spans = [s for s in main.find_all("span", class_="markup")
                    if len(s.get_text(" ", strip=True)) > 200]
    if markup_spans:
        # Take the largest span (main article body)
        biggest = max(markup_spans, key=lambda s: len(s.get_text()))
        raw = biggest.get_text(" ", strip=True)
        return _clean_text(raw[:max_chars])

    for tag in main.find_all(["p", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if len(text) < 30:
            continue
        if re.match(r"^\[?\d+\]", text):
            continue
        paragraphs.append(text)
        total += len(text) + 2
        if total >= max_chars:
            break

    return _clean_text("\n\n".join(paragraphs))


async def fetch_mactutor_page(url: str, max_chars: int = 2500) -> dict:
    """抓取 MacTutor 页面，返回 {title, content, url}。"""
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT) as client:
            resp = await client.get(url, follow_redirects=True)
        if resp.status_code != 200:
            return {}
        html = resp.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = title.get_text(" ", strip=True) if title else ""
        content = _extract_main_text(soup, max_chars)
        if len(content) < 100:
            return {}
        return {"title": title_text, "content": content, "url": str(resp.url)}
    except Exception as e:
        logger.debug("MacTutor fetch error (%s): %s", url, e)
        return {}


# ── 高层接口（供 pipeline 调用） ──────────────────────────────────────────────

async def get_mactutor_context(
    statement: str,
    max_chars: int = 2500,
    timeout_s: float = 12.0,
) -> tuple[str, str]:
    """
    给定数学命题，返回 (mactutor_text, source_url)。

    mactutor_text: 原文摘录，可直接作为 LLM history 任务的上下文素材。
    source_url:    来源页面 URL，用于在输出末尾加归因链接。
    若网络失败或未找到相关内容，两者均为空字符串。
    """
    import asyncio

    terms = _extract_search_terms(statement, n=4)
    query = " ".join(terms[:3])
    if not query.strip():
        return "", ""

    try:
        async with asyncio.timeout(timeout_s):
            results = await search_mactutor(query, top_k=4)
            if not results:
                # 退化：用单词再搜一次
                query2 = " ".join(terms[:2])
                results = await search_mactutor(query2, top_k=4) if query2 != query else []
            if not results:
                return "", ""

            # 优先抓 HistTopics 页
            best = results[0]
            page = await fetch_mactutor_page(best["url"], max_chars=max_chars)
            if not page or len(page.get("content", "")) < 150:
                # 尝试第二个候选
                if len(results) > 1:
                    page = await fetch_mactutor_page(results[1]["url"], max_chars=max_chars)
            if not page or len(page.get("content", "")) < 150:
                return "", ""

            title = page.get("title", "")
            content = page.get("content", "")
            source_url = page.get("url", best["url"])

            header = f"[MacTutor source: {title}]\n" if title else "[MacTutor source]\n"
            return header + content, source_url

    except TimeoutError:
        logger.debug("MacTutor context timed out for: %s", statement[:60])
        return "", ""
    except Exception as e:
        logger.debug("get_mactutor_context error: %s", e)
        return "", ""
