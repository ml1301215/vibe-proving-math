#!/usr/bin/env python3
"""详细调试LLM调用"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

import logging
logging.basicConfig(level=logging.DEBUG)

from core.llm import stream_chat_with_reasoning
from core.config import llm_cfg

async def test_debug():
    print("=" * 60)
    print("LLM Configuration:")
    print(f"  base_url: {llm_cfg().get('base_url')}")
    print(f"  model: {llm_cfg().get('model')}")
    print(f"  api_key: {'*' * 20}{llm_cfg().get('api_key', '')[-10:]}")
    print("=" * 60)

    chunk_count = 0
    content_chunks = 0
    reasoning_chunks = 0

    try:
        print("\nCalling stream_chat_with_reasoning...")
        async for kind, text in stream_chat_with_reasoning(
            "Say hello in one sentence",
            system="You are a helpful assistant",
            model="deepseek-v4pro",
            max_tokens=100
        ):
            chunk_count += 1
            if kind == "content":
                content_chunks += 1
                print(f"[CONTENT] {text}", end="", flush=True)
            elif kind == "reasoning":
                reasoning_chunks += 1
                print(f"[REASONING] {text[:50]}...", flush=True)

        print("\n" + "=" * 60)
        print(f"Total chunks: {chunk_count}")
        print(f"Content chunks: {content_chunks}")
        print(f"Reasoning chunks: {reasoning_chunks}")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_debug())
