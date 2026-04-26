"""Phase 3 验收测试：学习模式（新四节结构）

新四节：数学背景 | 前置知识 | 完整证明 | 具体例子
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_output_structure():
    """3.1 + 3.5 输出包含 4 个必需二级标题（新结构）"""
    from modes.learning.pipeline import run_learning_pipeline

    result = await run_learning_pipeline(
        "证明有限域的乘法群是循环群",
        level="undergraduate",
        include_prereqs=True,
    )

    md = result.to_markdown()
    print(f"\n学习模式输出 ({len(md)} 字符):")
    print(md[:500] + "...")

    assert "## 数学背景" in md,   "缺少 ## 数学背景"
    assert "## 前置知识" in md,   "缺少 ## 前置知识"
    assert "## 完整证明" in md,   "缺少 ## 完整证明"
    assert "## 具体例子" in md,   "缺少 ## 具体例子"
    assert "## 延伸阅读" not in md, "不应存在已废弃的 ## 延伸阅读"
    assert "## 例子" not in md,   "不应存在已废弃的 ## 例子"
    assert result.has_required_sections(), "has_required_sections() 返回 False"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_prereq_exists():
    """3.2 前置知识段落存在且非空"""
    from modes.learning.pipeline import run_learning_pipeline

    result = await run_learning_pipeline(
        "证明有限域的乘法群是循环群",
        level="undergraduate",
        include_prereqs=True,
    )

    md = result.to_markdown()
    assert "## 前置知识" in md, "缺少 ## 前置知识"
    section = md.split("## 前置知识")[1]
    assert len(section.strip()) > 20, "前置知识内容为空"
    print(f"\n前置知识节片段: {section[:200]}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_proof_exists():
    """3.6 完整证明节存在且包含分步结构"""
    from modes.learning.pipeline import run_learning_pipeline

    result = await run_learning_pipeline(
        "证明素数有无穷多个",
        level="undergraduate",
    )

    md = result.to_markdown()
    assert "## 完整证明" in md, "缺少 ## 完整证明"
    proof_section = md.split("## 完整证明")[1]
    # 截到下一节
    for marker in ("## 具体例子", "## 延伸阅读"):
        if marker in proof_section:
            proof_section = proof_section.split(marker)[0]
    assert len(proof_section.strip()) > 100, "完整证明内容太短"
    print(f"\n完整证明节片段: {proof_section[:300]}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_examples_renamed():
    """3.7 具体例子节存在（不再是 ## 例子）"""
    from modes.learning.pipeline import run_learning_pipeline

    result = await run_learning_pipeline(
        "证明素数有无穷多个",
        level="undergraduate",
    )

    md = result.to_markdown()
    assert "## 具体例子" in md, "缺少 ## 具体例子"
    ex_section = md.split("## 具体例子")[1].strip()
    assert len(ex_section) > 50, "具体例子内容太短"
    print(f"\n具体例子节片段: {ex_section[:200]}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_level_difference():
    """3.3 undergraduate 与 graduate 输出有差异"""
    from modes.learning.pipeline import run_learning_pipeline

    ug_result = await run_learning_pipeline(
        "Prove that the multiplicative group of a finite field is cyclic.",
        level="undergraduate",
        include_prereqs=False,
    )

    grad_result = await run_learning_pipeline(
        "Prove that the multiplicative group of a finite field is cyclic.",
        level="graduate",
        include_prereqs=False,
    )

    assert ug_result.to_markdown() != grad_result.to_markdown(), "本科/研究生输出完全相同"
    print(f"\nUG output length: {len(ug_result.to_markdown())}")
    print(f"Grad output length: {len(grad_result.to_markdown())}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_learning_stream_output():
    """3.4 流式 pipeline 能产出 token，且包含 proof/examples 状态帧"""
    import time
    from modes.learning.pipeline import stream_learning_pipeline

    chunks = []
    status_steps = []
    t0 = time.time()
    first_chunk_time = None

    async for chunk in stream_learning_pipeline(
        "证明素数有无穷多个",
        level="undergraduate",
    ):
        if chunk.startswith("<!--vp-status:"):
            step = chunk.split(":")[1].split("|")[0]
            status_steps.append(step)
        if first_chunk_time is None and chunk.strip():
            first_chunk_time = time.time() - t0
        chunks.append(chunk)
        if len(chunks) >= 10:
            break

    assert len(chunks) >= 1, "流式输出未产出任何内容"
    full = "".join(chunks)
    assert len(full) > 0, "流式输出内容为空"
    print(f"\n流式测试: {len(chunks)} 个 chunk，首 chunk 延迟={first_chunk_time:.2f}s")
    print(f"  状态帧: {status_steps}")
    print(f"  前 200 字符: {full[:200]}")
