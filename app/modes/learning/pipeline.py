"""学习模式 Pipeline —— 面向数学专业学生和研究人员的深度教学输出。

Pipeline 流程（4 个板块，均标注来源）：
  Card 1: 数学背景  → MacTutor 史料 + LLM 叙述（来源：MacTutor, St Andrews）
  Card 2: 前置知识  → prerequisite_map + TheoremSearch（来源：Mathlib4 定理库）
  Card 3: 完整证明  → LLM 分步证明，每步说明 why
  Card 4: 具体例子  → LLM 生成，含边界情形分析与教材引注

输出格式：Markdown（4 个二级标题，可直接 KaTeX 渲染）
支持流式 (async generator) 和非流式两种接口。
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from core.llm import chat, stream_chat, lang_sys_suffix
from skills.prerequisite_map import prerequisite_map
from skills.search_theorems import search_theorems, format_theorems_for_prompt
from skills.mactutor_search import get_mactutor_context, ATTRIBUTION


# ── System Prompts ────────────────────────────────────────────────────────────

_HISTORY_SYSTEM = """You are a mathematics historian and educator with deep knowledge of the history of mathematics.
Given a mathematical statement or theorem, provide a substantive, engaging account of its background and history.

You will receive archival source material from the MacTutor History of Mathematics Archive (St Andrews).
Use this material as your factual backbone: reference specific mathematicians, dates, controversies,
and interesting stories found in the source. If the source contains a surprising anecdote, priority dispute,
or unexpected historical development — include it. Make the history vivid and intellectually alive.

Your response should cover:
1. **Origin & Motivation** — who first stated or proved it, in what context, what problem it solved,
   and what mathematical landscape it emerged from
2. **Mathematical Significance** — why this result matters; what it unlocks, what it connects,
   what it changed in mathematics
3. **Key Ideas in Historical Development** — major milestones, failed approaches, priority disputes,
   or surprising turns that reveal the human side of mathematics
4. **Modern Perspective** — how the result fits into the contemporary landscape

Tone: rigorous yet intellectually engaging. Write for PhD students who appreciate both precision and
the human story behind mathematics. Use specific names, dates, and incidents from the source material.
Use LaTeX for all formulas ($...$ inline, $$...$$ display).
Length: 400–650 words. No bullet-list summaries — write in flowing, engaging prose.
Always finish the final sentence completely before stopping.

If source material is provided below, integrate its specific facts naturally into your narrative.

IMPORTANT: Do NOT start with "## 数学背景" or any "## " heading. Output body text directly.
IMPORTANT: Do NOT include any preamble or meta-commentary. Start immediately with the actual content.
"""

_ELABORATION_SYSTEM = """You are a mathematics educator writing a complete, pedagogically rigorous exposition.
Audience: advanced undergraduates or graduate students.

Write a complete proof and conceptual explanation of the given statement. For each step:
- State clearly WHAT you are doing (the mathematical move)
- Explain WHY this step is valid or necessary (the intuition or theorem used)
- Use LaTeX for all formulas: $...$ for inline math, $$...$$ for display math (never use \\[ or \\])

Structure:
1. Begin with a brief strategy overview (1–2 sentences)
2. Number each step: **Step N** — [what] — *because* [why]
3. End with a clear ∎ marker and a one-line reflection on the key idea

If the statement requires multiple cases, handle each case with a clearly labeled sub-section.
Length: 400–700 words. Do NOT start with "## 完整证明" or any ## heading.
Do NOT include preamble. Start immediately with the strategy sentence.
"""

_EXAMPLES_SYSTEM = """You are a mathematician providing non-trivial concrete examples for a theorem.
Audience: advanced undergraduates to researchers in mathematics.

Provide 2–3 concrete examples that together:
- Demonstrate the theorem in a specific, worked-out case (at least one)
- Illuminate a boundary case or show why a hypothesis is necessary (at least one)
- If possible, show the theorem failing when a condition is dropped

For each example:
- State clearly what the example is and why it is relevant
- Work it out in enough detail to be instructive
- Include boundary case analysis where relevant
- Use LaTeX for all mathematics: $...$ inline, $$...$$ display (never \\[ or \\])
- End with a citation line: > *参见：[Author, Title, §X.X]* referencing a standard textbook or paper
  (e.g., Rudin, Dummit & Foote, Lang, Hartshorne, Atiyah–Macdonald)

