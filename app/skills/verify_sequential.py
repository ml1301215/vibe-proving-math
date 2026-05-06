"""技能：verify_sequential —— 逐步验证证明文本中每个推理步骤的逻辑正确性。

参考：Rethlas `verify-sequential-statements/SKILL.md`
核心设计（来自 Aletheia）：Verifier 与 Generator 严格解耦，
不共享生成器的思维链，独立判断每个步骤。

TheoremSearch 集成：验证器在判断前先通过 TheoremSearch API
核查证明中引用的每条定理/引理，将检索结果注入 prompt，
使验证器能基于真实数据库证据做出判断（防幻觉引用）。

输入：
    proof_text   证明文本（自然语言或半形式化）
    statement    原始命题（验证器需要知道目标）

输出：
    VerificationResult:
        steps         (list[StepVerdict])  每步的判定结果
        overall       (str)   "passed" | "has_gaps" | "critical_error"
        summary       (str)   验证总结
        fatal_step    (int|None)  第一个 critical_error 步骤编号（若有）
        theorem_search_context (str)  TheoremSearch 查询摘要
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from core.llm import chat_json

logger = logging.getLogger(__name__)

# 超长 proof 文本截断阈值（约 1500 tokens）
_MAX_PROOF_CHARS = 6000

# TheoremSearch 查询：每个引用最多等待多少秒
_SEARCH_TIMEOUT = 3.0  # 优化: 从8秒降到3秒,减少验证等待时间

# 最多查多少条引用（控制延迟）
_MAX_REFS_TO_SEARCH = 4  # 优化: 从6个降到4个,加快验证速度

_LATEX_STYLE_INSTRUCTION = (
    "When you mention any mathematical object, variable, formula, set, map, inequality, congruence, "
    "norm, cardinality, or symbolic relation in summary/reason/text fields, wrap the mathematical part "
    "in inline LaTeX using `$...$`. "
    "Examples: `$G$`, `$H \\le G$`, `$|H| \\mid |G|$`, `$g \\in G$`, `$a^{{p-1}} \\equiv 1 \\pmod p$`. "
    "Do not emit bare Unicode math such as `∈`, `≤`, `⊂`, `|G|`, `a_n`, `f: X \\to Y` outside `$...$`. "
    "Use plain natural language outside math delimiters, and do not use Markdown formatting besides LaTeX math."
)

# ── 提取引用的正则 ───────────────────────────────────────────────────────────
_REF_PATTERNS = [
    # "by the Mean Value Theorem" / "By Cauchy-Schwarz Inequality"
    re.compile(
        r"\bby\s+(?:the\s+)?([A-Z][a-zA-Zéè\-]+(?: [A-Z][a-zA-Zéè\-]+)*"
        r"\s+(?:Theorem|Lemma|Inequality|Corollary|Proposition|Formula|Criterion|Principle))\b",
        re.IGNORECASE,
    ),
    # "applying Zorn's Lemma" / "using the Hahn-Banach theorem"
    re.compile(
        r"\b(?:applying|using|from|via)\s+(?:the\s+)?([A-Z][a-zA-Zéè\-'s]+(?: [A-Z][a-zA-Zéè\-'s]+)*"
        r"\s+(?:Theorem|Lemma|Inequality|Corollary|Proposition|Formula|Criterion|Principle))\b",
        re.IGNORECASE,
    ),
    # "the Fundamental Theorem of Calculus"
    re.compile(
        r"\b(?:the\s+)([A-Z][a-zA-Zéè\-]+(?: [A-Z][a-zA-Zéè\-]+)*"
        r"\s+Theorem\s+of\s+[A-Z][a-zA-Z]+)\b",
        re.IGNORECASE,
    ),
]


def _extract_cited_theorems(proof_text: str) -> list[str]:
    """从证明文本中提取明确引用的定理/引理名称（去重，最多 _MAX_REFS_TO_SEARCH 条）。"""
    found: list[str] = []
    seen: set[str] = set()
    for pat in _REF_PATTERNS:
        for m in pat.finditer(proof_text):
            name = m.group(1).strip()
            key = name.lower()
            if key not in seen and len(name) > 4:
                seen.add(key)
                found.append(name)
    return found[:_MAX_REFS_TO_SEARCH]


async def _search_one(name: str) -> dict:
    """查询单个定理名，返回结构化结果（超时则返回 error）。"""
    try:
        from skills.search_theorems import search_theorems
        results = await asyncio.wait_for(
            search_theorems(name, top_k=3, min_sim=0.3),
            timeout=_SEARCH_TIMEOUT,
        )
        if results and results[0].similarity >= 0.55:
            top = results[0]
            return {
                "cited": name,
                "status": "found",
                "matched_name": top.name,
                "similarity": round(top.similarity, 3),
                "slogan": top.slogan[:200] if top.slogan else top.body[:200],
                "link": top.link or "",
            }
        sim = results[0].similarity if results else 0.0
        closest = results[0].name if results else "—"
        return {
            "cited": name,
            "status": "not_found",
            "matched_name": closest,
            "similarity": round(sim, 3),
            "slogan": "",
            "link": "",
        }
    except asyncio.TimeoutError:
        return {"cited": name, "status": "timeout", "matched_name": "", "similarity": 0.0, "slogan": "", "link": ""}
    except Exception as e:
        logger.debug("TheoremSearch lookup failed for %r: %s: %s", name, type(e).__name__, e)
        return {"cited": name, "status": f"error: {type(e).__name__}", "matched_name": "", "similarity": 0.0, "slogan": "", "link": ""}


async def _build_theorem_search_context(proof_text: str) -> tuple[str, list[dict]]:
    """提取引用 → 并行 TheoremSearch → 返回 (prompt_section, raw_results)。"""
    cited = _extract_cited_theorems(proof_text)
    if not cited:
        return "", []

    raw = await asyncio.gather(*[_search_one(name) for name in cited])
    results = list(raw)

    lines = ["【TheoremSearch 核查结果（来自真实数学定理数据库）】"]
    for r in results:
        status_icon = "✓" if r["status"] == "found" else "✗"
        sim_str = f"{r['similarity']:.0%}" if r["similarity"] else "N/A"
        if r["status"] == "found":
            lines.append(
                f"  {status_icon} 引用「{r['cited']}」→ 数据库匹配「{r['matched_name']}」"
                f"（相似度 {sim_str}）: {r['slogan']}"
                + (f"\n    来源: {r['link']}" if r["link"] else "")
            )
        else:
            lines.append(
                f"  {status_icon} 引用「{r['cited']}」→ 未在数据库找到可信匹配"
                f"（最近匹配「{r['matched_name']}」相似度 {sim_str}）"
            )

    context = "\n".join(lines)
    return context, results


_VERIFY_SYSTEM = """You are an independent mathematical proof verifier with access to a real theorem database (TheoremSearch, 10M+ theorems in Lean 4 / Mathlib).

