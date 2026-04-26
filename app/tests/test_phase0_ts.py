"""Phase 0 验收 0.4：TheoremSearch API 调用"""
import pytest


@pytest.mark.asyncio
@pytest.mark.slow
async def test_theorem_search_basic():
    """0.4 查询 'Sylow theorem' 返回 >= 3 条结果，每条含 similarity 字段"""
    from core.theorem_search import search_theorems

    results = await search_theorems("Sylow theorem", top_k=10)

    assert len(results) >= 3, f"结果太少：{len(results)} 条"
    for r in results:
        assert "similarity" in r, f"结果缺少 similarity 字段：{r.keys()}"
    print(f"\nTheoremSearch 返回 {len(results)} 条，top similarity: {results[0].get('similarity'):.3f}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_theorem_search_fermat():
    """查询费马小定理，相似度应 > 0.3"""
    import httpx
    from core.theorem_search import search_theorems

    try:
        results = await search_theorems("Fermat little theorem", top_k=5)
        assert len(results) > 0, "费马小定理查询无结果"
        top = results[0]
        assert top.get("similarity", 0) >= 0.3, f"相似度过低: {top.get('similarity')}"
        print(f"\n费马小定理 top 结果: similarity={top.get('similarity'):.3f}")
        body = top.get("body") or top.get("slogan", "")
        print(f"  body: {str(body)[:120]}")
    except httpx.ReadTimeout:
        pytest.skip("TheoremSearch 响应超时（服务繁忙），跳过此次测试")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_theorem_search_min_similarity_filter():
    """min_similarity 过滤器有效"""
    import httpx
    from core.theorem_search import search_theorems

    try:
        results = await search_theorems("Lagrange theorem group", top_k=10, min_similarity=0.3)
        for r in results:
            assert r.get("similarity", 0) >= 0.3
    except httpx.ReadTimeout:
        pytest.skip("TheoremSearch 响应超时（服务繁忙），跳过此次测试")
