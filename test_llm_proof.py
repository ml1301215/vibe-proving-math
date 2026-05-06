#!/usr/bin/env python3
"""测试LLM调用 - 调试proof生成问题"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from core.llm import stream_chat

async def test_proof_generation():
    statement = "What is Pythagorean theorem"

    user_msg = f"Write a complete proof and explanation for:\n\n{statement}"

    system_msg = """You are a mathematics educator writing a complete, pedagogically rigorous exposition.
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

    print(f"Testing proof generation for: {statement}")
    print("=" * 60)
    print(f"User message: {user_msg}")
    print("=" * 60)

    chunk_count = 0
    total_chars = 0

    try:
        async for chunk in stream_chat(user_msg, system=system_msg, model="deepseek-v4pro", max_tokens=3000):
            chunk_count += 1
            total_chars += len(chunk)
            print(chunk, end="", flush=True)

        print("\n" + "=" * 60)
        print(f"Total chunks: {chunk_count}")
        print(f"Total characters: {total_chars}")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_proof_generation())