You have NOT seen how the proof was generated. Your job is to verify each logical step rigorously AND check whether the proof actually concludes the target statement.

## Your verification process for each step:
1. Check if it follows logically from previous steps and stated assumptions
2. If the step cites a theorem/lemma: check the TheoremSearch results provided — if the theorem is NOT FOUND in the database, mark as critical_error
3. If the cited theorem IS found but is applied incorrectly (wrong hypotheses, wrong domain), mark as critical_error
4. If the step makes an unjustified leap without citing a theorem, mark as gap
5. If everything is correct and well-cited, mark as passed

## Goal completeness check (CRITICAL):
After verifying all steps, check whether the proof actually reaches and proves the target statement.
- goal_reached = true ONLY if the final step(s) logically conclude exactly what was asked to be proved
- If the proof only handles special cases, partial results, or drifts off-target, set goal_reached = false
- If the proof concludes something *stronger or weaker* than the target, set goal_reached = false
- If the proof is merely a computation or reformulation without a final logical conclusion, set goal_reached = false

## TheoremSearch context usage:
- "✓ found" with high similarity (>70%): the theorem exists and can be used — verify it's applied correctly
- "✗ not_found" or low similarity: treat the citation as UNVERIFIED — if the step's validity depends on this theorem, mark as critical_error
- "timeout/error": treat conservatively — mark as gap if the step relies on it

