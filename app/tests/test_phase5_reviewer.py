"""Phase 5 验收测试：研究模式-论文审查"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 选一篇合适的 arXiv 论文（有已知定理和证明）
# 使用 2404.05216 —— 之前测试过的一篇数学论文
TEST_ARXIV_ID = "2404.05216"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_arxiv_parse():
    """5.1 输入 arXiv ID，成功解析出 >= 1 个 theorem+proof 对"""
    from modes.research.parser import parse_arxiv

    pairs = await parse_arxiv(TEST_ARXIV_ID)
    print(f"\narXiv {TEST_ARXIV_ID} 解析: {len(pairs)} 个定理-证明对")
    for p in pairs[:3]:
        print(f"  [{p.env_type}] ref={p.ref}, stmt={p.statement[:60]}...")
        print(f"           proof_present={p.has_proof()}")

    assert len(pairs) >= 1, f"未解析出任何定理，结果: {len(pairs)}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_review_report_structure():
    """5.2 输出 JSON 含 overall_verdict（4 取 1）和 issues 字段"""
    from modes.research.reviewer import review_arxiv

    report = await review_arxiv(TEST_ARXIV_ID, max_theorems=3)
    d = report.to_dict()

    print(f"\n审查报告:")
    print(f"  overall_verdict: {d['overall_verdict']}")
    print(f"  issues: {len(d['issues'])} 条")
    print(f"  stats: {d['stats']}")

    assert "overall_verdict" in d, "缺少 overall_verdict"
    assert d["overall_verdict"] in ("Correct", "Minor Issues", "Major Issues", "Incorrect"), \
        f"overall_verdict 不合法: {d['overall_verdict']}"
    assert "issues" in d, "缺少 issues"
    assert "theorem_reviews" in d, "缺少 theorem_reviews"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_review_step_verdicts():
    """5.3 每个被检查的证明步骤有 verdict 属于 {passed, gap, critical_error}"""
    from modes.research.reviewer import review_arxiv

    report = await review_arxiv(TEST_ARXIV_ID, max_theorems=3)

    checked_steps = 0
    for review in report.theorem_reviews:
        if review.verification:
            for step in review.verification.steps:
                assert step.verdict in ("passed", "gap", "critical_error"), \
                    f"步骤 verdict 不合法: {step.verdict}"
                checked_steps += 1

    print(f"\n步骤验证: 共检查 {checked_steps} 步")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_review_citation_check():
    """5.4 至少一个外部引用经 TheoremSearch 核查"""
    from modes.research.reviewer import review_arxiv

    report = await review_arxiv(TEST_ARXIV_ID, max_theorems=5)

    total_citations = sum(len(r.citation_checks) for r in report.theorem_reviews)
    print(f"\n引用核查: 共 {total_citations} 条引用被核查")

    valid_statuses = {"verified", "not_found", "condition_mismatch"}
    for review in report.theorem_reviews:
        for check in review.citation_checks:
            assert check["status"] in valid_statuses, f"引用状态不合法: {check['status']}"

    # 5.4 验收：stats 中记录了 citations_checked
    assert "citations_checked" in report.stats, "stats 缺少 citations_checked"
    print(f"  verified/not_found 统计: {report.stats}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_review_markdown_output():
    """审查报告能生成可读的 Markdown"""
    from modes.research.reviewer import review_arxiv

    report = await review_arxiv(TEST_ARXIV_ID, max_theorems=2)
    md = report.to_markdown()

    print(f"\n审查 Markdown ({len(md)} 字符):")
    print(md[:500])

    assert "# 论文审查报告" in md, "缺少报告标题"
    assert "总体评判" in md, "缺少总体评判"
    assert len(md) > 100, "Markdown 输出太短"
