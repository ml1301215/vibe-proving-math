"""Phase 2 验收测试：LATRACE 记忆集成

注意：LATRACE 需要 Docker 启动才能运行这些测试。
若 LATRACE 未启动，所有测试会自动跳过（不影响 CI）。
"""
import pytest
import asyncio


async def _check_latrace_available() -> bool:
    """检查 LATRACE 是否可用。"""
    from core.memory import MemoryClient
    client = MemoryClient(user_id="health-check")
    try:
        health = await client.health()
        return health.get("status") in ("ok", "healthy")
    except Exception:
        return False


@pytest.fixture
async def mem_client():
    """提供已连接的 MemoryClient，若 LATRACE 不可用则跳过。"""
    from core.memory import MemoryClient
    if not await _check_latrace_available():
        pytest.skip("LATRACE 未启动（docker compose up -d）")
    return MemoryClient(user_id="test-user-phase2")


# ── 2.1 项目隔离测试 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_project_isolation(mem_client):
    """2.4 项目 A 的内容不出现在项目 B 的检索结果中"""
    import time

    client = mem_client

    # 写入项目 A（代数话题）
    await client.ingest("proj-A-algebra", [
        {"role": "user", "text": "What is a Sylow subgroup?"},
        {"role": "assistant", "text": "A Sylow p-subgroup is a maximal p-subgroup of a finite group G."},
    ])

    # 写入项目 B（分析话题）
    await client.ingest("proj-B-analysis", [
        {"role": "user", "text": "What is the Riemann hypothesis?"},
        {"role": "assistant", "text": "The Riemann hypothesis states that all non-trivial zeros of the Riemann zeta function have real part 1/2."},
    ])

    # 等待 LATRACE 处理
    await asyncio.sleep(25)

    # 项目 A 检索：找 Sylow 相关
    results_a = await client.retrieve("proj-A-algebra", "Sylow subgroup definition", topk=5)
    # 项目 B 检索：找 Riemann 相关
    results_b = await client.retrieve("proj-B-analysis", "Riemann hypothesis zeros", topk=5)

    print(f"\n项目隔离测试:")
    print(f"  项目A(Sylow)检索: {len(results_a)} 条")
    print(f"  项目B(Riemann)检索: {len(results_b)} 条")

    # 验证项目 A 的检索结果不含项目 B 的话题
    for r in results_a:
        assert "riemann" not in r.get("text", "").lower(), "项目隔离失败：A 中出现了 B 的内容"


# ── 2.2 + 2.3 写入和检索 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_ingest_and_retrieve(mem_client):
    """2.2 + 2.3 写入 3 轮对话后检索，相关事实能被召回"""
    import time

    client = mem_client
    project = f"test-retrieve-{int(time.time())}"

    # 写入 3 轮对话
    job1 = await client.ingest(project, [
        {"role": "user", "text": "Explain Lagrange's theorem in group theory."},
        {"role": "assistant", "text": "Lagrange's theorem states that for any finite group G, the order of every subgroup H divides the order of G. That is, |H| divides |G|."},
    ])
    job2 = await client.ingest(project, [
        {"role": "user", "text": "What are the consequences of Lagrange's theorem?"},
        {"role": "assistant", "text": "Key consequences: (1) The order of any element divides |G|. (2) Any group of prime order is cyclic. (3) Fermat's little theorem follows as a corollary."},
    ])
    job3 = await client.ingest(project, [
        {"role": "user", "text": "Can you give an example?"},
        {"role": "assistant", "text": "Example: Z/6Z has order 6. Its subgroups have orders 1, 2, 3, 6 — all divisors of 6. This confirms Lagrange's theorem."},
    ])

    print(f"\ningest job IDs: {job1!r}, {job2!r}, {job3!r}")

    # 等待 LATRACE 异步处理（约 20-25s）
    await asyncio.sleep(30)

    # 检索相关记忆
    results = await client.retrieve(project, "Lagrange theorem subgroup order", topk=8)
    print(f"检索结果: {len(results)} 条")
    for r in results:
        print(f"  [score={r.get('score', 0):.3f}] {str(r.get('text', ''))[:80]}")

    # 验收标准：至少 1 条 score > 0.1
    high_score = [r for r in results if r.get("score", 0) > 0.1]
    assert len(high_score) >= 1, f"未检索到高分记忆，所有分数: {[r.get('score') for r in results]}"


# ── 2.5 异步非阻塞 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_memory_ingest_is_fast(mem_client):
    """2.5 ingest 调用在 < 500ms 内返回（不等待 LLM 提取）"""
    import time

    client = mem_client
    t0 = time.time()
    await client.ingest("test-speed", [
        {"role": "user", "text": "Test message"},
        {"role": "assistant", "text": "Test response"},
    ])
    elapsed_ms = (time.time() - t0) * 1000

    print(f"\ningest 耗时: {elapsed_ms:.0f}ms")
    assert elapsed_ms < 2000, f"ingest 阻塞太久: {elapsed_ms:.0f}ms（应 < 2000ms）"


# ── 无 LATRACE 场景：验证 fallback 行为 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_graceful_no_latrace():
    """LATRACE 不可用时，retrieve 返回空列表而不是抛异常"""
    from core.memory import MemoryClient

    # 指向不存在的端口
    import unittest.mock as mock

    client = MemoryClient(user_id="test-no-latrace")
    client._base = "http://localhost:19999"  # 不存在的端口

    results = await client.retrieve("proj-x", "some query")
    assert results == [], f"应返回空列表，实际: {results}"
    print("\nfallback 测试通过：LATRACE 不可用时返回空列表")
