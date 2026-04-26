"""端到端测试：学习模式 pipeline（新四节结构 + MacTutor API）

新四节：数学背景 | 前置知识 | 完整证明 | 具体例子

验收标准：
  1. 数学背景：有 ## 数学背景 标题，有实质内容，附来源归因
  2. 前置知识：格式正确、无报错
  3. 完整证明：存在且有分步证明结构
  4. 具体例子：有 ### Example 结构、有教材引注
  5. 无任何"XX失败"错误消息
  6. GET /mactutor_search 端点返回合法数据
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# 测试用命题
_STMT_PRIMES = "证明素数有无穷多个"
_STMT_FIELD  = "证明有限域的乘法群是循环群"

# 新四节名称
_KNOWN = ("数学背景", "前置知识", "完整证明", "具体例子")
_SECTION_BOUNDARY = re.compile(
    r'\n## (?:' + '|'.join(_KNOWN) + r')(?:\n|$)'
)


# ── 辅助 ─────────────────────────────────────────────────────────────────────

async def _collect(statement: str, level: str = "undergraduate") -> tuple[str, list[str]]:
    """收集 stream_learning_pipeline 输出，返回 (content, status_steps)。"""
    from modes.learning.pipeline import stream_learning_pipeline
    content_parts: list[str] = []
    steps: list[str] = []
    async for chunk in stream_learning_pipeline(statement, level=level):
        if chunk.startswith("<!--vp-status:"):
            step = chunk.split(":")[1].split("|")[0]
            steps.append(step)
        elif not chunk.startswith("<!--"):
            content_parts.append(chunk)
    return "".join(content_parts), steps


def _section(output: str, heading: str) -> str:
    """提取指定 ## 标题之后、下一个管道级别 section 之前的内容。"""
    marker = f"## {heading}"
    if marker not in output:
        return ""
    _, after = output.split(marker, 1)
    m = _SECTION_BOUNDARY.search(after)
    return after[:m.start()].strip() if m else after.strip()


# ── 测试 1：全板块存在且无错误 ─────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_all_sections_present():
    """全部 4 个板块存在：数学背景 + 前置知识 + 完整证明 + 具体例子。"""
    output, steps = await _collect(_STMT_PRIMES)

    for heading in _KNOWN:
        assert f"## {heading}" in output, f"缺少 ## {heading}"
        sec = _section(output, heading)
        assert len(sec) > 40, f"## {heading} 内容太短（{len(sec)} 字）:\n{sec[:200]}"

    # 确认旧节名不再出现
    assert "## 例子" not in output,   "不应存在已废弃的 ## 例子"
    assert "## 延伸阅读" not in output, "不应存在已废弃的 ## 延伸阅读"

    # 无错误消息
    for marker in ("分析失败", "生成失败", "TypeError", "Exception"):
        assert marker not in output, f"输出中含错误标记 '{marker}'"

    print(f"\n[test_all_sections_present] 总输出 {len(output)} 字，steps={steps}")
    for h in _KNOWN:
        print(f"  {h}={len(_section(output, h))}字")


# ── 测试 2：数学背景来源归因存在 ─────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_background_attribution():
    """数学背景板块末尾有来源归因（MacTutor 或 blockquote 来源行）。"""
    output, _ = await _collect(_STMT_PRIMES)
    bg = _section(output, "数学背景")
    assert len(bg) > 80, f"数学背景内容太短（{len(bg)} 字）"
    has_attr = any(kw in bg for kw in ("MacTutor", "来源", "Source", "St Andrews"))
    assert has_attr, f"数学背景板块缺少来源归因，当前内容末尾：\n{bg[-300:]}"


# ── 测试 3：前置知识数量合理 ──────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_prereq_count_elementary():
    """'素数无穷多'（基础命题）前置知识 1–4 条，学习路径 ≥ 2 步。"""
    from skills.prerequisite_map import prerequisite_map
    pmap = await prerequisite_map(_STMT_PRIMES, level="undergraduate")

    n = len(pmap.prerequisites)
    assert 1 <= n <= 4, (
        f"基础命题前置知识数量应为 1-4，实际 {n} 条：\n"
        + "\n".join(f"  - {p.concept}" for p in pmap.prerequisites)
    )
    assert len(pmap.learning_path) >= 2, f"学习路径步骤太少：{pmap.learning_path}"
    print(f"\n[test_prereq_count_elementary] {n} 条：{[p.concept for p in pmap.prerequisites]}")


