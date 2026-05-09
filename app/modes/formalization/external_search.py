from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

import httpx
from core.config import formalization_cfg

logger = logging.getLogger("modes.formalization")

_FORM_CFG = formalization_cfg()
_LEANSEARCH_URL = str(_FORM_CFG.get("leansearch_url") or "https://leansearch.net/search").strip()
_LOOGLE_URL = str(_FORM_CFG.get("loogle_url") or "https://loogle.lean-lang.org/json").strip()
_EXTERNAL_SEARCH_TIMEOUT_SECONDS = float(_FORM_CFG.get("external_search_timeout_seconds") or 4.0)
_LEANSEARCH_MODE: Optional[str] = None
_LEANSEARCH_DISABLED = False
_LEANSEARCH_DISABLE_REASON = ""
_LOOGLE_DISABLED = False
_LOOGLE_DISABLE_REASON = ""
_EXTERNAL_RESULT_CACHE: dict[tuple[str, str, int], list[dict]] = {}


def _normalize_query_token(token: str) -> str:
    token = str(token or "").strip()
    if not token:
        return ""
    token = re.sub(r"\s+", " ", token)
    return token


def build_external_queries(statement: str, keywords: list[str], *, max_queries: int = 3) -> list[str]:
    normalized = [_normalize_query_token(keyword) for keyword in keywords if _normalize_query_token(keyword)]
    theoremish = [token for token in normalized if "_" in token or "." in token]
    atomic = [token for token in normalized if token not in theoremish]
    queries: list[str] = []
    seen: set[str] = set()

    def push(query: str) -> None:
        compact = _normalize_query_token(query)
        lowered = compact.lower()
        if not compact or lowered in seen:
            return
        seen.add(lowered)
        queries.append(compact)

    if theoremish:
        push(theoremish[0])
    if theoremish and atomic:
        push(" ".join([theoremish[0], *atomic[:2]]))
    if atomic:
        push(" ".join(atomic[:4]))
    if not queries and statement.strip():
        push(statement.strip())
    elif statement.strip() and len(statement.strip()) <= 80 and len(queries) < min(2, max_queries):
        push(statement.strip())
    return queries[:max_queries]


def _normalize_candidate(
    *,
    source: str,
    name: str,
    snippet: str,
    url: str = "",
    path: str = "",
    score: float = 0.0,
    lean_name: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    path = path or name
    return {
        "name": name,
        "path": path,
        "html_url": url,
        "snippet": snippet[:800],
        "source": source,
        "score": float(score or 0.0),
        "lean_name": lean_name or name,
        "metadata": dict(metadata or {}),
    }


def _coerce_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _copy_candidates(candidates: list[dict]) -> list[dict]:
    return [{**candidate, "metadata": dict(candidate.get("metadata", {}) or {})} for candidate in candidates]


def _extract_leansearch_candidates(payload: dict, *, query: str) -> list[dict]:
    items = payload.get("results") or payload.get("items") or payload.get("hits") or []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("declName") or item.get("declarationName") or "").strip()
        snippet = str(
            item.get("snippet")
            or item.get("type")
            or item.get("doc")
            or item.get("text")
            or item.get("content")
            or ""
        ).strip()
        if not name and not snippet:
            continue
        url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
        module = str(item.get("module") or item.get("path") or "").strip()
        out.append(
            _normalize_candidate(
                source="leansearch",
                name=name or module or query,
                path=module or name or query,
                snippet=snippet or name or query,
                url=url,
                score=_coerce_float(item.get("score") or item.get("_score")),
                lean_name=name,
                metadata={"query": query},
            )
        )
    return out


def _extract_loogle_candidates(payload, *, query: str) -> list[dict]:
    items = payload if isinstance(payload, list) else payload.get("results") or payload.get("items") or []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("declName") or item.get("declarationName") or "").strip()
        module = str(item.get("module") or item.get("path") or "").strip()
        signature = str(
            item.get("type")
            or item.get("signature")
            or item.get("snippet")
            or item.get("doc")
            or item.get("text")
            or ""
        ).strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        if not name and not signature:
            continue
        out.append(
            _normalize_candidate(
                source="loogle",
                name=name or module or query,
                path=module or name or query,
                snippet=signature or name or query,
                url=url,
                score=_coerce_float(item.get("score")),
                lean_name=name,
                metadata={"query": query},
            )
        )
    return out


