"""MinerU PDF 输出后处理修复模块。

修复 MinerU vlm/pipeline 模型在 PDF 解析中产生的系统性问题：
  1. 预组合字符 —— PDF 字体将 é 拆成 e + 独立音标符 ´
  2. \text{} 字符间距 —— PDF 逐字提取导致 "f o r a l l"
  3. 丢失 \to 箭头 —— PDF U+2192 箭头被 vlm 识别为双空格
  4. display math 中数字序列 —— tabular 排版导致 "1 2 3 4"
  5. Mojibake —— 编码回退产生 "Â´" 等乱码（via ftfy）

主入口：
    fixed_text = fix_all(markdown_text)

所有修复均为保守策略，不会修改 LaTeX math 符号语义（仅清理排版噪声）。
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

try:
    import ftfy as _ftfy
    _HAS_FTFY = True
except ImportError:
    _HAS_FTFY = False


# ── 修复 1：独立音标符 + 字母 → 预组合字符 ─────────────────────────────────

_DIACRITIC_MAP: dict[str, str] = {}


def _build_diacritic_map() -> None:
    """构建"独立音标符 + 字母"→ 预组合字符的映射表。"""
    pairs = [
        ('\u00b4', '\u0301'),  # ´ ACUTE ACCENT         → COMBINING ACUTE
        ('\u0060', '\u0300'),  # ` GRAVE ACCENT          → COMBINING GRAVE
        ('\u00a8', '\u0308'),  # ¨ DIAERESIS             → COMBINING DIAERESIS
        ('\u02c6', '\u0302'),  # ˆ MODIFIER CIRCUMFLEX   → COMBINING CIRCUMFLEX
        ('\u02dc', '\u0303'),  # ˜ SMALL TILDE           → COMBINING TILDE
        ('\u02dd', '\u030b'),  # ˝ DOUBLE ACUTE          → COMBINING DOUBLE ACUTE
        ('\u02c7', '\u030c'),  # ˇ CARON                 → COMBINING CARON
        ('\u02d8', '\u0306'),  # ˘ BREVE                 → COMBINING BREVE
        ('\u02d9', '\u0307'),  # ˙ DOT ABOVE             → COMBINING DOT ABOVE
        ('\u00b8', '\u0327'),  # ¸ CEDILLA               → COMBINING CEDILLA
        ('\u02db', '\u0328'),  # ˛ OGONEK                → COMBINING OGONEK
        ('\u00af', '\u0304'),  # ¯ MACRON                → COMBINING MACRON
        ('\u02da', '\u030a'),  # ˚ RING ABOVE            → COMBINING RING ABOVE
    ]
    base_letters = 'aeiouycnszrldtgAEIOUYCNSZRLDTG'
    for standalone, combining in pairs:
        for letter in base_letters:
            combined = unicodedata.normalize('NFC', letter + combining)
            if combined != letter + combining:
                _DIACRITIC_MAP[standalone + letter] = combined
                _DIACRITIC_MAP[letter + standalone] = combined


_build_diacritic_map()


def fix_precomposed_chars(text: str) -> str:
    """将独立音标符+字母替换为预组合 Unicode 字符；调用 ftfy 修复 Mojibake。"""
    if _HAS_FTFY:
        text = _ftfy.fix_text(text)
    for pattern, replacement in _DIACRITIC_MAP.items():
        text = text.replace(pattern, replacement)
    return text


# ── 修复 2：\text{} 内字符间距 ───────────────────────────────────────────────

_TEXT_WORD_MAP: dict[str, str] = {
    'forall':  r'\forall',
    'exists':  r'\exists',
    'const':   r'\mathrm{const}',
    'sup':     r'\sup',
    'inf':     r'\inf',
    'max':     r'\max',
    'min':     r'\min',
    'lim':     r'\lim',
    'limsup':  r'\limsup',
    'liminf':  r'\liminf',
    'det':     r'\det',
    'log':     r'\log',
    'exp':     r'\exp',
    'sin':     r'\sin',
    'cos':     r'\cos',
    'tan':     r'\tan',
}


def fix_spaced_text_commands(text: str) -> str:
    r"""修复 \text{f o r a l l} → \forall（或 \text{forall}）。"""
    def _collapse(m: re.Match) -> str:
        content = m.group(1)
        tokens = content.split()
        if len(tokens) >= 3 and all(len(t) == 1 for t in tokens):
            word = ''.join(tokens)
            return _TEXT_WORD_MAP.get(word, r'\text{' + word + '}')
        return m.group(0)

    return re.sub(r'\\text\s*\{([^}]{3,})\}', _collapse, text)


# ── 修复 3：数学环境中丢失的 \to 箭头 ───────────────────────────────────────

_ARROW_RIGHT_TRIGGERS = (
    r'\\mathbb', r'\\mathcal', r'\\mathfrak', r'\\mathbf',
    r'\\mathrm', r'\\mathit', r'\\mathsf', r'\\infty',
)
_ARROW_RIGHT_PAT = '|'.join(_ARROW_RIGHT_TRIGGERS)


def _fix_arrows_in_math(math: str) -> str:
    math = re.sub(
        r'([A-Za-z}\]^+])  (' + _ARROW_RIGHT_PAT + r')',
        r'\1 \\to \2', math,
    )
    math = re.sub(r'([A-Za-z}\]])  (\\infty)', r'\1 \\to \2', math)
    math = re.sub(r'(?<=[A-Z] )([A-Z])  ([A-Z]\b)', r'\1 \\to \2', math)
    return math


def fix_missing_arrows(text: str) -> str:
    r"""在 display math 和 inline math 中修复双空格 → \to。"""
    def fix_display(m: re.Match) -> str:
        return '$$\n' + _fix_arrows_in_math(m.group(1)) + '\n$$'

    text = re.sub(r'\$\$\n(.*?)\n\$\$', fix_display, text, flags=re.DOTALL)

    def fix_inline(m: re.Match) -> str:
        return '$' + _fix_arrows_in_math(m.group(1)) + '$'

    text = re.sub(
        r'(?<!\$)\$(?!\$)([^$\n]{1,300}?)(?<!\$)\$(?!\$)',
        fix_inline, text,
    )
    return text


# ── 修复 4：display math 中大数字字符间距 ────────────────────────────────────

def fix_digit_sequences(text: str) -> str:
    """修复 display math 中 "5 6 2 1" → "5621"（6+ 位以上才合并）。"""
    def _merge_digits(s: str) -> str:
        return re.sub(
            r'(?<!\d)(\d(?: \d){5,})(?!\d)',
            lambda m: m.group(0).replace(' ', ''),
            s,
        )

    def fix_display(m: re.Match) -> str:
        return '$$\n' + _merge_digits(m.group(1)) + '\n$$'

    return re.sub(r'\$\$\n(.*?)\n\$\$', fix_display, text, flags=re.DOTALL)


# ── 主修复入口 ────────────────────────────────────────────────────────────────

def fix_all(text: str) -> str:
    """依序应用全部修复，返回修复后的 Markdown 文本。"""
    text = fix_precomposed_chars(text)
    text = fix_spaced_text_commands(text)
    text = fix_missing_arrows(text)
    text = fix_digit_sequences(text)
    return text


# ── Markdown 分块（供 review_paper_pages 使用）────────────────────────────────

_HEADING_RE = re.compile(r'^#{1,4}\s+\S', re.MULTILINE)


def split_markdown_into_chunks(
    text: str,
    max_chars: int = 4000,
) -> list[str]:
    """将 Markdown 文本按节标题切分成审查友好的块列表。

    优先在 `#` 标题处切割；单个 section 超过 max_chars 时进一步按段落切。
    返回非空字符串列表，保持顺序。
    """
    if not text.strip():
        return []

    # 找出所有标题位置
    positions = [m.start() for m in _HEADING_RE.finditer(text)]
    if not positions:
        return _split_by_paragraphs(text, max_chars)

    # 按标题位置切段
    sections: list[str] = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        section = text[pos:end].strip()
        if section:
            sections.append(section)

    # 前置内容（标题前）
    preamble = text[: positions[0]].strip()
    if preamble:
        sections.insert(0, preamble)

    # 超过 max_chars 的 section 进一步切割
    chunks: list[str] = []
    for sec in sections:
        if len(sec) <= max_chars:
            chunks.append(sec)
        else:
            chunks.extend(_split_by_paragraphs(sec, max_chars))

    return [c for c in chunks if c.strip()]


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    """按段落（双换行）切分，超长段落强制截断。"""
    paragraphs = re.split(r'\n{2,}', text)
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 2 <= max_chars:
            buf = (buf + "\n\n" + para).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= max_chars:
                buf = para
            else:
                for i in range(0, len(para), max_chars):
                    piece = para[i: i + max_chars].strip()
                    if piece:
                        chunks.append(piece)
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks
