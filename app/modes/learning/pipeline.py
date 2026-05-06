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
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from core.llm import stream_chat, lang_sys_suffix
from skills.prerequisite_map import prerequisite_map
from skills.mactutor_search import get_mactutor_context

# ── 可调度的 section id（与前端 data-section、SSE step 对齐）──────────────────

SECTION_IDS = frozenset({"background", "prereq", "proof", "examples"})


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


_STRIP_HEADING_KEYWORDS: frozenset[str] = frozenset({
    "## 证明", "## 完整证明", "## 例子", "## 具体例子", "## 延伸阅读",
    "## 数学背景", "## 前置知识",
    "## proof", "## elaboration", "## examples", "## background",
})


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
            or any(s.lower().startswith(kw) for kw in _STRIP_HEADING_KEYWORDS)
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


def _status_frame(step: str, message: str) -> str:
    # 清理特殊字符避免截断HTML注释帧
    safe_message = str(message).replace('>', ' ').replace('-->', ' ').replace('\n', ' ') if message else message
    return f"<!--vp-status:{step}|{safe_message}-->"


async def _stream_stripped(
    user_msg: str,
    system: str,
    model: Optional[str],
    max_tokens: int,
    heading: str,
) -> AsyncIterator[str]:
    """流式调用 LLM，并剥掉开头的重复 ## 标题行。

    改进：积累 pending 直到足够判断标题，避免跨 chunk 边界时标题剥离失效。
    """
    pending = ""
    leading_stripped = False
    async for chunk in stream_chat(user_msg, system=system, model=model, max_tokens=max_tokens):
        pending += chunk
        if not leading_stripped:
            # 等到缓冲区足够（>80字符 或 出现段落分隔 \n\n）再做标题剥离
            if len(pending) > 80 or '\n\n' in pending:
                pending = _strip_leading_heading(pending, heading).lstrip('\n')
                leading_stripped = True
                yield pending
                pending = ""
            # 不够时继续积累，不 yield
        else:
            yield pending
            pending = ""
    if pending:
        if not leading_stripped:
            pending = _strip_leading_heading(pending, heading).lstrip('\n')
        yield pending


def _section_error_frame(section_id: str, message: str) -> str:
    """结构化单卡错误，供 SSE 转成 section_error JSON。"""
    safe = str(message).replace("-->", " ").replace("\n", " ").strip()
    return f"<!--vp-section-error:{section_id}|{safe}-->"


async def stream_card_background(
    statement: str,
    mactutor_task: asyncio.Task,
    *,
    kb_context: Optional[str],
    lang: Optional[str],
    model: Optional[str],
) -> AsyncIterator[str]:
    _ls = lang_sys_suffix(lang)
    _kb_prefix = (kb_context + "\n\n") if kb_context else ""

    # 根据语言选择标题
    title = "## Background\n\n" if lang == "en" else "## 数学背景\n\n"
    status_msg = "Retrieving mathematical history..." if lang == "en" else "正在检索数学史料，梳理历史脉络…"
    heading_for_strip = "## Background" if lang == "en" else "## 数学背景"

    yield _status_frame("background", status_msg)
    yield title
    source_url_for_card = ""
    try:
        mactutor_text, source_url = await mactutor_task
        source_url_for_card = source_url or ""

        history_user_msg = _kb_prefix
        if mactutor_text:
            history_user_msg += f"[MacTutor Archive source material]\n{mactutor_text}\n\n"
        history_user_msg += f"Mathematical statement:\n\n{statement}"
        history_sys = _HISTORY_SYSTEM + _ls

        async for chunk in _stream_stripped(history_user_msg, history_sys, model, 3000, heading_for_strip):
            yield chunk

        if source_url_for_card:
            yield f"\n\n> 来源：[MacTutor History of Mathematics, University of St Andrews]({source_url_for_card})\n"
        elif mactutor_text:
            yield f"\n\n> 来源：MacTutor History of Mathematics, University of St Andrews\n"
        else:
            # MacTutor检索未找到相关内容时，LLM基于自身知识生成
            yield "\n\n> 来源：数学史文献综合\n"
    except Exception as e:
        yield _section_error_frame("background", f"{type(e).__name__}: {e}")
        yield f"_背景生成失败：{type(e).__name__}: {e}_\n"
    yield "\n\n"


async def stream_card_prereq(
    statement: str,
    prereq_task: asyncio.Task,
    *,
    level: str,
    model: Optional[str],
    lang: Optional[str] = None,
) -> AsyncIterator[str]:
    # 根据语言选择标题和标签
    title = "## Prerequisites\n\n" if lang == "en" else "## 前置知识\n\n"
    status_msg = "Organizing prerequisites..." if lang == "en" else "正在整理前置知识…"
    type_labels_en = {"definition": "Definition", "theorem": "Theorem", "technique": "Technique"}
    type_labels_zh = {"definition": "定义", "theorem": "定理", "technique": "技术"}
    type_labels = type_labels_en if lang == "en" else type_labels_zh
    no_prereq_msg = "_No explicit prerequisites for this statement._\n" if lang == "en" else "_本命题无显式前置依赖。_\n"
    learning_path_title = "**Learning Path**\n\n" if lang == "en" else "**学习路径**\n\n"
    related_theorems_prefix = "Related theorems: " if lang == "en" else "相关定理："

    yield _status_frame("prereq", status_msg)
    yield title
    try:
        pmap = await prereq_task
        if pmap and pmap.prerequisites:
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
                yield learning_path_title
                for i, step in enumerate(pmap.learning_path, 1):
                    yield f"{i}. {step}\n"
                yield "\n"

            if matched_items:
                refs = " · ".join(f"[{n}]({l})" for n, l in matched_items[:3])
                yield f"> {related_theorems_prefix}{refs}\n"
        else:
            yield no_prereq_msg
    except Exception as e:
        yield _section_error_frame("prereq", f"{type(e).__name__}: {e}")
        error_msg = f"_Prerequisite analysis failed ({type(e).__name__}: {e})._\n" if lang == "en" else f"_前置知识分析失败（{type(e).__name__}: {e}）。_\n"
        yield error_msg
    yield "\n\n"