Format: use "### Example 1: [descriptive title]", "### Example 2: [descriptive title]", etc.
Do NOT start with "## 具体例子" or any ## heading.
Do NOT include any preamble. Start immediately with "### Example 1:".
Each example body: 100–200 words. Total output: 400–700 words.
Complete every sentence and formula — never stop mid-expression.
"""


@dataclass
class LearningOutput:
    """学习模式的完整输出。"""
    statement: str
    level: str
    markdown: str

    def to_markdown(self) -> str:
        return self.markdown

    def has_required_sections(self) -> bool:
        required = ["## 前置知识", "## 完整证明", "## 具体例子"]
        return all(r in self.markdown for r in required)


async def run_learning_pipeline(
    statement: str,
    *,
    level: str = "undergraduate",
    model: Optional[str] = None,
    include_prereqs: bool = True,
    lang: Optional[str] = None,
) -> LearningOutput:
    """非流式包装：收集 stream_learning_pipeline 的所有输出，返回 LearningOutput。"""
    chunks: list[str] = []
    async for chunk in stream_learning_pipeline(
        statement,
        level=level,
        model=model,
        lang=lang,
    ):
        if not chunk.startswith("<!--vp-"):
            chunks.append(chunk)
    return LearningOutput(
        statement=statement,
        level=level,
        markdown="".join(chunks),
    )


def _strip_leading_heading(text: str, heading: str) -> str:
    """剥掉 LLM 输出最前面的 ## 标题，避免与 pipeline 加的标题重复。"""
    if not text:
        return text
    lines = text.lstrip().splitlines()
    drop = 0
    for i, line in enumerate(lines[:3]):
        s = line.strip()
        if not s:
            drop = i + 1
            continue
        if s.startswith("##") and (
            heading.lstrip("# ").lower() in s.lower()
            or s.lower().startswith("## 证明")
            or s.lower().startswith("## 完整证明")
            or s.lower().startswith("## 例子")
            or s.lower().startswith("## 具体例子")
            or s.lower().startswith("## 延伸阅读")
            or s.lower().startswith("## 数学背景")
            or s.lower().startswith("## 前置知识")
            or s.lower().startswith("## proof")
            or s.lower().startswith("## elaboration")
            or s.lower().startswith("## examples")
            or s.lower().startswith("## background")
        ):
            drop = i + 1
        else:
            break
    return "\n".join(lines[drop:])


import re as _re


def _fix_broken_dollar(text: str) -> str:
    """修复 LLM 在数字或小数点旁边错误插入 $ 的问题，以及把整句话包进 $...$ 的问题。"""
    if not text or '$' not in text:
        return text
    text = _re.sub(r'(\d)\$\.(\d)', r'\1.\2', text)
    text = _re.sub(r'(\d)\$([^$\w])', r'\1\2', text)
    text = _re.sub(r'(\d)\$(\d)', r'\1.\2', text)
    text = _re.sub(r'([A-Za-z])\$(\d)', r'\1 \2', text)
    def _strip_orphan(m):
        inner = m.group(1)
        # 超过 60 字符且含空格的 $...$ 几乎必然是误包的句子
        if len(inner) > 60 and ' ' in inner:
            return inner
        if _re.match(r'^[\d\s.,;:]+$', inner):
            return inner
        return m.group(0)
    text = _re.sub(r'\$([^$\n]{1,300})\$', _strip_orphan, text)
    return text


_LANG_INSTRUCTION = {
    "zh": "\n\nIMPORTANT: The user wrote in Chinese. You MUST respond entirely in Chinese (简体中文). All explanations, prose, and section titles must be in Chinese. Keep LaTeX formulas as-is.",
    "en": "",
}

def _lang_suffix(lang: Optional[str]) -> str:
    if lang == "zh":
        return _LANG_INSTRUCTION["zh"]
    return ""


def _status_frame(step: str, message: str) -> str:
    return f"<!--vp-status:{step}|{message}-->"