async def search_leansearch(statement: str, keywords: list[str], *, top_k: int = 4) -> list[dict]:
    global _LEANSEARCH_MODE, _LEANSEARCH_DISABLED, _LEANSEARCH_DISABLE_REASON
    queries = build_external_queries(statement, keywords)
    if not queries:
        return []
    if _LEANSEARCH_DISABLED:
        logger.info("LeanSearch disabled for current session: %s", _LEANSEARCH_DISABLE_REASON or "unsupported")
        return []
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    async with httpx.AsyncClient(timeout=_EXTERNAL_SEARCH_TIMEOUT_SECONDS) as client:
        for query in queries:
            cache_key = ("leansearch", query.lower(), int(top_k))
            if cache_key in _EXTERNAL_RESULT_CACHE:
                for candidate in _copy_candidates(_EXTERNAL_RESULT_CACHE[cache_key]):
                    key = (candidate["path"], candidate["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(candidate)
                    if len(results) >= top_k:
                        return results
                continue
            try:
                payload = None
                ordered_attempts = {
                    "post_json": {"json": {"query": query, "size": top_k}},
                    "post_form": {"data": {"query": query, "size": top_k}},
                    "get": {"params": {"q": query, "query": query, "size": top_k}},
                }
                attempt_names = [_LEANSEARCH_MODE] if _LEANSEARCH_MODE in ordered_attempts else []
                attempt_names.extend(name for name in ordered_attempts if name not in attempt_names)
                all_unprocessable = True
                for kind in attempt_names:
                    kwargs = ordered_attempts[kind]
                    if kind == "get":
                        resp = await client.get(_LEANSEARCH_URL, **kwargs)
                    else:
                        resp = await client.post(_LEANSEARCH_URL, **kwargs)
                    if resp.status_code == 422:
                        continue
                    all_unprocessable = False
                    if resp.status_code >= 400:
                        if resp.status_code in {401, 403, 404, 405}:
                            _LEANSEARCH_DISABLED = True
                            _LEANSEARCH_DISABLE_REASON = f"http_{resp.status_code}"
                        logger.warning("LeanSearch returned %d for query %s", resp.status_code, query)
                        break
                    payload = resp.json()
                    _LEANSEARCH_MODE = kind
                    break
                if payload is None:
                    if all_unprocessable:
                        _LEANSEARCH_DISABLED = True
                        _LEANSEARCH_DISABLE_REASON = "all request formats returned 422"
                        logger.warning("LeanSearch disabled after unsupported request formats for %s", query)
                    else:
                        logger.warning("LeanSearch could not parse query format for %s", query)
                    if _LEANSEARCH_DISABLED:
                        break
                    continue
                if _LEANSEARCH_DISABLED:
                    break
            except Exception as exc:  # noqa: BLE001
                logger.warning("LeanSearch query failed (%s): %s", query, exc)
                continue
            extracted = _extract_leansearch_candidates(payload, query=query)
            _EXTERNAL_RESULT_CACHE[cache_key] = _copy_candidates(extracted)
            for candidate in extracted:
                key = (candidate["path"], candidate["name"])
                if key in seen:
                    continue
                seen.add(key)
                results.append(candidate)
                if len(results) >= top_k:
                    return results
    return results


async def search_loogle(statement: str, keywords: list[str], *, top_k: int = 4) -> list[dict]:
    global _LOOGLE_DISABLED, _LOOGLE_DISABLE_REASON
    queries = build_external_queries(statement, keywords)
    if not queries:
        return []
    if _LOOGLE_DISABLED:
        logger.info("Loogle disabled for current session: %s", _LOOGLE_DISABLE_REASON or "unreachable")
        return []
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    async with httpx.AsyncClient(timeout=_EXTERNAL_SEARCH_TIMEOUT_SECONDS) as client:
        for query in queries:
            cache_key = ("loogle", query.lower(), int(top_k))
            if cache_key in _EXTERNAL_RESULT_CACHE:
                for candidate in _copy_candidates(_EXTERNAL_RESULT_CACHE[cache_key]):
                    key = (candidate["path"], candidate["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(candidate)
                    if len(results) >= top_k:
                        return results
                continue
            try:
                resp = await client.get(_LOOGLE_URL, params={"q": query})
                if resp.status_code >= 400:
                    if resp.status_code in {401, 403, 404, 405}:
                        _LOOGLE_DISABLED = True
                        _LOOGLE_DISABLE_REASON = f"http_{resp.status_code}"
                    logger.warning("Loogle returned %d for query %s", resp.status_code, query)
                    continue
                payload = resp.json()
            except Exception as exc:  # noqa: BLE001
                if "getaddrinfo failed" in str(exc).lower():
                    _LOOGLE_DISABLED = True
                    _LOOGLE_DISABLE_REASON = "dns_lookup_failed"
                logger.warning("Loogle query failed (%s): %s", query, exc)
                continue
            extracted = _extract_loogle_candidates(payload, query=query)
            _EXTERNAL_RESULT_CACHE[cache_key] = _copy_candidates(extracted)
            for candidate in extracted:
                key = (candidate["path"], candidate["name"])
                if key in seen:
                    continue
                seen.add(key)
                results.append(candidate)
                if len(results) >= top_k:
                    return results
    return results


async def search_external_mathlib(statement: str, keywords: list[str], *, top_k: int = 4) -> list[dict]:
    leansearch_results, loogle_results = await asyncio.gather(
        search_leansearch(statement, keywords, top_k=top_k),
        search_loogle(statement, keywords, top_k=top_k),
        return_exceptions=True,
    )

    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for batch in (leansearch_results, loogle_results):
        if isinstance(batch, Exception):
            logger.warning("external search batch failed: %s", batch)
            continue
        for candidate in batch:
            key = (candidate.get("path", ""), candidate.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(candidate)
            if len(merged) >= top_k * 2:
                return merged
    return merged
