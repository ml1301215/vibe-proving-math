"""LaTeX 清理 —— 把出向用户的字符串字段中所有"非数学"的 LaTeX 控制序列剥离，
保留 `$...$` / `$$...$$` 数学块原样让前端 KaTeX 渲染。

设计原则：
  - 仅保留数学块（`$...$` / `$$...$$`）作为给 KaTeX 的载荷
  - 数学块外的 \\command{...}、\\command、\\begin{xxx}/\\end{xxx} 一律剥离
  - `\\textbf{x}` 等"文本包裹命令"保留内部内容（即变成 `x`）
  - `\\label{...}` / `\\cite{...}` / `\\ref{...}` 等"标注命令"整段移除
  - 其他单参 `\\cmd{X}` 默认保留 `X`，无参 `\\cmd` 直接删

输出保证：
  浏览器最终用户看到的 textContent 不会出现 `\\xxx` 这种裸控制序列；
  KaTeX 接管 `$...$` 后渲染为可视数学符号。
"""
from __future__ import annotations

import re
from typing import Any

# 数学块（必须放在最前面，保护原样）
_MATH_BLOCK = re.compile(r"(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)")

# 标注/版式控制命令：连同 {…} 整体移除
_LABEL_LIKE = re.compile(
    r"\\(label|cite|citep|citet|ref|eqref|nonumber|notag|qed|hfill|smallskip|medskip|bigskip|noindent|par|newline|newpage|footnote|footnotemark|footnotetext|index|marginpar)\s*\{[^{}]*\}"
)
_LABEL_BARE = re.compile(
    r"\\(label|cite|citep|citet|ref|eqref|nonumber|notag|qed|hfill|smallskip|medskip|bigskip|noindent|par|newline|newpage|maketitle)\b"
)

# \begin{env} / \end{env}（带可选参数 [..]）
_BEGIN_END = re.compile(r"\\(begin|end)\s*\{[^{}]*\}(?:\s*\[[^\[\]]*\])?")

# 文本包裹命令：保留内部
_TEXT_WRAP = re.compile(
    r"\\(text|textbf|textit|textsf|texttt|textsc|textrm|emph|underline|mathrm|mathbf|mathit|operatorname)\s*\{([^{}]*)\}"
)

# 通用单参命令：`\cmd{X}` → `X`，无参 `\cmd`（后接非字母）→ 删
_GENERIC_WITH_ARG = re.compile(r"\\([a-zA-Z]+)\s*\{([^{}]*)\}")
_GENERIC_NO_ARG = re.compile(r"\\([a-zA-Z]+)(?![a-zA-Z])")

# `~`（不换行空格）→ 普通空格
_TILDE = re.compile(r"(?<!\\)~")

# 多空格折叠
_WS = re.compile(r"[ \t]{2,}")
# 多空行折叠
_WS_LINES = re.compile(r"\n{3,}")
_CODE_BLOCK = re.compile(r"```[\s\S]*?```|`[^`\n]+`")
_PROTECTED_INLINE = re.compile(r"```[\s\S]*?```|`[^`\n]+`|https?://\S+|\$\$[\s\S]+?\$\$|\$[^$\n]+?\$")
_MATH_COMMAND = re.compile(
    r"(?<![$\\A-Za-z0-9_])"
    r"(\\(?:frac|sqrt|sum|prod|int|lim|sup|inf|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|operatorname|forall|exists|in|notin|subset|subseteq|cup|cap|leq|geq|neq|to|mapsto|mid|alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega|infty|partial|nabla|cdot|cdots|ldots|times|div|pm|mp|approx|equiv|sim|propto|circ|prime)"
    r"(?:\{[^{}]*\}|\b))"
)
_MATH_RELATION_FRAGMENT = re.compile(
    r"(?<![$\\A-Za-z0-9_])"
    r"("
    r"(?:\|?[A-Za-zΑ-Ωα-ω][A-Za-z0-9_Α-Ωα-ω]*\|?|\([^)]+\)|\{[^{}\n]{1,40}\}|[ΔΛΣΠΩα-ωΑ-Ω][A-Za-z0-9_]*)"
    r"(?:\s*(?:\^|_)\s*(?:\{[^{}]+\}|[A-Za-z0-9]+))?"
    r"(?:\s*[+\-*/]\s*(?:\|?[A-Za-z0-9Α-Ωα-ω]+\|?|\([^)]+\)|\{[^{}\n]{1,30}\})){0,4}"
    r"\s*(?:=|≡|≤|≥|<|>|∈|∉|⊂|⊆|∣|→|↦|\\in|\\notin|\\subseteq|\\subset|\\to|\\mapsto|\\leq|\\geq|\\mid)"
    r"\s*[^,\n，。、；;:：！？!?（）()]{1,80}"
    r")"
)
_UNICODE_MATH_MAP = {
    "∈": r" \in ",
    "∉": r" \notin ",
    "≤": r" \leq ",
    "≥": r" \geq ",
    "⊂": r" \subset ",
    "⊆": r" \subseteq ",
    "∣": r" \mid ",
    "→": r" \to ",
    "↦": r" \mapsto ",
    "≡": r" \equiv ",
    "≈": r" \approx ",
    "Δ": r"\Delta",
}


