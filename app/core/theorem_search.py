"""TheoremSearch API 客户端。

优化记录：
  - 单一模块级 httpx.AsyncClient（连接池，keepalive），避免每次请求新建 TCP
  - search_theorems 结果 TTL 缓存（默认 5 分钟），GVR 循环中同一 query 只调用一次
  - 缓存上限 512 条（LRU 淘汰最老条目）

API 文档：https://www.theoremsearch.com/docs
基础端点：https://api.theoremsearch.com

用法：
    from core.theorem_search import search_theorems, search_papers

    results = await search_theorems("Sylow theorem")
    for r in results:
        print(r["similarity"], r["statement"])
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from .config import ts_cfg

logger = logging.getLogger(__name__)

# ── 模块级长连接池（进程生命周期内复用）─────────────────────────────────────────
# httpx.AsyncClient 创建时不绑定 event loop，可在首次异步调用时安全使用。
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        cfg = ts_cfg()
        _http_client = httpx.AsyncClient(
            timeout=cfg.get("timeout", 15),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
        logger.debug("TheoremSearch HTTP client created: base=%s", cfg.get("base_url", "?"))
    return _http_client


# ── 搜索结果 TTL 缓存 ──────────────────────────────────────────────────────────
_CACHE_TTL = 300          # 5 分钟
_CACHE_MAX_SIZE = 512
_search_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_get(key: str) -> Optional[list[dict]]:
    entry = _search_cache.get(key)
    if entry is None:
        return None
    ts, results = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _search_cache[key]
        return None
    return results


def _cache_set(key: str, results: list[dict]) -> None:
    if len(_search_cache) >= _CACHE_MAX_SIZE:
        # 淘汰最老的 10% 条目（简单 LRU 近似）
        evict_count = _CACHE_MAX_SIZE // 10
        oldest = sorted(_search_cache.items(), key=lambda kv: kv[1][0])[:evict_count]
        for k, _ in oldest:
            _search_cache.pop(k, None)
    _search_cache[key] = (time.monotonic(), results)


class TheoremSearchClient:
    def __init__(self) -> None:
        cfg = ts_cfg()
        self._base = cfg["base_url"].rstrip("/")

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[dict]:
        """搜索定理，返回按相似度排序的结果列表（带缓存）。

        API: POST /search  {"query": str, "n_results": int}
        每条结果（TheoremResult）包含：
            body         (str)   定理陈述正文
            slogan       (str)   定理一句话描述
            name         (str)   定理名称
            similarity   (float) 相似度 0-1
            score        (float) 综合评分
            link         (str)   来源链接
            paper        (dict)  论文信息
        """
        cache_key = f"search:{query}:{top_k}:{min_similarity}"
        cached = _cache_get(cache_key)
        if cached is not None:
            logger.debug("TheoremSearch cache hit: q=%r", query[:40])
            return cached

        url = f"{self._base}/search"
        client = _get_http_client()
        try:
            logger.info("TheoremSearch API call: query=%r, top_k=%d, base_url=%s", query[:50], top_k, self._base)
            resp = await client.post(url, json={"query": query, "n_results": top_k})
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("TheoremSearch API failed: %s (base_url=%s)", str(e), self._base)
            raise

        results = data.get("theorems", data) if isinstance(data, dict) else data
        if min_similarity > 0:
            results = [r for r in results if r.get("similarity", 0) >= min_similarity]

        logger.info("TheoremSearch returned %d results for query=%r", len(results), query[:50])
        _cache_set(cache_key, results)
        return results

    async def paper_search(self, query: str, top_k: int = 5) -> list[dict]:
        """搜索论文（GET /paper-search?q=...&limit=...）。"""
        cache_key = f"paper:{query}:{top_k}"
        cached = _cache_get(cache_key)
        if cached is not None:
            logger.debug("TheoremSearch paper_search cache hit: q=%r", query[:40])
            return cached

        url = f"{self._base}/paper-search"
        try:
            client = _get_http_client()
            resp = await client.get(url, params={"q": query, "limit": top_k})
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("TheoremSearch.paper_search failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("results", [])
        _cache_set(cache_key, results)
        return results


# ── 模块级单例 ─────────────────────────────────────────────────────────────────
_client: Optional[TheoremSearchClient] = None


def get_client() -> TheoremSearchClient:
    global _client
    if _client is None:
        _client = TheoremSearchClient()
    return _client


async def search_theorems(
    query: str,
    top_k: int = 10,
    min_similarity: float = 0.0,
) -> list[dict]:
    """便捷函数：搜索定理（带 TTL 缓存）。"""
    return await get_client().search(query, top_k=top_k, min_similarity=min_similarity)


async def search_papers(query: str, top_k: int = 5) -> list[dict]:
    """便捷函数：搜索论文（带 TTL 缓存）。"""
    return await get_client().paper_search(query, top_k=top_k)


def get_cache_stats() -> dict:
    """返回缓存统计信息（供 /health 端点调用）。"""
    now = time.monotonic()
    valid = sum(1 for ts, _ in _search_cache.values() if now - ts <= _CACHE_TTL)
    return {"total": len(_search_cache), "valid": valid, "ttl_seconds": _CACHE_TTL}
