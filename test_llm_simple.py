#!/usr/bin/env python3
"""简单测试LLM调用"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from core.llm import stream_chat

async def test_simple():
    print("Testing simple LLM call...")
    print("=" * 60)

    chunk_count = 0
    total_chars = 0

    try:
        async for chunk in stream_chat("Say hello", system="You are a helpful assistant", model="deepseek-v4pro", max_tokens=100):
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
    asyncio.run(test_simple())
