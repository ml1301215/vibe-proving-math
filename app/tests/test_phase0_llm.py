"""Phase 0 验收 0.3：LLM 调用成功"""
import pytest
import time


@pytest.mark.asyncio
@pytest.mark.slow
async def test_llm_basic_call():
    """0.3 通过 [llm].base_url 发一次调用，返回非空字符串，延迟 < 30s"""
    from core.llm import chat

    t0 = time.time()
    reply = await chat("Say 'Hello from vibe_proving' in exactly those words.")
    elapsed = time.time() - t0

    assert reply, "LLM 返回空字符串"
    assert len(reply) > 0, "LLM 返回内容长度为 0"
    assert elapsed < 30, f"LLM 响应超时：{elapsed:.1f}s"
    print(f"\nLLM 回复 ({elapsed:.1f}s): {reply[:100]}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_llm_with_system_prompt():
    """LLM 支持 system prompt"""
    from core.llm import chat

    reply = await chat(
        "What is 2+2?",
        system="You are a math assistant. Answer with just the number.",
    )
    assert reply.strip(), "system prompt 模式返回空"
    print(f"\nSystem prompt 测试: {reply}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_llm_stream():
    """LLM 流式输出可用，能 yield 至少 1 个 token"""
    from core.llm import stream_chat

    tokens = []
    async for chunk in stream_chat("Count from 1 to 3 with commas."):
        tokens.append(chunk)
        if len(tokens) >= 3:
            break

    assert len(tokens) >= 1, "流式输出未能产出任何 token"
    print(f"\n流式测试：收到 {len(tokens)} 个 chunk，前几个: {''.join(tokens[:5])}")
