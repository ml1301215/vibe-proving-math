import asyncio

import pytest

from modes.formalization.external_search import (
    build_external_queries,
    search_external_mathlib,
    search_leansearch,
    search_loogle,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _reset_external_search_session_state():
    """避免同一会话中其它测试触发真实 LeanSearch 后全局禁用，导致本模块测试拿到空结果。"""
    import modes.formalization.external_search as es

    es._LEANSEARCH_DISABLED = False
    es._LEANSEARCH_DISABLE_REASON = ""
    es._LEANSEARCH_MODE = None
    es._LOOGLE_DISABLED = False
    es._LOOGLE_DISABLE_REASON = ""
    es._EXTERNAL_RESULT_CACHE.clear()
    yield
    es._EXTERNAL_RESULT_CACHE.clear()


class _FakeAsyncClient:
    def __init__(self, *, posts=None, gets=None):
        self._posts = list(posts or [])
        self._gets = list(gets or [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json=None, data=None):
        if self._posts:
            return self._posts.pop(0)
        return _FakeResponse(200, {"results": []})

    async def get(self, url, params=None):
        if self._gets:
            return self._gets.pop(0)
        return _FakeResponse(200, [])


def test_build_external_queries_prefers_theoremish_keyword():
    queries = build_external_queries(
        "对任意自然数 a, b，有 a + b = b + a",
        ["nat.add_comm", "comm", "nat"],
    )

    assert queries[0] == "nat.add_comm"
    assert any("comm" in query for query in queries)


def test_search_leansearch_normalizes_results(monkeypatch):
    monkeypatch.setattr(
        "modes.formalization.external_search.httpx.AsyncClient",
        lambda timeout=8.0: _FakeAsyncClient(
            posts=[
                _FakeResponse(
                    200,
                    {
                        "results": [
                            {
                                "name": "two_mul_le_add_sq",
                                "module": "Mathlib.Algebra.Order.Field.Basic",
                                "type": "2 * a * b ≤ a ^ 2 + b ^ 2",
                                "url": "https://leansearch.example/two_mul_le_add_sq",
                                "score": 0.91,
                            }
                        ]
                    },
                )
            ]
        ),
    )

    results = asyncio.run(search_leansearch("a^2+b^2≥2ab", ["two_mul_le_add_sq"], top_k=2))

    assert results[0]["source"] == "leansearch"
    assert results[0]["lean_name"] == "two_mul_le_add_sq"
    assert "2 * a * b" in results[0]["snippet"]


def test_search_loogle_normalizes_results(monkeypatch):
    monkeypatch.setattr(
        "modes.formalization.external_search.httpx.AsyncClient",
        lambda timeout=8.0: _FakeAsyncClient(
            gets=[
                _FakeResponse(
                    200,
                    [
                        {
                            "name": "Nat.add_comm",
                            "module": "Mathlib.Data.Nat.Basic",
                            "type": "(a b : Nat) -> a + b = b + a",
                            "url": "https://loogle.example/Nat.add_comm",
                            "score": 0.88,
                        }
                    ],
                )
            ]
        ),
    )

    results = asyncio.run(search_loogle("a+b=b+a", ["Nat.add_comm"], top_k=2))

    assert results[0]["source"] == "loogle"
    assert results[0]["lean_name"] == "Nat.add_comm"
    assert "a + b = b + a" in results[0]["snippet"]


def test_search_external_mathlib_merges_sources(monkeypatch):
    async def fake_leansearch(statement: str, keywords: list[str], *, top_k: int = 4):
        return [{"name": "Nat.add_comm", "path": "Mathlib/Data/Nat/Basic.lean", "snippet": "Nat.add_comm", "source": "leansearch"}]

    async def fake_loogle(statement: str, keywords: list[str], *, top_k: int = 4):
        return [{"name": "dvd_trans", "path": "Mathlib/Init/Algebra/Classes.lean", "snippet": "dvd_trans", "source": "loogle"}]

    monkeypatch.setattr("modes.formalization.external_search.search_leansearch", fake_leansearch)
    monkeypatch.setattr("modes.formalization.external_search.search_loogle", fake_loogle)

    results = asyncio.run(search_external_mathlib("demo", ["nat.add_comm"], top_k=2))

    assert {item["source"] for item in results} == {"leansearch", "loogle"}
