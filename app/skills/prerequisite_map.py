"""技能：prerequisite_map —— 为数学命题生成前置知识图谱（学习模式专属）。

两阶段流程：
  Step 1: LLM 生成候选前置知识列表（宽松）
  Step 2: TheoremSearch 并行补充定理链接
  Step 3: LLM 二次验证 —— 筛掉非必要项，基于留下的项派生学习路径
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional

from core.llm import chat_json
from skills.search_theorems import search_theorems, TheoremMatch


# ── 第一阶段：生成候选前置知识 ─────────────────────────────────────────────────

_PREREQ_GENERATE_SYSTEM = """You are a mathematics educator analyzing prerequisites for a theorem.

List the concepts and theorems that appear DIRECTLY in a standard proof of the given statement.
A prerequisite qualifies only if:
- It is explicitly invoked in the proof (not mere background)
- A student who lacks it would be blocked from following the argument
- It is specific to the topic (not universal basics like "logic", "sets", "arithmetic")

Calibrate depth to the statement:
- Elementary result (e.g., Euclid's proof of infinitely many primes): 1-2 prerequisites
- Standard undergraduate theorem: 2-4 prerequisites
- Graduate-level result: 3-5 prerequisites, never more

Each description: ONE sentence, precise, with all math in $...$. No preamble.

Output ONLY valid JSON:
{
  "prerequisites": [
    {
      "concept": "concise name with LaTeX math",
      "type": "definition | theorem | technique",
      "description": "One sentence. Use $...$ for all math.",
      "search_query": "short English keywords for a theorem database"
    }
  ]
}
"""

_PREREQ_GENERATE_USER = """Mathematical statement: {statement}

Student level: {level}

List candidate prerequisites. JSON only."""


# ── 第三阶段：验证并派生学习路径 ───────────────────────────────────────────────

_PREREQ_VALIDATE_SYSTEM = """You are a strict mathematics educator reviewing a prerequisite list.

Given a mathematical statement and a candidate list of prerequisites (with any matching theorem
database entries), your tasks:

1. REMOVE prerequisites that are:
   - Not directly invoked in a proof of this statement
   - Redundant with another prerequisite in the list
   - Too elementary for any student who would encounter this statement
2. MERGE closely related prerequisites into one item
   (e.g. "prime numbers" + "prime divisors" + "divisibility" → "Prime numbers and divisibility")
3. KEEP only the minimum set of truly distinct, necessary prerequisites (aim for 2–3 items)
4. Write a LEARNING PATH: an ordered sequence of 3-6 steps showing how a student should
   build up to this result, derived from the kept prerequisites.
   - Start from the most foundational concept, end at the theorem itself.
   - Steps should be concept names or short phrases, not full sentences.

Output ONLY valid JSON:
{
  "prerequisites": [
    {
      "concept": "...",
      "type": "definition | theorem | technique",
      "description": "One sentence.",
      "search_query": "..."
    }
  ],
  "learning_path": ["concept A", "concept B", "..."],
  "difficulty": "undergraduate | graduate"
}
"""

_PREREQ_VALIDATE_USER = """Mathematical statement:
{statement}

Candidate prerequisites (with any matched theorem references):
{candidates_json}

Filter to only the truly necessary ones, then derive the learning path. JSON only."""


# ── 数据结构 ────────────────────────────────────────────────────────────────────

@dataclass
class Prerequisite:
    concept: str
    type: str        # "definition" | "theorem" | "technique"
    description: str
    search_query: str = ""
    theorem_matches: list[TheoremMatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "type": self.type,
            "description": self.description,
            "theorem_refs": [
                {"name": m.name, "similarity": round(float(m.similarity), 3), "link": m.link}
                for m in self.theorem_matches[:2]
            ],
        }


@dataclass
class PrerequisiteMap:
    prerequisites: list[Prerequisite]
    learning_path: list[str]
    difficulty: str = "undergraduate"

    def to_dict(self) -> dict:
        return {
            "difficulty": self.difficulty,
            "learning_path": self.learning_path,
            "prerequisites": [p.to_dict() for p in self.prerequisites],
        }

    def to_prompt_text(self) -> str:
        lines = ["【前置知识清单】"]
        for p in self.prerequisites:
            refs = ""
            if p.theorem_matches:
                top = p.theorem_matches[0]
                refs = f" → [{top.name}]({top.link})"
            lines.append(f"- **{p.concept}** ({p.type}): {p.description}{refs}")
        if self.learning_path:
            lines.append("\n**推荐学习路径：** " + " → ".join(self.learning_path))
        return "\n".join(lines)


# ── 主接口 ──────────────────────────────────────────────────────────────────────

async def prerequisite_map(
    statement: str,
    *,
    level: str = "undergraduate",
    enrich_with_search: bool = True,
    model: Optional[str] = None,
) -> PrerequisiteMap:
    """两阶段 LLM + TheoremSearch 前置知识图谱。"""

    # ── Step 1: 生成候选列表 ─────────────────────────────────────────────────
    try:
        raw = await chat_json(
            _PREREQ_GENERATE_USER.format(statement=statement, level=level),
            system=_PREREQ_GENERATE_SYSTEM,
            model=model,
        )
        raw_data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(raw_data, dict):
            raw_data = {}
        raw_items = [(it if isinstance(it, dict) else {}) for it in (raw_data.get("prerequisites") or [])[:7]]
    except Exception:
        return PrerequisiteMap(prerequisites=[], learning_path=[], difficulty="unknown")

    # ── Step 2: 并行 TheoremSearch 丰富 ──────────────────────────────────────
    async def _enrich(item: dict) -> Prerequisite:
        matches: list[TheoremMatch] = []
        if enrich_with_search and item.get("search_query"):
            try:
                matches = await search_theorems(
                    item["search_query"], top_k=2, min_sim=0.5
                )
            except Exception:
                pass
        return Prerequisite(
            concept=item.get("concept", ""),
            type=item.get("type", "definition"),
            description=item.get("description", ""),
            search_query=item.get("search_query", ""),
            theorem_matches=matches,
        )

    candidates: list[Prerequisite] = list(
        await asyncio.gather(*[_enrich(it) for it in raw_items])
    )

    # ── Step 3: LLM 验证 + 学习路径派生 ──────────────────────────────────────
    candidates_for_prompt = json.dumps(
        [p.to_dict() for p in candidates], ensure_ascii=False, indent=2
    )
    try:
        val_raw = await chat_json(
            _PREREQ_VALIDATE_USER.format(
                statement=statement,
                candidates_json=candidates_for_prompt,
            ),
            system=_PREREQ_VALIDATE_SYSTEM,
            model=model,
        )
        val_data = json.loads(val_raw) if isinstance(val_raw, str) else val_raw
        if not isinstance(val_data, dict):
            val_data = {}
    except Exception:
        # 验证失败时降级为候选列表
        return PrerequisiteMap(
            prerequisites=candidates[:5],
            learning_path=[p.concept for p in candidates[:5]],
            difficulty="undergraduate",
        )

    # 将验证后的项映射回候选（复用 TheoremSearch 结果）
    concept_to_candidate: dict[str, Prerequisite] = {
        p.concept.lower().strip(): p for p in candidates
    }

    final_prereqs: list[Prerequisite] = []
    for item in (val_data.get("prerequisites") or []):
        if not isinstance(item, dict):
            continue  # 跳过非 dict 元素，防止 item.get() AttributeError
        concept_key = item.get("concept", "").lower().strip()
        # 用前缀匹配复用 TheoremSearch 结果
        matched_candidate = concept_to_candidate.get(concept_key)
        if not matched_candidate:
            matched_candidate = next(
                (c for k, c in concept_to_candidate.items()
                 if concept_key[:15] in k or k[:15] in concept_key),
                None,
            )
        final_prereqs.append(Prerequisite(
            concept=item.get("concept", ""),
            type=item.get("type", "definition"),
            description=item.get("description", ""),
            search_query=item.get("search_query", ""),
            theorem_matches=matched_candidate.theorem_matches if matched_candidate else [],
        ))

    raw_path = val_data.get("learning_path", [])
    if isinstance(raw_path, str):
        # LLM 返回字符串而非列表时，按常见分隔符拆分
        import re as _re
        raw_path = [s.strip() for s in _re.split(r'[→\->,;]', raw_path) if s.strip()]
    return PrerequisiteMap(
        prerequisites=final_prereqs[:5],
        learning_path=raw_path,
        difficulty=val_data.get("difficulty", "undergraduate"),
    )