async def stream_learning_pipeline(
    statement: str,
    *,
    level: str = "undergraduate",
    model: Optional[str] = None,
    kb_context: Optional[str] = None,
    lang: Optional[str] = None,
) -> AsyncIterator[str]:
    """流式版本：按节顺序输出 Markdown，供 SSE 使用。

    顺序：数学背景 → 前置知识 → 完整证明 → 具体例子
    每个板块均附来源归因；非流式节在后台并行生成。
    """
    _ls = lang_sys_suffix(lang)
    _kb_prefix = (kb_context + "\n\n") if kb_context else ""

    # ── 后台并行启动非流式任务 ────────────────────────────────────────────────
    mactutor_task = asyncio.create_task(
        get_mactutor_context(statement, max_chars=2500)
    )
    prereq_task = asyncio.create_task(
        prerequisite_map(statement, level=level, enrich_with_search=True, model=model)
    )

    # ── Card 1: 数学背景（流式；等待 MacTutor 史料后开始） ───────────────────
    yield _status_frame("background", "正在检索数学史料，梳理历史脉络…")
    yield "## 数学背景\n\n"
    source_url_for_card = ""
    try:
        mactutor_text, source_url = await mactutor_task
        source_url_for_card = source_url or ""

        history_user_msg = _kb_prefix
        if mactutor_text:
            history_user_msg += f"[MacTutor Archive source material]\n{mactutor_text}\n\n"
        history_user_msg += f"Mathematical statement:\n\n{statement}"
        history_sys = _HISTORY_SYSTEM + _ls

        # 流式输出背景叙述
        pending = ""
        leading_stripped = False
        async for chunk in stream_chat(history_user_msg, system=history_sys, model=model, max_tokens=3000):
            pending += chunk
            if not leading_stripped and (len(pending) > 80 or '\n\n' in pending):
                pending = _strip_leading_heading(pending, "## 数学背景").lstrip('\n')
                leading_stripped = True
            yield pending
            pending = ""
        if pending:
            if not leading_stripped:
                pending = _strip_leading_heading(pending, "## 数学背景").lstrip('\n')
            yield pending

        # 来源归因
        if source_url_for_card:
            yield f"\n\n> 来源：[MacTutor History of Mathematics, University of St Andrews]({source_url_for_card})\n"
        elif mactutor_text:
            yield f"\n\n> 来源：MacTutor History of Mathematics, University of St Andrews\n"
        else:
            yield "\n\n> 来源：数学历史文献综合（MacTutor 检索不可用）\n"
    except Exception as e:
        yield f"_背景生成失败：{type(e).__name__}: {e}_\n"
    yield "\n\n"

    # ── Card 2: 前置知识 ──────────────────────────────────────────────────────
    yield _status_frame("prereq", "正在整理前置知识…")
    yield "## 前置知识\n\n"
    try:
        pmap = await prereq_task
        if pmap and pmap.prerequisites:
            type_labels = {"definition": "定义", "theorem": "定理", "technique": "技术"}
            matched_items: list[tuple[str, str]] = []
            for p in pmap.prerequisites:
                concept = _fix_broken_dollar(p.concept)
                desc = _fix_broken_dollar(p.description)
                label = type_labels.get(p.type, p.type)
                yield f"- **{concept}** *({label})* — {desc}\n"
                if p.theorem_matches:
                    top = p.theorem_matches[0]
                    if getattr(top, "similarity", 0) >= 0.6 and top.name and top.link:
                        matched_items.append((top.name, top.link))
            yield "\n"

            if pmap.learning_path:
                yield "**学习路径**\n\n"
                for i, step in enumerate(pmap.learning_path, 1):
                    yield f"{i}. {step}\n"
                yield "\n"

            if matched_items:
                refs = " · ".join(f"[{n}]({l})" for n, l in matched_items[:3])
                yield f"> 相关定理：{refs}\n"
        else:
            yield "_本命题无显式前置依赖。_\n"
    except Exception as e:
        yield f"_前置知识分析失败（{type(e).__name__}: {e}）。_\n"
    yield "\n\n"

    # ── Card 3: 完整证明（流式） ──────────────────────────────────────────────
    yield _status_frame("proof", "正在生成完整证明…")
    yield "## 完整证明\n\n"
    try:
        elab_user_msg = _kb_prefix + f"Write a complete proof and explanation for:\n\n{statement}"
        elab_sys = _ELABORATION_SYSTEM + _ls
        pending = ""
        leading_stripped = False
        async for chunk in stream_chat(elab_user_msg, system=elab_sys, model=model, max_tokens=3000):
            pending += chunk
            if not leading_stripped and (len(pending) > 80 or '\n\n' in pending):
                pending = _strip_leading_heading(pending, "## 完整证明").lstrip('\n')
                leading_stripped = True
            yield pending
            pending = ""
        if pending:
            if not leading_stripped:
                pending = _strip_leading_heading(pending, "## 完整证明").lstrip('\n')
            yield pending
    except Exception as e:
        yield f"_阐释生成失败：{type(e).__name__}: {e}_\n"
    yield "\n\n"

    # ── Card 4: 具体例子（流式，避免截断） ────────────────────────────────────
    yield _status_frame("examples", "正在整理具体例子…")
    yield "## 具体例子\n\n"
    try:
        examples_user_msg = _kb_prefix + f"Provide concrete examples for:\n\n{statement}"
        examples_sys = _EXAMPLES_SYSTEM + _ls
        pending = ""
        leading_stripped = False
        async for chunk in stream_chat(examples_user_msg, system=examples_sys, model=model, max_tokens=4000):
            pending += chunk
            if not leading_stripped and (len(pending) > 80 or '\n\n' in pending):
                pending = _strip_leading_heading(pending, "## 具体例子").lstrip('\n')
                leading_stripped = True
            yield pending
            pending = ""
        if pending:
            if not leading_stripped:
                pending = _strip_leading_heading(pending, "## 具体例子").lstrip('\n')
            yield pending
    except Exception as e:
        yield f"_例子生成失败：{type(e).__name__}: {e}_\n"
    yield "\n"

    yield _status_frame("done", "完成")