def _clean_outside(t: str) -> str:
    """对数学块外的文本做 LaTeX 剥离。"""
    if not t:
        return t
    # 1) 环境 \begin{xxx}/\end{xxx}
    t = _BEGIN_END.sub("", t)
    # 2) 标注命令整段删
    t = _LABEL_LIKE.sub("", t)
    t = _LABEL_BARE.sub("", t)
    # 3) 文本包裹命令保留内部
    # 多次运行直至稳定（嵌套 \textbf{\emph{x}} → x）
    for _ in range(3):
        new_t = _TEXT_WRAP.sub(r"\2", t)
        if new_t == t:
            break
        t = new_t
    # 4) 通用单参 \cmd{X} → X
    for _ in range(3):
        new_t = _GENERIC_WITH_ARG.sub(r"\2", t)
        if new_t == t:
            break
        t = new_t
    # 5) 无参 \cmd → 删
    t = _GENERIC_NO_ARG.sub("", t)
    # 6) `~` → 空格
    t = _TILDE.sub(" ", t)
    return t


def strip_non_math_latex(s: Any) -> Any:
    """保留 `$...$` / `$$...$$`，剥离数学块外的所有 LaTeX 控制序列与环境。

    - None / 非 str：原样返回
    - 空串："" 直接返回
    """
    if s is None:
        return None
    if not isinstance(s, str):
        return s
    if not s:
        return s

    parts: list[str] = []
    last = 0
    for m in _MATH_BLOCK.finditer(s):
        parts.append(_clean_outside(s[last:m.start()]))
        parts.append(m.group(0))  # 数学块原样保留
        last = m.end()
    parts.append(_clean_outside(s[last:]))

    out = "".join(parts)
    out = _WS.sub(" ", out)
    out = _WS_LINES.sub("\n\n", out)
    return out.strip()


def ensure_inline_math(s: Any) -> Any:
    r"""给明显的裸数学片段补 `$...$`，作为前端渲染前的轻量兜底。

    目标不是完美公式解析，只处理高度确信的片段：
    - 裸露的 LaTeX 数学命令，如 `\alpha`, `\subseteq`, `\mathbb{R}`
    - 关系式/成员关系/箭头片段，如 `p=3`, `g \in G`, `f: X → Y`
    """
    if s is None:
        return None
    if not isinstance(s, str):
        return s
    if not s:
        return s

    placeholders: list[str] = []

    def _stash(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f"\u0000MATH{len(placeholders) - 1}\u0000"

    def _normalize_math_fragment(fragment: str) -> str:
        out = fragment
        for raw, latex in _UNICODE_MATH_MAP.items():
            out = out.replace(raw, latex)
        out = _WS.sub(" ", out)
        return out.strip()

    protected = _PROTECTED_INLINE.sub(_stash, s)
    protected = _MATH_COMMAND.sub(lambda m: f"${_normalize_math_fragment(m.group(1))}$", protected)
    protected = _MATH_RELATION_FRAGMENT.sub(lambda m: f"${_normalize_math_fragment(m.group(1))}$", protected)

    for idx, block in enumerate(placeholders):
        protected = protected.replace(f"\u0000MATH{idx}\u0000", block)
    return protected


def strip_non_math_latex_preserve_code(s: Any) -> Any:
    """类似 strip_non_math_latex，但保护 Markdown 代码块/行内代码。

    用于 Markdown 正文清洗，避免 traceback、Lean 代码、内联代码中的反斜杠被误删。
    """
    if s is None:
        return None
    if not isinstance(s, str):
        return s
    if not s:
        return s

    placeholders: list[str] = []

    def _stash(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f"\u0000CODE{len(placeholders) - 1}\u0000"

    protected = _CODE_BLOCK.sub(_stash, s)
    cleaned = strip_non_math_latex(protected)
    for i, block in enumerate(placeholders):
        cleaned = cleaned.replace(f"\u0000CODE{i}\u0000", block)
    return cleaned


def sanitize_dict(d: Any, fields: tuple[str, ...] | None = None) -> Any:
    """对 dict 中指定 key 的字符串值做 strip_non_math_latex。

    - fields=None 表示所有字符串字段都过一遍
    - 嵌套 dict / list 递归处理
    """
    if isinstance(d, dict):
        out: dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                out[k] = sanitize_dict(v, fields)
            elif isinstance(v, str) and (fields is None or k in fields):
                out[k] = strip_non_math_latex(v)
            else:
                out[k] = v
        return out
    if isinstance(d, list):
        return [sanitize_dict(x, fields) for x in d]
    return d