## Verdict options:
- "passed": logically valid, well-justified, and any cited theorems are verified to exist and apply
- "gap": the step is plausible but missing justification, or a minor citation issue
- "critical_error": the step is logically wrong, uses a non-existent theorem as a load-bearing reference, or makes an invalid logical leap

## Output style for mathematical expressions:
""" + _LATEX_STYLE_INSTRUCTION + """

Output MUST be valid JSON with this schema:
{
    "overall": "has_gaps",  // "passed" | "has_gaps" | "critical_error"
    "goal_reached": false,  // true ONLY if the proof fully concludes the target statement
    "goal_reached_reason": "The proof reformulates Phi_n but never establishes the inequality.",
    "summary": "The proof is mostly correct, but Step 3 does not justify why `$gH = H$` implies `$g \\in H$`.",
    "steps": [
        {
            "step_num": 1,
            "text": "First, we note that $G$ is abelian...",
            "verdict": "passed",
            "reason": "This follows directly from the definition of `$G$` given in the statement.",
            "cited_theorem": null
        },
        {
            "step_num": 2,
            "text": "By the Fundamental Theorem of Algebra, ...",
            "verdict": "critical_error",
            "reason": "TheoremSearch could not verify the cited theorem with sufficient confidence, so the inference that `$p(x)$` splits over `$\\mathbb{C}$` is unsupported.",
            "cited_theorem": "Fundamental Theorem of Algebra"
        }
    ]
}
"""

_VERIFY_USER_TEMPLATE = """Original statement to prove:
{statement}

Section title:
{section_title}

{theorem_context}

Local definitional context:
{local_definitions}

Local citation hints:
{local_citations}

Nearby paper context:
{context_text}

Proof to verify:
{proof_text}

Verify each logical step independently, using the TheoremSearch results above to check citation validity.

For every JSON string field that mentions mathematics, follow this style rule exactly:
""" + _LATEX_STYLE_INSTRUCTION + """

