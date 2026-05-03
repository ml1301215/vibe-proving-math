"""LLM 客户端 —— 统一封装 OpenAI 兼容接口，指向 OpenRouter 代理。

优化记录：
  - AsyncOpenAI 客户端单例化，避免每次调用重建 HTTP 连接
  - chat_json 重试次数从 6 降至 4（json_mode 2 + fallback 2），减少无效等待
  - 超长 prompt 自动截断（max_prompt_chars），防止 token 超限

支持两种调用风格：
    # 字符串风格（简洁）
    reply = await chat("证明费马小定理")

    # 带系统提示
    reply = await chat("...", system="你是数学助手")

    # 流式
    async for chunk in stream_chat("..."):
        print(chunk, end="", flush=True)

    # JSON 模式，返回 dict
    result = await chat_json("返回包含 answer 字段的 JSON", model="deepseek/deepseek-r1")
"""
from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator, Optional, Union


def _fix_latex_json(text: str) -> str:
    """Fix unescaped LaTeX backslashes in JSON before json.loads.

    LLMs often write \\frac{...} as \\frac without escaping the backslash.
    json.loads silently converts \\f → form-feed, \\n → newline, \\b → backspace, etc.
    This regex doubles backslashes before 2+ letter sequences (LaTeX commands),
    preserving valid single-letter JSON escapes: \\n \\t \\r \\b \\f \\u.
    """
    if not text or '\\' not in text:
        return text
    return re.sub(r'(?<!\\)\\([A-Za-z]{2,})', r'\\\\\1', text)

from openai import AsyncOpenAI

from .config import llm_cfg

logger = logging.getLogger(__name__)

_MsgInput = Union[str, list[dict]]

# ── 单例 LLM 客户端 ────────────────────────────────────────────────────────────
# 在首次使用时创建，进程生命周期内复用同一 AsyncOpenAI 实例（内置连接池）
_llm_client: Optional[AsyncOpenAI] = None
_config_override: dict = {}


def update_config_override(patch: dict) -> None:
    """热更新 LLM 配置（由 server /config/llm 调用），下次 get_client() 会使用新配置。"""
    global _config_override, _llm_client
    _config_override = {k: v for k, v in patch.items() if v}
    _llm_client = None  # 强制下次重建客户端


def get_client() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        import httpx as _httpx
        cfg = dict(llm_cfg())
        cfg.update(_config_override)  # 运行时覆盖优先
        # plan B：移除全部超时（解题模式以解决问题为核心目标，长耗时不是问题）
        # 使用 httpx.Timeout(None) 显式禁用 read/write/connect 全部超时
        _llm_client = AsyncOpenAI(
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=_httpx.Timeout(None, connect=30.0),  # 仅保留连接超时（30s）
        )
        logger.debug(
            "LLM client created: base_url=%s model=%s timeout=disabled",
            cfg["base_url"],
            cfg.get("model", "unknown"),
        )
    return _llm_client


def reset_client() -> None:
    """仅测试时使用：清除单例，下次 get_client() 重新创建。"""
    global _llm_client
    _llm_client = None


def _effective_model(model: Optional[str] = None) -> str:
    """返回有效模型名称：显式参数 > 运行时覆盖 > config.toml 默认值。"""
    if model:
        return _normalize_model(model)
    return _normalize_model(_config_override.get("model") or llm_cfg().get("model", "gpt-4o"))


# ── Prompt 工具 ────────────────────────────────────────────────────────────────
MAX_PROMPT_CHARS = 16_000  # 约 4000 tokens，超出则从中间截断（保留头尾）


def _truncate_content(text: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """安全截断超长文本：保留前 60% + 省略提示 + 后 30%。"""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.6)
    tail = int(max_chars * 0.3)
    omitted = len(text) - head - tail
    return (
        text[:head]
        + f"\n\n[... {omitted} chars omitted for token budget ...]\n\n"
        + text[-tail:]
    )