# ── 测试 4：前置知识字段格式 ───────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_prereq_format():
    """每条前置知识有 concept / type / description，type 为合法值。"""
    from skills.prerequisite_map import prerequisite_map
    pmap = await prerequisite_map(_STMT_FIELD, level="undergraduate")

    assert pmap.prerequisites, "前置知识列表为空"
    for p in pmap.prerequisites:
        assert p.concept.strip(), f"concept 为空: {p}"
        assert p.type in ("definition", "theorem", "technique"), \
            f"type 非法: {p.type!r}（concept={p.concept}）"
        assert len(p.description.strip()) >= 10, \
            f"description 太短: {p.description!r}"

    print(f"\n[test_prereq_format] {len(pmap.prerequisites)} 条前置知识：")
    for p in pmap.prerequisites:
        print(f"  [{p.type}] {p.concept}: {p.description[:70]}")


# ── 测试 5：完整证明有分步结构 ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_proof_structure():
    """完整证明板块有实质内容（> 200 字），且包含分步或结构性标记。"""
    output, _ = await _collect(_STMT_PRIMES)
    proof = _section(output, "完整证明")
    assert len(proof) > 200, f"完整证明内容太短（{len(proof)} 字）:\n{proof[:300]}"

    # 分步标记：Step / 步骤 / 数字列表 / **Step
    step_markers = ("Step ", "步骤", "**Step", "∎", "QED", "1.", "2.", "**1")
    has_steps = any(m in proof for m in step_markers)
    assert has_steps, f"完整证明缺少分步结构标记:\n{proof[:400]}"

    print(f"\n[test_proof_structure] 完整证明 {len(proof)} 字")
    print(f"  前300字: {proof[:300]}")


# ── 测试 6：具体例子有 ### 结构和引注 ─────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_examples_structure():
    """具体例子板块有 ### 子标题，且含教材引注。"""
    output, _ = await _collect(_STMT_FIELD)
    ex = _section(output, "具体例子")
    assert len(ex) > 80, f"具体例子内容太短（{len(ex)} 字）"
    assert "### " in ex, f"具体例子板块缺少 ### 子标题（前300字）：\n{ex[:300]}"

    cite_keywords = (
        "参见", "cf.", "参考", "See", "Reference", "refer",
        "Dummit", "Lang", "Rudin", "Hartshorne", "Atiyah",
        "Algebra", "Analysis", "Hungerford", "Jacobson", "Artin",
        "textbook", "chapter", "§", "p.",
    )
    has_cite = any(kw in ex for kw in cite_keywords)
    assert has_cite, f"具体例子板块缺少教材引注\n末尾300字：\n{ex[-300:]}"

    print(f"\n[test_examples_structure] 具体例子 {len(ex)} 字")


# ── 测试 7：状态帧顺序正确 ────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_status_frames_order():
    """SSE 状态帧按 background → prereq → proof → examples → done 顺序出现。"""
    _, steps = await _collect(_STMT_PRIMES)
    expected_order = ["background", "prereq", "proof", "examples", "done"]
    filtered = [s for s in steps if s in expected_order]
    # 验证每个期望步骤都出现
    for s in expected_order:
        assert s in filtered, f"缺少状态帧 '{s}'，实际步骤：{steps}"
    # 验证顺序正确
    assert filtered == sorted(filtered, key=lambda x: expected_order.index(x)), \
        f"状态帧顺序不对：{filtered}"
    print(f"\n[test_status_frames_order] steps={steps}")


# ── 测试 8：GET /mactutor_search 端点 ────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_mactutor_search_endpoint():
    """GET /mactutor_search?q=Euclid+primes 返回合法 JSON 结构。"""
    import httpx
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8080", timeout=20) as client:
        resp = await client.get("/mactutor_search", params={"q": "Euclid primes", "top_k": 3})

    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
    data = resp.json()
    assert "query" in data,      "响应缺少 query 字段"
    assert "results" in data,    "响应缺少 results 字段"
    assert "content" in data,    "响应缺少 content 字段"
    assert "source_url" in data, "响应缺少 source_url 字段"
    assert isinstance(data["results"], list), "results 应为列表"

    print(f"\n[test_mactutor_search_endpoint] query={data['query']}")
    print(f"  results={len(data['results'])} 条，content={len(data.get('content',''))} 字")
    for r in data["results"][:3]:
        print(f"  - [{r.get('score')}] {r.get('title')} → {r.get('url')}")