async def stream_card_proof(
    statement: str,
    *,
    kb_context: Optional[str],
    lang: Optional[str],
    model: Optional[str],
) -> AsyncIterator[str]:
    _ls = lang_sys_suffix(lang)
    _kb_prefix = (kb_context + "\n\n") if kb_context else ""

    # 根据语言选择标题
    title = "## Complete Proof\n\n" if lang == "en" else "## 完整证明\n\n"
    status_msg = "Generating complete proof..." if lang == "en" else "正在生成完整证明…"
    heading_for_strip = "## Complete Proof" if lang == "en" else "## 完整证明"

    yield _status_frame("proof", status_msg)
    yield title
    try:
        elab_user_msg = _kb_prefix + f"Write a complete proof and explanation for:\n\n{statement}"
        elab_sys = _ELABORATION_SYSTEM + _ls

        # 添加日志：调试proof生成
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[PROOF] Starting generation for: {statement[:50]}...")
        logger.info(f"[PROOF] Model: {model}, max_tokens: 3000")

        chunk_count = 0
        total_chars = 0
        async for chunk in _stream_stripped(elab_user_msg, elab_sys, model, 3000, heading_for_strip):
            chunk_count += 1
            total_chars += len(chunk)
            yield chunk

        logger.info(f"[PROOF] Completed: {chunk_count} chunks, {total_chars} chars total")
    except Exception as e:
        logger.exception(f"[PROOF] Exception: {e}")
        yield _section_error_frame("proof", f"{type(e).__name__}: {e}")
        error_msg = f"_Proof generation failed: {type(e).__name__}: {e}_\n" if lang == "en" else f"_阐释生成失败：{type(e).__name__}: {e}_\n"
        yield error_msg
    yield "\n\n"


async def stream_card_examples(
    statement: str,
    *,
    kb_context: Optional[str],
    lang: Optional[str],
    model: Optional[str],
) -> AsyncIterator[str]:
    _ls = lang_sys_suffix(lang)
    _kb_prefix = (kb_context + "\n\n") if kb_context else ""

    # 根据语言选择标题
    title = "## Examples\n\n" if lang == "en" else "## 具体例子\n\n"
    status_msg = "Organizing examples..." if lang == "en" else "正在整理具体例子…"
    heading_for_strip = "## Examples" if lang == "en" else "## 具体例子"

    yield _status_frame("examples", status_msg)
    yield title
    try:
        examples_user_msg = _kb_prefix + f"Provide concrete examples for:\n\n{statement}"
        examples_sys = _EXAMPLES_SYSTEM + _ls
        async for chunk in _stream_stripped(examples_user_msg, examples_sys, model, 4000, heading_for_strip):
            yield chunk
    except Exception as e:
        yield _section_error_frame("examples", f"{type(e).__name__}: {e}")
        error_msg = f"_Example generation failed: {type(e).__name__}: {e}_\n" if lang == "en" else f"_例子生成失败：{type(e).__name__}: {e}_\n"
        yield error_msg
    yield "\n"


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
    mactutor_task = asyncio.create_task(
        get_mactutor_context(statement, max_chars=2500)
    )
    prereq_task = asyncio.create_task(
        prerequisite_map(statement, level=level, enrich_with_search=True, model=model, lang=lang)
    )

    async for chunk in stream_card_background(
        statement, mactutor_task, kb_context=kb_context, lang=lang, model=model
    ):
        yield chunk

    async for chunk in stream_card_prereq(statement, prereq_task, level=level, model=model, lang=lang):
        yield chunk

    async for chunk in stream_card_proof(statement, kb_context=kb_context, lang=lang, model=model):
        yield chunk

    async for chunk in stream_card_examples(statement, kb_context=kb_context, lang=lang, model=model):
        yield chunk

    yield _status_frame("done", "完成")


async def stream_learning_section(
    section: str,
    statement: str,
    *,
    level: str = "undergraduate",
    model: Optional[str] = None,
    kb_context: Optional[str] = None,
    lang: Optional[str] = None,
) -> AsyncIterator[str]:
    """仅生成单卡（用于 /learn/section 重试）。"""
    sid = section.strip().lower()
    if sid not in SECTION_IDS:
        raise ValueError(f"invalid section: {section}")

    if sid == "background":
        task = asyncio.create_task(get_mactutor_context(statement, max_chars=2500))
        async for c in stream_card_background(
            statement, task, kb_context=kb_context, lang=lang, model=model
        ):
            yield c
        return

    if sid == "prereq":
        task = asyncio.create_task(
            prerequisite_map(statement, level=level, enrich_with_search=True, model=model, lang=lang)
        )
        async for c in stream_card_prereq(statement, task, level=level, model=model, lang=lang):
            yield c
        return

    if sid == "proof":
        async for c in stream_card_proof(statement, kb_context=kb_context, lang=lang, model=model):
            yield c
        return

    # examples
    async for c in stream_card_examples(statement, kb_context=kb_context, lang=lang, model=model):
        yield c