def _build_messages(
    user_message: _MsgInput,
    system: Optional[str] = None,
    extra_messages: Optional[list[dict]] = None,
) -> list[dict]:
    """统一将各种输入格式转换为 OpenAI messages 列表，并截断超长内容。"""
    messages: list[dict] = []

    if system:
        messages.append({"role": "system", "content": system})

    if isinstance(user_message, list):
        for msg in user_message:
            if isinstance(msg.get("content"), str):
                msg = {**msg, "content": _truncate_content(msg["content"])}
            messages.append(msg)
    else:
        if extra_messages:
            messages.extend(extra_messages)
        content = _truncate_content(str(user_message))
        messages.append({"role": "user", "content": content})

    return messages


def _extract_content(resp_obj) -> str:
    """从 LLM 响应中提取文本内容（兼容 reasoning_content 字段）。"""
    c = resp_obj.choices[0].message.content
    if not c:
        rc = getattr(resp_obj.choices[0].message, "reasoning_content", None)
        c = rc or ""
    return c


def _append_hint_to_content(content, hint: str):
    """给 text 或多模态 content 追加文本提示。"""
    if isinstance(content, str):
        return content + hint
    if isinstance(content, list):
        return [*content, {"type": "text", "text": hint}]
    return content


# ── 公共 API ───────────────────────────────────────────────────────────────────

# 此 API 不接受 provider/ 前缀格式（OpenRouter 风格），需归一化
_PROVIDER_PREFIXES = ("google/", "openai/", "anthropic/", "meta-llama/", "mistralai/",
                      "deepseek/", "x-ai/", "cohere/", "qwen/", "together/")

def _normalize_model(model_id: str) -> str:
    """去掉 'provider/' 前缀，适配本地 API 的模型命名格式。"""
    for prefix in _PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


_LANG_SUFFIX_ZH = (
    "\n\nCRITICAL — LANGUAGE REQUIREMENT: The user submitted this problem in Chinese. "
    "You MUST write your ENTIRE response in Simplified Chinese (简体中文). "
    "This applies to: headings, proof steps, explanations, examples, summaries, and all prose. "
    "LaTeX math formulas ($...$, $$...$$) stay in standard mathematical notation as-is. "
    "Absolutely NO English prose is allowed."
)

_LANG_SUFFIX_EN = (
    "\n\nCRITICAL — LANGUAGE REQUIREMENT: You MUST write your ENTIRE response in English. "
    "This applies to: headings, proof steps, explanations, examples, summaries, and all prose. "
    "LaTeX math formulas ($...$, $$...$$) stay in standard mathematical notation as-is. "
    "Absolutely NO Chinese or other non-English prose is allowed."
)


def lang_sys_suffix(lang: Optional[str]) -> str:
    """返回需要追加到 system prompt 末尾的语言指令。"""
    if lang == "zh":
        return _LANG_SUFFIX_ZH
    if lang == "en":
        return _LANG_SUFFIX_EN
    return ""


