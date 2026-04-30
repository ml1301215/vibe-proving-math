"""技能：direct_proving —— 直接尝试证明一个数学命题。

参考：Rethlas `direct-proving/SKILL.md`
实现：
  1. 用 TheoremSearch 检索相关引理（可选，提供上下文）
  2. 调用 LLM 生成完整证明尝试
  3. 返回 ProofResult（含置信度评估）

输出：
    ProofResult:
        proof      (str)    证明文本（可能不完整）
        confidence (float)  0.0-1.0，LLM 自评置信度
        status     (str)    "proved" | "partial" | "failed"
        gaps       (list)   证明中识别出的空洞/待验证步骤
        references (list)   使用的定理引用
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from core.llm import chat_json, chat, lang_sys_suffix
from skills.search_theorems import search_theorems, format_theorems_for_prompt, TheoremMatch


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _safe_list(v) -> list:
    """确保 v 是列表；若为字符串则包装为单元素列表；否则返回 []。"""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [v]
    return []

_DIRECT_PROVING_SYSTEM = """You are an expert mathematician and formal proof assistant.
Your task is to attempt a direct proof of the given mathematical statement.

Guidelines:
- Write a rigorous, complete, step-by-step mathematical proof
- Number each step explicitly: **Step 1.**, **Step 2.**, etc.
- Before each step, give one sentence explaining WHY this step is taken
- Cite specific theorems and lemmas you rely on (using the provided references if available)
- If you cannot complete the proof, clearly mark where you are stuck
- Be honest about your confidence level
- Do NOT fabricate theorem names or citations
- ALL mathematical expressions, variables, and equations MUST be wrapped in LaTeX
  delimiters: $...$ for inline (e.g. $a = 2p+1$, $\\mathbb{R}$, $f(x) \\to 0$),
  and $$...$$ for displayed equations. NEVER write plain-text math.
- In the JSON output, every backslash in a math expression must be doubled:
  write "\\\\frac{a}{b}" not "\\frac{a}{b}" in the JSON string.
- Aim for a COMPLETE proof (400-700 words). Quality and completeness over brevity.

Output MUST be valid JSON with this exact schema:
{
    "proof": "The complete proof text in mathematical notation...",
    "confidence": 0.85,
    "status": "proved",
    "gaps": ["Step 3 lacks justification: why does X imply Y?"],
    "references": ["Lagrange's theorem", "Sylow's first theorem"]
}
"""

_DIRECT_PROVING_USER_TEMPLATE = """Mathematical statement to prove:
{statement}

{context}

Provide a direct proof attempt. Output JSON only."""


async def direct_proving(
    statement: str,
    *,
    use_search: bool = True,
    model: Optional[str] = None,
    extra_context: Optional[str] = None,
    lang: Optional[str] = None,
) -> "ProofResult":
    """尝试直接证明 statement，返回 ProofResult。"""
    # 1. 搜索相关定理作为参考上下文
    references: list[TheoremMatch] = []
    context_text = ""

    if use_search:
        try:
            references = await search_theorems(statement, top_k=5, min_sim=0.3)
            context_text = format_theorems_for_prompt(references)
        except Exception:
            context_text = "（定理检索暂时不可用）"

    if extra_context:
        context_text = extra_context + "\n\n" + context_text

    user_msg = _DIRECT_PROVING_USER_TEMPLATE.format(
        statement=statement,
        context=context_text,
    )

    sys_prompt = _DIRECT_PROVING_SYSTEM + lang_sys_suffix(lang)
    try:
        raw = await chat_json(user_msg, system=sys_prompt, model=model)
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, Exception) as e:
        return ProofResult(
            proof=str(e),
            confidence=0.0,
            status="failed",
            gaps=[f"LLM 调用失败: {e}"],
            references=[],
        )

    return ProofResult(
        proof=data.get("proof", "") if isinstance(data, dict) else "",
        confidence=_safe_float(data.get("confidence") if isinstance(data, dict) else None),
        status=data.get("status", "failed") if isinstance(data, dict) else "failed",
        gaps=_safe_list(data.get("gaps") if isinstance(data, dict) else None),
        references=_safe_list(data.get("references") if isinstance(data, dict) else None),
        theorem_matches=references,
    )


@dataclass
class ProofResult:
    proof: str
    confidence: float
    status: str  # "proved" | "partial" | "failed"
    gaps: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    theorem_matches: list[TheoremMatch] = field(default_factory=list)

    def is_successful(self) -> bool:
        return self.status in ("proved", "partial") and len(self.proof) > 100

    def to_dict(self) -> dict:
        return {
            "proof": self.proof,
            "confidence": self.confidence,
            "status": self.status,
            "gaps": self.gaps,
            "references": self.references,
        }
