"""技能：subgoal_decomp —— 将复杂命题分解为若干可独立证明的子目标。

参考：Rethlas `propose-subgoal-decomposition-plans/SKILL.md`

输出：
    DecompResult:
        subgoals    (list[Subgoal])  分解后的子目标列表
        strategy    (str)           整体证明策略描述
        rationale   (str)           为什么选择此分解方式
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from core.llm import chat_json

_DECOMP_SYSTEM = """You are an expert mathematician specializing in proof strategy.
Your task is to decompose a complex mathematical statement into 2-4 manageable subgoals.

Each subgoal should:
- Be independently provable (or reducible to known results)
- Together with other subgoals, imply the main statement
- Be clearly stated as a self-contained mathematical claim

Output MUST be valid JSON with this schema:
{
    "strategy": "We use induction on the order of the group...",
    "rationale": "This decomposition works because...",
    "subgoals": [
        {
            "id": "S1",
            "statement": "First, show that every element has finite order...",
            "type": "auxiliary",  // "auxiliary" | "key_lemma" | "base_case" | "induction_step"
            "depends_on": [],
            "hint": "Use Lagrange's theorem on finite groups"
        },
        ...
    ]
}
"""

_DECOMP_USER_TEMPLATE = """Complex mathematical statement to decompose:
{statement}

{extra_context}

Propose 2-4 subgoals that together prove the statement. Output JSON only."""


@dataclass
class Subgoal:
    id: str
    statement: str
    type: str  # "auxiliary" | "key_lemma" | "base_case" | "induction_step"
    depends_on: list[str] = field(default_factory=list)
    hint: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type,
            "depends_on": self.depends_on,
            "hint": self.hint,
        }


@dataclass
class DecompResult:
    subgoals: list[Subgoal]
    strategy: str = ""
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "rationale": self.rationale,
            "subgoals": [s.to_dict() for s in self.subgoals],
        }


async def subgoal_decomp(
    statement: str,
    *,
    model: Optional[str] = None,
    extra_context: str = "",
) -> DecompResult:
    """将 statement 分解为子目标，返回 DecompResult。"""
    user_msg = _DECOMP_USER_TEMPLATE.format(
        statement=statement,
        extra_context=extra_context,
    )

    try:
        raw = await chat_json(user_msg, system=_DECOMP_SYSTEM, model=model)
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        return DecompResult(
            subgoals=[],
            strategy=f"分解失败: {e}",
        )

    subgoals = []
    for sg in data.get("subgoals", []):
        subgoals.append(
            Subgoal(
                id=sg.get("id", f"S{len(subgoals)+1}"),
                statement=sg.get("statement", ""),
                type=sg.get("type", "auxiliary"),
                depends_on=sg.get("depends_on", []),
                hint=sg.get("hint", ""),
            )
        )

    return DecompResult(
        subgoals=subgoals,
        strategy=data.get("strategy", ""),
        rationale=data.get("rationale", ""),
    )
