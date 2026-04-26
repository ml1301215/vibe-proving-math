"""Phase 1 验收测试：核心技能层"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 1.1 search_theorems ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_theorems_basic():
    """1.1 search_theorems 返回 >= 3 条，每条 similarity >= 0.3"""
    import httpx
    from skills.search_theorems import search_theorems

    try:
        results = await search_theorems("Fermat little theorem", top_k=8, min_sim=0.0)
        assert len(results) >= 3, f"结果太少: {len(results)}"
        for r in results:
            assert hasattr(r, "similarity"), "缺少 similarity"
            assert hasattr(r, "body"), "缺少 body"
        top = results[0]
        assert top.similarity >= 0.3, f"相似度过低: {top.similarity}"
        print(f"\nsearch_theorems: {len(results)} 条，top sim={top.similarity:.3f}, name={top.name}")
    except httpx.ReadTimeout:
        pytest.skip("TheoremSearch 超时")


# ── 1.2 prerequisite_map ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_prerequisite_map():
    """1.2 prerequisite_map 输出 >= 3 条前置知识"""
    from skills.prerequisite_map import prerequisite_map

    result = await prerequisite_map(
        "有限域的乘法群是循环群",
        level="undergraduate",
        enrich_with_search=False,  # 加速：不做 TheoremSearch 检索
    )
    assert len(result.prerequisites) >= 3, f"前置知识太少: {len(result.prerequisites)}"
    assert result.difficulty, "difficulty 为空"
    assert len(result.learning_path) >= 1, "学习路径为空"

    for p in result.prerequisites:
        assert p.concept, "concept 为空"
        assert p.description, "description 为空"

    print(f"\nprerequisite_map: {len(result.prerequisites)} 条")
    print(f"  学习路径: {' → '.join(result.learning_path[:4])}")
    for p in result.prerequisites[:3]:
        print(f"  - {p.concept} ({p.type}): {p.description[:60]}...")


# ── 1.3 direct_proving ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_direct_proving_fate_m():
    """1.3 direct_proving 输出 proof 非空且 > 100 字符，confidence > 0"""
    from skills.direct_proving import direct_proving

    # FATE-M 类型题目（简单代数题）
    statement = (
        "Prove that for any integers a and b, if a divides b and b divides a, "
        "then a = ±b."
    )
    result = await direct_proving(statement, use_search=False)

    assert result.proof, "proof 为空"
    assert len(result.proof) > 100, f"proof 太短: {len(result.proof)} 字符"
    assert result.confidence > 0, "confidence 为 0"
    assert result.status in ("proved", "partial", "failed"), f"status 非法: {result.status}"

    print(f"\ndirect_proving: status={result.status}, confidence={result.confidence:.2f}")
    print(f"  proof 前 200 字符: {result.proof[:200]}")


# ── 1.4 subgoal_decomp ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_subgoal_decomp_fate_h():
    """1.4 subgoal_decomp 输出 2-4 个子目标，每个 > 30 字符"""
    from skills.subgoal_decomp import subgoal_decomp

    # FATE-H 类型题目（研究级代数题）
    statement = (
        "Prove that every finite group G of order p^n (p prime) has a non-trivial center. "
        "(Hint: Consider the class equation of G.)"
    )
    result = await subgoal_decomp(statement)

    assert 2 <= len(result.subgoals) <= 4, f"子目标数量异常: {len(result.subgoals)}"
    for sg in result.subgoals:
        assert len(sg.statement) > 30, f"子目标太短: {sg.statement!r}"

    print(f"\nsubgoal_decomp: {len(result.subgoals)} subgoals")
    strat = result.strategy.encode("ascii", errors="replace").decode()
    print(f"  strategy: {strat[:100]}")
    for sg in result.subgoals:
        stmt = sg.statement.encode("ascii", errors="replace").decode()
        print(f"  [{sg.id}] {stmt[:80]}...")


# ── 1.5 verify_sequential ────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_verify_sequential_with_error():
    """1.5 verify_sequential 能识别含故意错误的证明"""
    from skills.verify_sequential import verify_sequential

    # 含故意错误的证明文本
    statement = "Prove that the square root of 2 is irrational."
    flawed_proof = """
Step 1: Assume √2 = p/q where gcd(p, q) = 1.
Step 2: Then 2 = p²/q², so p² = 2q².
Step 3: Therefore p² is even, so p must be even. Write p = 2k.
Step 4: By the Fundamental Theorem of Calculus, q is also even.
Step 5: But this contradicts gcd(p, q) = 1. Therefore √2 is irrational.
"""
    result = await verify_sequential(flawed_proof, statement)

    assert len(result.steps) > 0, "未返回任何步骤验证"
    assert result.overall in ("passed", "has_gaps", "critical_error")

    error_steps = [s for s in result.steps if s.verdict in ("gap", "critical_error")]
    assert len(error_steps) >= 1, "未检测到故意插入的错误（Step 4 引用了不相关定理）"

    print(f"\nverify_sequential: overall={result.overall}, {len(result.steps)} 步")
    print(f"  发现问题步骤: {len(error_steps)}")
    for s in error_steps:
        print(f"  Step {s.step_num} [{s.verdict}]: {s.reason[:100]}")


# ── 1.6 端到端：direct_proving → verify_sequential ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_end_to_end_fate_m():
    """1.6 FATE-M 题目的 direct_proving → verify_sequential 完整链路"""
    from skills.direct_proving import direct_proving
    from skills.verify_sequential import verify_sequential

    statement = (
        "Let G be a group and H be a subgroup of G. "
        "Prove that the left coset relation 'a ~ b iff a⁻¹b ∈ H' is an equivalence relation."
    )

    # Step 1: 生成证明
    proof_result = await direct_proving(statement, use_search=False)
    assert proof_result.proof, "证明为空"
    assert not proof_result.proof.startswith("LLM 调用失败"), "LLM 调用失败"

    # Step 2: 验证证明
    verify_result = await verify_sequential(proof_result.proof, statement)
    assert len(verify_result.steps) > 0, "验证返回空步骤"
    assert verify_result.overall in ("passed", "has_gaps", "critical_error")

    print(f"\n端到端测试:")
    print(f"  证明长度: {len(proof_result.proof)} 字符, confidence={proof_result.confidence:.2f}")
    print(f"  验证结果: {verify_result.overall}, {len(verify_result.steps)} 步")
    print(f"  验证摘要: {verify_result.summary[:120]}")
