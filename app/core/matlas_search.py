"""Matlas semantic search client."""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://matlas.ai"
_SEARCH_PATH = "/api/search"
_TIMEOUT = 12.0
_CACHE_TTL = 300
_CACHE_MAX_SIZE = 256

_http_client: Optional[httpx.AsyncClient] = None
_cache: dict[str, tuple[float, list[dict]]] = {}


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(_TIMEOUT, connect=8.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=30),
        )
    return _http_client


def _cache_get(key: str) -> Optional[list[dict]]:
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, results = entry
    if time.monotonic() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return results


def _cache_set(key: str, results: list[dict]) -> None:
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[: max(1, _CACHE_MAX_SIZE // 10)]
        for key_to_drop, _ in oldest:
            _cache.pop(key_to_drop, None)
    _cache[key] = (time.monotonic(), results)


async def search_matlas(query: str, top_k: int = 10) -> list[dict]:
    """Search Matlas and return raw result dictionaries."""
    query = (query or "").strip()
    if not query:
        return []
    num_results = max(10, int(top_k or 10))
    cache_key = f"{query}:{num_results}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_http_client()
    try:
        logger.info("Matlas API call: query=%r, num_results=%d", query[:50], num_results)
        resp = await client.post(_SEARCH_PATH, json={"query": query, "num_results": num_results})
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Matlas API failed: %s", exc)
        return []

    results = data if isinstance(data, list) else data.get("results", [])
    if not isinstance(results, list):
        results = []
    _cache_set(cache_key, results)
    logger.info("Matlas returned %d results for query=%r", len(results), query[:50])
    return results


def get_cache_stats() -> dict:
    now = time.monotonic()
    valid = sum(1 for ts, _ in _cache.values() if now - ts <= _CACHE_TTL)
    return {"total": len(_cache), "valid": valid, "ttl_seconds": _CACHE_TTL}
