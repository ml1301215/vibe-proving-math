"""Phase 5+ 验收：review_text() 三条路径覆盖（不依赖外部网络/LLM）。

通过 monkeypatch 注入：
- _review_single_theorem  → 避免真实 LLM verify_sequential 调用
- _llm_extract_from_text  → 避免真实 LLM 解析

涵盖：
1. 多定理路径（含 \\begin{theorem}/\\begin{proof}）
2. LLM 兜底解析路径（结构化提取为空 → LLM 返回 1 条）
3. 单证明降级路径（结构 + LLM 都为空 → 整段文本视为单证明）
4. 空输入抛 ValueError
5. 截断行为（超长文本被截到 50000）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


LATEX_MULTI = r"""
Some preamble text.

\begin{theorem}\label{thm:main}
For any prime $p > 3$, $p^2 \equiv 1 \pmod{24}$.
\end{theorem}
\begin{proof}
Step 1: Since $p > 3$, $p$ is coprime to 24.
Step 2: By Euler's theorem, $p^{\phi(24)} \equiv 1 \pmod{24}$.
Step 3: Since $\phi(24) = 8$ and we need $p^2$, ...
\end{proof}

\begin{lemma}\label{lem:aux}
Auxiliary lemma statement here.
\end{lemma}
\begin{proof}
A short proof body that is long enough to count.
\end{proof}
"""

PROOF_PLAIN = (
    "证明：设 G 是有限群，H 是 G 的子群。考察 G 关于 H 的左陪集分解，"
    "由 Lagrange 定理可知 |H| 整除 |G|。再由 ..."
)


def _make_fake_review(captured: list):
    """构造一个 fake _review_single_theorem，记录 (env_type, statement, proof) 并返回 Correct。"""
    from modes.research import reviewer as R

    async def fake_review(tp, idx, **kwargs):
        captured.append({
            "env_type": tp.env_type,
            "ref": tp.ref,
            "statement": tp.statement,
            "proof": tp.proof,
        })
        return R.TheoremReview(
            theorem=tp,
            verification=None,
            citation_checks=[],
            issues=[],
            verdict="Correct",
        )
    return fake_review


# ── 1. 多定理路径 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_multi_theorem(monkeypatch):
    """有 \\begin{theorem} → 走结构化抽取，至少被检视一个定理。"""
    from modes.research import reviewer as R

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    report = await R.review_text(LATEX_MULTI)

    assert report.stats["theorems_checked"] >= 1
    assert report.overall_verdict == "Correct"
    # 多定理路径不会带 fallback 字段
    assert "fallback" not in report.stats
    # captured 至少有一个，env_type 不是 'proof'（说明走了结构化抽取）
    assert captured, "_review_single_theorem 未被调用"
    assert any(c["env_type"] in {"theorem", "lemma"} for c in captured), \
        f"应解析出 theorem/lemma 类型，实际: {[c['env_type'] for c in captured]}"


# ── 2. LLM 兜底解析路径 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_llm_fallback(monkeypatch):
    """无结构化环境但 LLM 能识别 → 走 _llm_extract_from_text。"""
    from modes.research import reviewer as R
    from modes.research import parser as P

    plain_text = (
        "Theorem 1. The sum of two even integers is even.\n"
        "Proof. Let a = 2m and b = 2n. Then a+b = 2(m+n). QED.\n"
    )

    async def fake_llm(text, source, lang="zh"):
        return [P.TheoremProofPair(
            env_type="theorem",
            ref=None,
            statement="The sum of two even integers is even.",
            proof="Let a = 2m and b = 2n. Then a+b = 2(m+n).",
            source=source,
        )]
    # reviewer.py 内部从 parser 导入符号到自己的命名空间，所以 patch 两处都更稳。
    monkeypatch.setattr(R, "_llm_extract_from_text", fake_llm)
    monkeypatch.setattr(P, "_llm_extract_from_text", fake_llm)

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    report = await R.review_text(plain_text)

    assert report.stats["theorems_checked"] == 1
    assert report.overall_verdict == "Correct"
    assert "fallback" not in report.stats
    assert captured[0]["env_type"] == "theorem"


# ── 3. 单证明降级路径 ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_single_proof_fallback(monkeypatch):
    """无结构 + LLM 也提不出 → 单证明降级。"""
    from modes.research import reviewer as R
    from modes.research import parser as P

    async def empty_llm(text, source, lang="zh"):
        return []
    monkeypatch.setattr(R, "_llm_extract_from_text", empty_llm)
    monkeypatch.setattr(P, "_llm_extract_from_text", empty_llm)

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    report = await R.review_text(PROOF_PLAIN)

    assert report.stats["theorems_checked"] == 1
    assert report.stats.get("fallback") == "single_proof", \
        "单证明路径必须打 fallback 标记"
    assert captured, "_review_single_theorem 未被调用"
    pair = captured[0]
    assert pair["env_type"] == "proof"
    # statement 是占位提示，不应为空，且应包含"未单独提供命题"字样
    assert pair["statement"] and "未单独提供命题" in pair["statement"]
    assert PROOF_PLAIN[:20] in pair["proof"]


# ── 4. 空输入 ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_empty_raises():
    from modes.research.reviewer import review_text
    with pytest.raises(ValueError):
        await review_text("   ")
    with pytest.raises(ValueError):
        await review_text("")


# ── 5. 超长截断 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_truncates_long_input(monkeypatch):
    """50000 字符以上的输入会被截断；不应崩溃。"""
    from modes.research import reviewer as R
    from modes.research import parser as P

    async def empty_llm(text, source, lang="zh"):
        return []
    monkeypatch.setattr(R, "_llm_extract_from_text", empty_llm)
    monkeypatch.setattr(P, "_llm_extract_from_text", empty_llm)

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    long_text = "证明：" + ("a" * 60_000)
    report = await R.review_text(long_text)

    assert report.stats.get("fallback") == "single_proof"
    # 单证明降级用 _MAX_PROOF_FALLBACK = 6000，proof 长度不应超过 6000
    assert len(captured[0]["proof"]) <= 6_000


# ── 6. 报告 to_dict 结构稳定 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_text_report_dict_structure(monkeypatch):
    from modes.research import reviewer as R
    from modes.research import parser as P

    async def empty_llm(text, source, lang="zh"):
        return []
    monkeypatch.setattr(R, "_llm_extract_from_text", empty_llm)
    monkeypatch.setattr(P, "_llm_extract_from_text", empty_llm)
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review([]))

    report = await R.review_text("一段简短证明文本，足够触发兜底路径。")
    d = report.to_dict()
    for key in ("source", "overall_verdict", "stats", "issues", "theorem_reviews"):
        assert key in d, f"to_dict 缺少 {key}"
    assert d["overall_verdict"] in ("Correct", "Partial", "Incorrect", "NotChecked")


# ── 7. progress 回调（多定理路径） ─────────────────────────────────────────
import json as _json
import re as _re

# 检测残留：数学块 `$...$` 之外不应出现裸 `\xxx`
_LEAK_RE = _re.compile(r"\\[a-zA-Z]+")


def _no_residual_latex(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return True
    stripped = _re.sub(r"\$\$[\s\S]+?\$\$|\$[^$\n]+?\$", "", s)
    return _LEAK_RE.search(stripped) is None


def _walk_strings(obj):
    """递归 yield dict/list 中所有 str 值。"""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _walk_strings(x)


@pytest.mark.asyncio
async def test_progress_callback_multi_theorem(monkeypatch):
    """多定理路径下 progress 至少触发 parse / review / theorem / done 四类阶段。"""
    from modes.research import reviewer as R

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    steps: list[tuple[str, str]] = []
    results: list[dict] = []

    async def on_progress(step, msg):
        steps.append((step, msg))

    async def on_result(payload):
        results.append(payload)

    report = await R.review_text(
        LATEX_MULTI, progress=on_progress, result_cb=on_result
    )

    step_names = {s for s, _ in steps}
    assert "parse" in step_names
    assert "review" in step_names
    assert "theorem" in step_names
    assert "done" in step_names
    # result_cb 必须在 done 之前依次推送 theorem 结果
    assert results, "result_cb 应至少推送 1 条 theorem"
    for r in results:
        assert r["kind"] == "theorem"
        assert "index" in r and "data" in r
        # 推送过来的字段已应用过 sanitize
        for s in _walk_strings(r["data"]):
            assert _no_residual_latex(s), f"result 残留 LaTeX: {s!r}"
    # 最终报告 dict 也不应残留 LaTeX
    for s in _walk_strings(report.to_dict()):
        assert _no_residual_latex(s), f"final dict 残留 LaTeX: {s!r}"


@pytest.mark.asyncio
async def test_progress_callback_single_proof_fallback(monkeypatch):
    """单证明降级也要 parse / parse_llm / fallback / theorem / done。"""
    from modes.research import reviewer as R
    from modes.research import parser as P

    async def empty_llm(text, source, lang="zh"):
        return []

    monkeypatch.setattr(R, "_llm_extract_from_text", empty_llm)
    monkeypatch.setattr(P, "_llm_extract_from_text", empty_llm)

    captured: list = []
    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review(captured))

    steps: list[str] = []
    results: list[dict] = []

    async def on_progress(step, msg):
        steps.append(step)

    async def on_result(payload):
        results.append(payload)

    report = await R.review_text(
        PROOF_PLAIN, progress=on_progress, result_cb=on_result
    )

    assert "parse" in steps
    assert "fallback" in steps
    assert "theorem" in steps
    assert "done" in steps
    assert len(results) == 1 and results[0]["kind"] == "theorem"
    assert report.stats.get("fallback") == "single_proof"


@pytest.mark.asyncio
async def test_progress_callback_handles_failing_callback(monkeypatch):
    """progress 回调里抛异常不应中断主流程（_emit 用 try/except 兜住）。"""
    from modes.research import reviewer as R

    monkeypatch.setattr(R, "_review_single_theorem", _make_fake_review([]))

    async def bad_cb(*_):
        raise RuntimeError("ignored")

    report = await R.review_text(
        LATEX_MULTI, progress=bad_cb, result_cb=bad_cb
    )
    assert report.overall_verdict in {"Correct", "Partial"}


# ── 8. LaTeX 卫生：to_dict / summary_dict 出向 0 残留 ───────────────────────
@pytest.mark.asyncio
async def test_report_dicts_have_no_residual_latex(monkeypatch):
    """构造一份带大量 LaTeX 控制命令的 fake review，确保被剥离干净。"""
    from modes.research import reviewer as R

    async def fake_review(tp, idx, **kwargs):
        return R.TheoremReview(
            theorem=tp,
            verification=None,
            citation_checks=[],
            issues=[
                R.IssueReport(
                    location=r"Step \ref{eq:1}",
                    issue_type="logic_gap",
                    description=r"由 \cite{Knuth1984} 与 \textbf{关键引理}：$x^2 \ge 0$",
                    fix_suggestion=r"\emph{建议}补足 $\forall x \in \mathbb{R}$",
                    confidence=0.7,
                ),
            ],
            verdict="Minor Issues",
        )

    monkeypatch.setattr(R, "_review_single_theorem", fake_review)
    report = await R.review_text(LATEX_MULTI)

    # 主 to_dict
    full = report.to_dict()
    for s in _walk_strings(full):
        assert _no_residual_latex(s), f"to_dict 残留 LaTeX: {s!r}"

    # summary_dict
    summ = report.summary_dict()
    for s in _walk_strings(summ):
        assert _no_residual_latex(s), f"summary_dict 残留 LaTeX: {s!r}"
    # 数学块必须保留
    blob = _json.dumps(full, ensure_ascii=False)
    assert "$x^2 \\ge 0$" in blob or "$\\forall" in blob or "$x^2" in blob