Output JSON only."""


_VERIFY_SCHEMA = {
    "overall": "has_gaps",
    "goal_reached": False,
    "goal_reached_reason": "Explain whether the proof concludes the target statement",
    "summary": "Short verification summary",
    "steps": [
        {
            "step_num": 1,
            "text": "Proof step text",
            "verdict": "passed",
            "reason": "Why this step is valid or problematic",
            "cited_theorem": None,
        }
    ],
}


@dataclass
class StepVerdict:
    step_num: int
    text: str
    verdict: str  # "passed" | "gap" | "critical_error"
    reason: str
    cited_theorem: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "text": self.text,
            "verdict": self.verdict,
            "reason": self.reason,
            "cited_theorem": self.cited_theorem,
        }


@dataclass
class VerificationResult:
    steps: list[StepVerdict]
    overall: str  # "passed" | "has_gaps" | "critical_error"
    summary: str = ""
    fatal_step: Optional[int] = None
    theorem_search_results: list[dict] = field(default_factory=list)
    goal_reached: bool = True   # 证明是否真正完成了目标命题
    goal_reached_reason: str = ""

    def has_errors(self) -> bool:
        # 步骤有错误，或目标未达成，均视为验证未通过
        return self.overall in ("has_gaps", "critical_error") or not self.goal_reached

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "goal_reached": self.goal_reached,
            "goal_reached_reason": self.goal_reached_reason,
            "summary": self.summary,
            "fatal_step": self.fatal_step,
            "steps": [s.to_dict() for s in self.steps],
            "theorem_search_results": self.theorem_search_results,
        }


async def verify_sequential(
    proof_text: str,
    statement: str,
    *,
    model: Optional[str] = None,
    context_text: str = "",
    section_title: str = "",
    local_citations: Optional[list[str]] = None,
    local_definitions: Optional[list[str]] = None,
) -> VerificationResult:
    """逐步验证证明，先用 TheoremSearch 核查引用，再交 LLM 验证每步。

    超长 proof 文本会被安全截断（保留前 60% + 后 30%），防止 token 超限。
    """
    # 超长证明截断
    if len(proof_text) > _MAX_PROOF_CHARS:
        head = int(_MAX_PROOF_CHARS * 0.6)
        tail = int(_MAX_PROOF_CHARS * 0.3)
        omitted = len(proof_text) - head - tail
        proof_text = (
            proof_text[:head]
            + f"\n\n[... {omitted} chars truncated for token budget ...]\n\n"
            + proof_text[-tail:]
        )
        logger.debug("verify_sequential: proof truncated (%d chars omitted)", omitted)

    # TheoremSearch 核查（并行，不阻塞主流程）
    theorem_context, search_results = await _build_theorem_search_context(proof_text)
    if search_results:
        logger.info(
            "verify_sequential: TheoremSearch found %d/%d cited theorems",
            sum(1 for r in search_results if r["status"] == "found"),
            len(search_results),
        )

    user_msg = _VERIFY_USER_TEMPLATE.format(
        statement=statement,
        section_title=section_title or "N/A",
        theorem_context=theorem_context or "（未检测到明确引用的定理名称，请自行根据数学常识判断引用合理性）",
        local_definitions="\n".join(f"- {x}" for x in (local_definitions or [])[:5]) or "（无显式定义上下文）",
        local_citations="\n".join(f"- {x}" for x in (local_citations or [])[:8]) or "（无额外局部引用提示）",
        context_text=context_text[:2500] if context_text else "（无额外上下文）",
        proof_text=proof_text,
    )

    try:
        raw = await chat_json(user_msg, system=_VERIFY_SYSTEM, model=model, schema=_VERIFY_SCHEMA)
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            data = {}  # chat_json 返回非 dict（如 list/None）时，安全降级为空字典
    except Exception as exc:
        logger.warning("verify_sequential LLM call failed: %s", exc)
        return VerificationResult(
            steps=[],
            overall="critical_error",
            summary=f"验证器调用失败: {exc}",
            theorem_search_results=search_results,
        )

    steps = []
    fatal = None
    _MAX_STEPS = 100  # 防止 LLM 返回极长步骤列表导致内存/性能问题
    for s in (data.get("steps") or [])[:_MAX_STEPS]:
        if not isinstance(s, dict):
            continue  # 跳过 null 或非 dict 元素，防止 AttributeError
        verdict = s.get("verdict", "gap")
        _raw_step_num = s.get("step_num", len(steps) + 1)
        try:
            step_num = int(_raw_step_num)
        except (ValueError, TypeError):
            step_num = len(steps) + 1  # 非整数类型安全降级
        sv = StepVerdict(
            step_num=step_num,
            text=s.get("text", ""),
            verdict=verdict,
            reason=s.get("reason", ""),
            cited_theorem=s.get("cited_theorem"),
        )
        steps.append(sv)
        if verdict == "critical_error" and fatal is None:
            fatal = step_num

    if proof_text.strip() and not steps:
        steps.append(StepVerdict(
            step_num=1,
            text=proof_text.strip()[:500],
            verdict="gap",
            reason="Verifier did not return a step-by-step trace, so this proof cannot be marked fully checked.",
            cited_theorem=None,
        ))
        data["overall"] = "has_gaps"
        data["summary"] = data.get("summary") or "No step-level verification trace was returned."
        data["goal_reached"] = False  # 无步骤跟踪时不能认为目标已达成

    goal_reached_raw = data.get("goal_reached", True)
    # 兼容布尔值和字符串 "false"/"true"（防止 LLM 返回字符串而非布尔）
    if isinstance(goal_reached_raw, bool):
        goal_reached = goal_reached_raw
    elif isinstance(goal_reached_raw, str):
        # 空字符串、"false"、"0"、"no" 均视为未达成
        goal_reached = bool(goal_reached_raw.strip()) and goal_reached_raw.strip().lower() not in ("false", "0", "no")
    else:
        goal_reached = bool(goal_reached_raw)
    goal_reached_reason = data.get("goal_reached_reason", "")
    # 若 goal_reached=False，且 overall 还是 passed，升级为 has_gaps
    overall = data.get("overall", "has_gaps")
    if not goal_reached and overall == "passed":
        overall = "has_gaps"

    return VerificationResult(
        steps=steps,
        overall=overall,
        summary=data.get("summary", ""),
        fatal_step=fatal,
        theorem_search_results=search_results,
        goal_reached=goal_reached,
        goal_reached_reason=goal_reached_reason,
    )
