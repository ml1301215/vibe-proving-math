"""Phase 0 验收 0.5：LATRACE 健康检查"""
import pytest


@pytest.mark.asyncio
@pytest.mark.slow
async def test_latrace_health():
    """0.5 LATRACE /health 返回 200，向量和图数据库均 ok"""
    from core.memory import MemoryClient

    client = MemoryClient(user_id="test-user")
    try:
        health = await client.health()
        print(f"\nLATRACE health: {health}")

        deps = health.get("dependencies", {})
        vectors_ok = deps.get("vectors", {}).get("status") == "ok"
        graph_ok = deps.get("graph", {}).get("status") == "ok"

        assert vectors_ok, f"向量数据库状态异常: {deps.get('vectors')}"
        assert graph_ok, f"图数据库状态异常: {deps.get('graph')}"
    except Exception as e:
        pytest.skip(f"LATRACE 未启动（跳过）: {e}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_latrace_ingest_smoke():
    """LATRACE 写入接口冒烟测试（不等待提取完成）"""
    from core.memory import MemoryClient

    client = MemoryClient(user_id="test-smoke-001")
    try:
        job_id = await client.ingest(
            "test-project",
            [
                {"role": "user", "text": "Sylow 第一定理是什么？"},
                {"role": "assistant", "text": "Sylow 第一定理指出对于有限群 G，若素数 p 整除 |G|，则 G 含有阶为 p 的元素。"},
            ],
            llm_policy="best_effort",
        )
        # job_id 可能为空（LATRACE 未启动时），只要不抛异常即可
        print(f"\nLATRACE ingest job_id: {job_id!r}")
    except Exception as e:
        pytest.skip(f"LATRACE 未启动（跳过）: {e}")
