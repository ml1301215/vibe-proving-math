"""技能：counterexamples —— 尝试为疑似错误的命题构造反例。

参考：Rethlas `construct-counterexamples/SKILL.md`

用于：
  - 研究模式论文审查中，对 uncertain 步骤进行验证
  - 帮助识别错误证明

输出：
    CounterexampleResult:
        found       (bool)   是否找到反例
        counterexample (str) 具体反例描述
        explanation  (str)   为什么这是反例
        confidence   (float) 0-1
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from core.llm import chat_json

_CE_SYSTEM = """You are a mathematical counterexample expert.
Your task is to try to construct a counterexample to the given mathematical claim.

If the claim is TRUE (no counterexample exists), say so honestly.
If you can find a counterexample, provide it concisely and verify it satisfies all conditions.

IMPORTANT formatting rules:
- ALL mathematical expressions must use $...$ (inline) or $$...$$ (display) delimiters.
  Example: "$p(x) = x - 1$", "$$\\frac{1}{\\Phi_n(p)} \\geq \\frac{1}{\\Phi_n(q)}$$"
- In JSON strings, you MUST escape every backslash: write "\\\\frac" not "\\frac".
- Keep counterexample and explanation concise but precise.

Output MUST be valid JSON with this schema:
{
    "found": true,
    "counterexample": "Let $n=1$. Take $p(x) = x - 1$ and $q(x) = x - 1$...",
    "explanation": "This gives $\\\\frac{1}{\\\\Phi_1(p \\\\boxplus_1 q)} = 1$, but $\\\\frac{1}{\\\\Phi_1(p)} + \\\\frac{1}{\\\\Phi_1(q)} = 2$...",
    "confidence": 0.9,
    "note": "The claim might hold under additional conditions..."
}
"""

_CE_USER_TEMPLATE = """Mathematical claim (potentially false):
{statement}

{context}

Try to find a counterexample. Output JSON only."""


@dataclass
class CounterexampleResult:
    found: bool
    counterexample: str = ""
    explanation: str = ""
    confidence: float = 0.0
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "counterexample": self.counterexample,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "note": self.note,
        }


async def find_counterexample(
    statement: str,
    *,
    context: str = "",
    model: Optional[str] = None,
) -> CounterexampleResult:
    """尝试为 statement 构造反例。"""
    user_msg = _CE_USER_TEMPLATE.format(statement=statement, context=context)

    try:
        raw = await chat_json(user_msg, system=_CE_SYSTEM, model=model)
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        return CounterexampleResult(found=False, note=f"调用失败: {e}")

    return CounterexampleResult(
        found=bool(data.get("found", False)),
        counterexample=data.get("counterexample", ""),
        explanation=data.get("explanation", ""),
        confidence=float(data.get("confidence", 0.0)),
        note=data.get("note", ""),
    )
