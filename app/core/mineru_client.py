"""MinerU Agent Lightweight Extract API client（异步）。

调用 MinerU Agent 轻量解析 API，无需 token，IP 限频。
API 失败时返回 None，由调用方决定是否降级。

用法：
    from core.mineru_client import extract_pdf_markdown
    err: list[str] = []
    markdown = await extract_pdf_markdown(pdf_bytes, progress=cb, last_error=err)
    # None → 调用方可降级；err 可能含失败原因
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable, List, Optional

import httpx

from core.config import mineru_cfg
from core.pdf_fix import fix_all, split_markdown_into_chunks

logger = logging.getLogger(__name__)

_BASE_URL       = "https://mineru.net/api/v1/agent"
_UPLOAD_TIMEOUT = 120.0
_POLL_INTERVAL  =   3.0
_POLL_TIMEOUT   = 300.0

ProgressCb = Optional[Callable[[str, str], Awaitable[None]]]


def _record_error(last_error: Optional[List[str]], message: str) -> None:
    if last_error is not None:
        last_error.append(message)


async def _emit(cb: ProgressCb, step: str, msg: str) -> None:
    if cb is None:
        return
    try:
        await cb(step, msg)
    except Exception:
        pass


async def extract_pdf_markdown(
    pdf_bytes: bytes,
    *,
    token: Optional[str] = None,
    filename: str = "upload.pdf",
    progress: ProgressCb = None,
    last_error: Optional[list[str]] = None,
) -> Optional[str]:
    """从 PDF 字节流提取 Markdown（MinerU Agent 轻量文件上传 API）。

    返回修复后的 Markdown 字符串，或 None（API 失败 / 限频 / 文件超限时）。
    若传入 ``last_error`` 列表，失败时会在其中追加人类可读原因。

    ``token`` 参数仅为兼容旧调用签名保留；Agent 轻量 API 不使用 token。
    """
    if not pdf_bytes:
        _record_error(last_error, "PDF 内容为空")
        return None

    cfg = mineru_cfg()
    max_file_bytes = int(float(cfg.get("max_file_mb") or 10) * 1024 * 1024)
    if len(pdf_bytes) > max_file_bytes:
        msg = f"MinerU Agent 轻量解析文件大小超限（{len(pdf_bytes)/1024/1024:.1f}MB > {max_file_bytes/1024/1024:.0f}MB）"
        logger.info(msg)
        _record_error(last_error, msg)
        return None

    base_url = str(cfg.get("base_url") or _BASE_URL).rstrip("/")
    poll_interval = float(cfg.get("poll_interval_seconds") or _POLL_INTERVAL)
    poll_timeout = float(cfg.get("poll_timeout_seconds") or _POLL_TIMEOUT)
    request_timeout = float(cfg.get("request_timeout_seconds") or _UPLOAD_TIMEOUT)
    language = str(cfg.get("language") or "ch").strip() or "ch"
    page_range = str(cfg.get("page_range") or "").strip()
    enable_table = bool(cfg.get("enable_table", True))
    enable_formula = bool(cfg.get("enable_formula", True))
    is_ocr = bool(cfg.get("is_ocr", False))

    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(
        follow_redirects=True,
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
    ) as http:

        # Step 1: 创建 Agent 轻量文件解析任务并申请上传链接
        await _emit(progress, "mineru_upload", "创建 MinerU Agent 轻量解析任务…")
        task_id: str = ""
        file_url: str = ""
        payload = {
            "file_name": filename,
            "language": language,
            "enable_table": enable_table,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
        }
        if page_range:
            payload["page_range"] = page_range
        try:
            resp = await http.post(
                f"{base_url}/parse/file",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                msg = f"MinerU Agent 创建任务失败: {data}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
            inner = data.get("data") or {}
            task_id = inner.get("task_id") or ""
            file_url = inner.get("file_url") or ""
            if not task_id or not file_url:
                msg = f"MinerU Agent step1 返回缺少 task_id 或 file_url: {data}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
            if not isinstance(file_url, str) or not file_url.startswith("http"):
                msg = f"MinerU Agent step1 无效上传 URL: {file_url!r}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
        except Exception as exc:
            msg = f"MinerU Agent step1 failed: {exc}"
            logger.warning(msg)
            _record_error(last_error, msg)
            return None

        # Step 2: 上传 PDF（带 1 次重试；勿加 Content-Type，否则 OSS 预签名常返回 403）
        await _emit(progress, "mineru_upload", f"上传 PDF（{len(pdf_bytes)/1024:.0f} KB）…")
        last_put_exc: Optional[Exception] = None
        for attempt in range(2):
            try:
                put = await http.put(
                    file_url,
                    content=pdf_bytes,
                    timeout=request_timeout,
                )
                put.raise_for_status()
                break
            except Exception as exc:
                last_put_exc = exc
                logger.warning("MinerU PUT attempt %d failed: %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                msg = f"MinerU Agent 上传 PDF 失败（已重试）: {last_put_exc}"
                _record_error(last_error, msg)
                return None

        # Step 3: 轮询解析结果（先立即轮询一次，再按间隔等待）
        await _emit(progress, "mineru_parse", "MinerU Agent 轻量解析中…")
        start = time.monotonic()
        markdown_url: Optional[str] = None
        first_poll = True
        while time.monotonic() - start < poll_timeout:
            if not first_poll:
                await asyncio.sleep(poll_interval)
            first_poll = False
            try:
                r = await http.get(
                    f"{base_url}/parse/{task_id}",
                    timeout=30.0,
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 0:
                    msg = f"MinerU Agent poll error: {data}"
                    logger.warning(msg)
                    _record_error(last_error, msg)
                    return None
                item = data.get("data") or {}
                state = item.get("state", "")
                elapsed = int(time.monotonic() - start)
                if state == "done":
                    markdown_url = item.get("markdown_url", "") or ""
                    if not markdown_url:
                        msg = "MinerU Agent 解析完成但缺少 markdown_url"
                        logger.warning(msg)
                        _record_error(last_error, msg)
                        return None
                    await _emit(progress, "mineru_parse", f"解析完成（{elapsed}s）")
                    break
                if state == "failed":
                    err_msg = item.get("err_msg") or "unknown"
                    err_code = item.get("err_code")
                    suffix = f"（错误码 {err_code}）" if err_code is not None else ""
                    msg = f"MinerU Agent 解析失败{suffix}: {err_msg}"
                    logger.warning(msg)
                    _record_error(last_error, msg)
                    return None
                await _emit(progress, "mineru_parse", f"解析中…{state or 'pending'}（{elapsed}s）")
            except Exception as exc:
                resp = getattr(exc, "response", None)
                status = getattr(resp, "status_code", None) if resp is not None else None
                logger.warning("MinerU Agent poll exception (HTTP %s): %s", status, exc)
                # 单次失败不立即退出，继续轮询直到总超时
        else:
            msg = f"MinerU Agent 解析超时（{int(poll_timeout)}s）"
            logger.warning(msg)
            _record_error(last_error, msg)
            return None

        # Step 4: 下载 Markdown
        await _emit(progress, "mineru_download", "下载 Markdown 解析结果…")
        try:
            dl = await http.get(markdown_url or "", timeout=request_timeout)
            dl.raise_for_status()
            raw_md = dl.text
        except Exception as exc:
            msg = f"MinerU Agent 下载 Markdown 失败: {exc}"
            logger.warning(msg)
            _record_error(last_error, msg)
            return None

        # Step 5: 后处理修复
        await _emit(progress, "mineru_fix", "应用后处理修复管道…")
        fixed = fix_all(raw_md)
        logger.info("MinerU 提取完成：%d → %d 字符", len(raw_md), len(fixed))
        return fixed


async def extract_url_markdown(
    url: str,
    *,
    filename: str = "",
    progress: ProgressCb = None,
    last_error: Optional[list[str]] = None,
) -> Optional[str]:
    """通过 MinerU Agent URL 解析 API 提取 Markdown。"""
    if not url.strip():
        _record_error(last_error, "URL 为空")
        return None

    cfg = mineru_cfg()
    base_url = str(cfg.get("base_url") or _BASE_URL).rstrip("/")
    poll_interval = float(cfg.get("poll_interval_seconds") or _POLL_INTERVAL)
    poll_timeout = float(cfg.get("poll_timeout_seconds") or _POLL_TIMEOUT)
    request_timeout = float(cfg.get("request_timeout_seconds") or _UPLOAD_TIMEOUT)
    payload = {
        "url": url.strip(),
        "language": str(cfg.get("language") or "ch").strip() or "ch",
        "enable_table": bool(cfg.get("enable_table", True)),
        "is_ocr": bool(cfg.get("is_ocr", False)),
        "enable_formula": bool(cfg.get("enable_formula", True)),
    }
    if filename.strip():
        payload["file_name"] = filename.strip()
    page_range = str(cfg.get("page_range") or "").strip()
    if page_range:
        payload["page_range"] = page_range

    async with httpx.AsyncClient(follow_redirects=True) as http:
        await _emit(progress, "mineru_submit", "提交 MinerU Agent URL 解析任务…")
        try:
            resp = await http.post(f"{base_url}/parse/url", headers={"Content-Type": "application/json"}, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                msg = f"MinerU Agent URL 任务提交失败: {data}"
                _record_error(last_error, msg)
                logger.warning(msg)
                return None
            task_id = (data.get("data") or {}).get("task_id") or ""
            if not task_id:
                msg = f"MinerU Agent URL 返回缺少 task_id: {data}"
                _record_error(last_error, msg)
                logger.warning(msg)
                return None
        except Exception as exc:
            msg = f"MinerU Agent URL 提交失败: {exc}"
            _record_error(last_error, msg)
            logger.warning(msg)
            return None

        start = time.monotonic()
        markdown_url = ""
        while time.monotonic() - start < poll_timeout:
            try:
                r = await http.get(f"{base_url}/parse/{task_id}", timeout=30.0)
                r.raise_for_status()
                data = r.json()
                item = data.get("data") or {}
                state = item.get("state", "")
                elapsed = int(time.monotonic() - start)
                if data.get("code") != 0:
                    msg = f"MinerU Agent URL poll error: {data}"
                    _record_error(last_error, msg)
                    logger.warning(msg)
                    return None
                if state == "done":
                    markdown_url = item.get("markdown_url") or ""
                    break
                if state == "failed":
                    msg = f"MinerU Agent URL 解析失败: {item.get('err_msg') or 'unknown'}"
                    _record_error(last_error, msg)
                    logger.warning(msg)
                    return None
                await _emit(progress, "mineru_parse", f"解析中…{state or 'pending'}（{elapsed}s）")
            except Exception as exc:
                logger.warning("MinerU Agent URL poll exception: %s", exc)
            await asyncio.sleep(poll_interval)

        if not markdown_url:
            msg = f"MinerU Agent URL 解析超时（{int(poll_timeout)}s）"
            _record_error(last_error, msg)
            logger.warning(msg)
            return None

        try:
            dl = await http.get(markdown_url, timeout=request_timeout)
            dl.raise_for_status()
            raw_md = dl.text
        except Exception as exc:
            msg = f"MinerU Agent URL 下载 Markdown 失败: {exc}"
            _record_error(last_error, msg)
            logger.warning(msg)
            return None

    fixed = fix_all(raw_md)
    logger.info("MinerU URL 提取完成：%d → %d 字符", len(raw_md), len(fixed))
    return fixed


def get_mineru_chunks(markdown: str, max_chars: int = 4000) -> list[str]:
    """将 MinerU Markdown 切分为审查用的块列表。"""
    return split_markdown_into_chunks(markdown, max_chars=max_chars)
