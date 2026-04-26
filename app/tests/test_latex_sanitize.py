"""单元测试：app/core/text_sanitize.py。

覆盖三类输入：
 1. 数学块（`$...$` / `$$...$$`）必须原样保留
 2. 标注命令（\\label / \\cite / \\ref / \\eqref / ...）必须整段移除
 3. 文本包裹命令（\\textbf / \\emph / 通用 \\cmd{X}）必须只保留内部
"""
from __future__ import annotations

import re

import pytest

from core.text_sanitize import (
    ensure_inline_math,
    sanitize_dict,
    strip_non_math_latex,
    strip_non_math_latex_preserve_code,
)


# 残留检测：除 `$...$` 数学块外，不允许再出现 `\\xxx`
_LEAK = re.compile(r"\\[a-zA-Z]+")


def _no_leak(s: str) -> bool:
    """删掉所有 `$...$` 数学块后，剩余文本不能含 `\\cmd`。"""
    stripped = re.sub(r"\$\$[\s\S]+?\$\$|\$[^$\n]+?\$", "", s)
    return _LEAK.search(stripped) is None


# ────────────────────────────────────────────────
# 1) 数学块保留
# ────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw",
    [
        r"设 $x \in \mathbb{R}$，证明 $x^2 \ge 0$。",
        r"$$\int_0^1 x^2\,dx = \frac{1}{3}$$",
        r"考虑 $a + b = c$ 与 $$\sum_{i=1}^n i = \frac{n(n+1)}{2}$$。",
    ],
)
def test_math_block_preserved(raw: str) -> None:
    out = strip_non_math_latex(raw)
    # 至少保留一个 $...$
    assert "$" in out, f"math delimiters lost: {out!r}"
    # 保留内的 \cmd 不被剥离
    if r"\frac" in raw:
        assert r"\frac" in out
    if r"\mathbb" in raw:
        assert r"\mathbb" in out


# ────────────────────────────────────────────────
# 2) 标注命令整段删
# ────────────────────────────────────────────────
def test_label_cite_ref_removed() -> None:
    raw = r"由定理 \ref{thm:main} 与 \cite{Knuth1984} 可知，证毕\qed\label{eq:1}。"
    out = strip_non_math_latex(raw)
    assert _no_leak(out), f"residual LaTeX: {out!r}"
    assert "\\ref" not in out
    assert "\\cite" not in out
    assert "\\label" not in out
    assert "\\qed" not in out


def test_eqref_and_footnote_removed() -> None:
    raw = r"\eqref{eq:2} 与脚注\footnote{见附录 A}。"
    out = strip_non_math_latex(raw)
    assert _no_leak(out)
    assert "附录" not in out  # 整段 \footnote{...} 包含的内容也一并剔除


# ────────────────────────────────────────────────
# 3) 文本包裹命令保留内部
# ────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw,must_have",
    [
        (r"\textbf{重要}：必须满足。", "重要"),
        (r"\emph{Cauchy} 不等式", "Cauchy"),
        (r"\textit{核心思路}是反证。", "核心思路"),
        (r"\underline{下划线} 文字", "下划线"),
    ],
)
def test_text_wrap_keeps_inner(raw: str, must_have: str) -> None:
    out = strip_non_math_latex(raw)
    assert _no_leak(out), f"residual LaTeX: {out!r}"
    assert must_have in out


def test_nested_text_wrap() -> None:
    raw = r"\textbf{\emph{粗斜体}}文字"
    out = strip_non_math_latex(raw)
    assert _no_leak(out)
    assert "粗斜体" in out


# ────────────────────────────────────────────────
# 4) 环境块剥离
# ────────────────────────────────────────────────
def test_begin_end_environment_removed() -> None:
    raw = r"\begin{proof}由 $a = b$ 得 $a^2 = b^2$。\end{proof}"
    out = strip_non_math_latex(raw)
    assert _no_leak(out)
    assert "$a = b$" in out and "$a^2 = b^2$" in out


# ────────────────────────────────────────────────
# 5) 边界 / 鲁棒性
# ────────────────────────────────────────────────
@pytest.mark.parametrize(
    "v",
    [None, "", 0, 3.14, True, ["a", "b"], {"k": "v"}],
)
def test_strip_non_string_passthrough(v) -> None:
    """非字符串输入应原样返回，避免误伤上层数据结构。"""
    assert strip_non_math_latex(v) == v


def test_tilde_to_space() -> None:
    raw = r"Cauchy~Schwarz 不等式"
    out = strip_non_math_latex(raw)
    assert "~" not in out
    assert "Cauchy Schwarz" in out or "Cauchy  Schwarz" in out  # 折叠后单个空格


def test_preserve_code_blocks_when_sanitizing_markdown() -> None:
    raw = (
        "证明思路：\\textbf{先化简}。\n\n"
        "```text\n"
        "C:\\Users\\me\\proof.lean: error: unknown identifier\n"
        "```\n"
        "行内代码 `\\ref{foo}` 也应原样保留。"
    )
    out = strip_non_math_latex_preserve_code(raw)
    assert "先化简" in out
    assert "\\textbf" not in out
    assert "C:\\Users\\me\\proof.lean" in out
    assert "`\\ref{foo}`" in out


# ────────────────────────────────────────────────
# 6) sanitize_dict 递归
# ────────────────────────────────────────────────
def test_sanitize_dict_recurses() -> None:
    raw = {
        "verdict": "Correct",
        "statement": r"由 \cite{x} 可知 $x^2 \ge 0$",
        "proof_steps": [
            {"text": r"\textbf{Step 1}: 取 $x \in \mathbb{R}$", "verdict": "passed"},
            {"text": r"\label{eq:1} 故得证", "verdict": "passed"},
        ],
        "stats": {"theorems_checked": 1},
    }
    out = sanitize_dict(raw)
    assert out["verdict"] == "Correct"
    assert _no_leak(out["statement"])
    assert "$x^2 \\ge 0$" in out["statement"]
    assert _no_leak(out["proof_steps"][0]["text"])
    assert "Step 1" in out["proof_steps"][0]["text"]
    assert _no_leak(out["proof_steps"][1]["text"])
    assert out["stats"]["theorems_checked"] == 1  # 数值不动


def test_sanitize_dict_specific_fields_only() -> None:
    raw = {"a": r"\textbf{保留}", "b": r"\textbf{忽略}"}
    out = sanitize_dict(raw, fields=("a",))
    assert "保留" in out["a"] and "\\textbf" not in out["a"]
    assert out["b"] == r"\textbf{忽略}"  # 未指定字段不动


def test_ensure_inline_math_wraps_and_normalizes_unicode_math() -> None:
    raw = "设p=3，且 g ∈ G，并满足 f: X → Y。"
    out = ensure_inline_math(raw)
    assert "$p=3$" in out
    assert "$g \\in G$" in out
    assert "\\to" in out