async def chat(
    user_message: _MsgInput,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    extra_messages: Optional[list[dict]] = None,
    _retries: int = 2,
) -> str:
    """单次非流式调用，返回完整回复字符串。空响应时自动重试（最多 _retries 次）。"""
    import asyncio as _asyncio
    client = get_client()
    messages = _build_messages(user_message, system=system, extra_messages=extra_messages)
    _model = _effective_model(model)

    last_content = ""
    for attempt in range(_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = _extract_content(resp)
            if content:
                if attempt > 0:
                    logger.debug("chat() succeeded on attempt %d", attempt + 1)
                return content
            last_content = content
        except Exception as exc:
            logger.warning("chat() attempt %d/%d failed: %s", attempt + 1, _retries + 1, exc)
            last_content = ""
        if attempt < _retries:
            await _asyncio.sleep(2)

    logger.warning("chat() returned empty after %d attempts", _retries + 1)
    return last_content


async def stream_chat(
    user_message: _MsgInput,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    extra_messages: Optional[list[dict]] = None,
) -> AsyncIterator[str]:
    """流式调用，逐 token yield **正文**字符串片段（reasoning 在此接口被丢弃）。

    若需要同时拿到推理链，请用 `stream_chat_with_reasoning`。
    """
    async for kind, text in stream_chat_with_reasoning(
        user_message,
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_messages=extra_messages,
    ):
        if kind == "content" and text:
            yield text


async def stream_chat_with_reasoning(
    user_message: _MsgInput,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    extra_messages: Optional[list[dict]] = None,
) -> AsyncIterator[tuple[str, str]]:
    """流式调用，yield (kind, text) 元组：
        kind = "reasoning" — 模型的思考链（chain-of-thought）
        kind = "content"   — 模型的最终回答正文

    通过 `extra_body={"reasoning": {"include": True}}` 显式要求网关把
    reasoning_content 一并流式下发；不同 OpenAI 兼容代理对推理链返回时机
    不同，实测可显著降低 deepseek-r1 类推理模型的首字节延迟。
    """
    cfg = llm_cfg()
    client = get_client()
    messages = _build_messages(user_message, system=system, extra_messages=extra_messages)

    try:
        stream = await client.chat.completions.create(
            model=_effective_model(model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            extra_body={"reasoning": {"include": True}},
        )
    except Exception:
        # 若 LLM 不支持 extra_body（如部分轻量代理），降级为不携带 reasoning 字段
        stream = await client.chat.completions.create(
            model=_effective_model(model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
    try:
        async for chunk in stream:
            if not chunk.choices:   # Gemini/一些网关会推送空 choices 的元数据块
                continue
            delta = chunk.choices[0].delta
            # 兼容三种字段：reasoning_content (DeepSeek)、reasoning (OpenRouter 扁平)
            r = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None) or ""
            c = delta.content or ""
            if r:
                yield ("reasoning", r)
            if c:
                yield ("content", c)
    except Exception as _e:
        logger.debug("stream_chat_with_reasoning: stream interrupted (%s)", _e)
        return  # 连接中断或服务端断流，停止迭代即可


async def chat_json(
    user_message: _MsgInput,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    schema: Optional[dict] = None,
) -> dict:
    """调用 LLM，要求以 JSON 格式返回并解析。

    优化：重试次数从 6 次降至 4 次（json_mode 2 + fallback 2），
    减少无效 API 调用和等待时间（原 2s sleep × 6 = 12s 最坏等待）。
    """
    import asyncio as _asyncio
    client = get_client()
    messages = _build_messages(user_message, system=system)
    _model = _effective_model(model)

    if schema:
        hint = f"\n\nRespond with valid JSON matching: {json.dumps(schema)}"
        last = messages[-1]
        messages[-1] = {**last, "content": _append_hint_to_content(last.get("content") or "", hint)}

    # ── Phase 1: JSON mode（2 次尝试，原 3 次）──────────────────────────────
    for attempt in range(2):
        try:
            resp = await client.chat.completions.create(
                model=_model,
                messages=messages,
                temperature=0.1,
                max_tokens=16384,  # plan F.3 (T46)：proof JSON 完整性优先，避免末尾截断
                response_format={"type": "json_object"},
            )
            text = _extract_content(resp) or "{}"
            parsed = json.loads(_fix_latex_json(text))
            if parsed:
                return parsed
        except Exception as exc:
            logger.debug("chat_json json_mode attempt %d failed: %s", attempt + 1, exc)
        if attempt < 1:
            await _asyncio.sleep(1)  # 原 2s → 1s

    # ── Phase 2: 普通 mode + 手动提取 JSON（2 次尝试，原 3 次）────────────────
    extra_hint = "\n\nIMPORTANT: Respond with valid JSON only, no markdown, no extra text."
    messages_fallback = list(messages)
    last = messages_fallback[-1]
    messages_fallback[-1] = {
        **last,
        "content": _append_hint_to_content(last.get("content") or "", extra_hint),
    }

    text = "{}"
    for attempt in range(2):
        try:
            resp = await client.chat.completions.create(
                model=_model,
                messages=messages_fallback,
                temperature=0.1,
                max_tokens=16384,  # plan F.3 (T46)：与 json_mode 路径对齐
            )
            text = _extract_content(resp) or "{}"
            if text and text != "{}":
                break
        except Exception as exc:
            logger.debug("chat_json fallback attempt %d failed: %s", attempt + 1, exc)
        if attempt < 1:
            await _asyncio.sleep(1)

    # 从 markdown 代码块中提取
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)

    try:
        return json.loads(_fix_latex_json(text))
    except json.JSONDecodeError:
        match2 = re.search(r"\{[\s\S]+\}", text)
        if match2:
            try:
                return json.loads(_fix_latex_json(match2.group(0)))
            except Exception:
                pass
    logger.warning("chat_json failed to parse JSON, returning empty dict")
    return {}
