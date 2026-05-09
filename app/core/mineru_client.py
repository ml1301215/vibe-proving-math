"""MinerU PDF 解析客户端（异步）。

调用 MinerU v4 精准 API（vlm 模型），自动应用 pdf_fix 后处理修复管道。
无 token 或 API 失败时返回 None，由调用方降级到 PyMuPDF。

用法：
    from core.mineru_client import extract_pdf_markdown
    err: list[str] = []
    markdown = await extract_pdf_markdown(pdf_bytes, token=tok, progress=cb, last_error=err)
    # None → 调用方应降级到 PyMuPDF；err 可能含失败原因
"""
from __future__ import annotations

import asyncio
import io
import logging
import time
import zipfile
from typing import Awaitable, Callable, List, Optional

import httpx

from core.config import mineru_cfg
from core.pdf_fix import fix_all, split_markdown_into_chunks

logger = logging.getLogger(__name__)

_BASE_URL       = "https://mineru.net/api/v4"
_UPLOAD_TIMEOUT = 120.0
_POLL_INTERVAL  =   8.0
_POLL_TIMEOUT   = 480.0

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
    """从 PDF 字节流提取带 LaTeX 的 Markdown（MinerU v4 精准 API，vlm 模型）。

    返回修复后的 Markdown 字符串，或 None（无 token / API 失败时）。
    若传入 ``last_error`` 列表，失败时会在其中追加人类可读原因。
    """
    if not pdf_bytes:
        _record_error(last_error, "PDF 内容为空")
        return None

    token = (token or mineru_cfg().get("token") or "").strip()
    if not token:
        logger.info("未配置 MinerU token，跳过 MinerU 解析")
        _record_error(last_error, "未配置 MinerU Token（config.toml [mineru].token）")
        return None

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        follow_redirects=True,
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
    ) as http:

        # Step 1: 申请上传链接
        await _emit(progress, "mineru_upload", "申请 MinerU 上传链接…")
        batch_id: str = ""
        file_url: str = ""
        try:
            resp = await http.post(
                f"{_BASE_URL}/file-urls/batch",
                headers=headers,
                json={
                    "files": [{"name": filename, "is_ocr": True, "data_id": filename}],
                    "model_version":  "vlm",
                    "enable_formula": True,
                    "enable_table":   True,
                    "language":       "en",
                    "extra_formats":  ["latex"],
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                msg = f"MinerU 申请上传失败: {data}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
            inner = data.get("data") or {}
            batch_id = inner.get("batch_id") or ""
            urls = inner.get("file_urls") or []
            if not batch_id or not urls:
                msg = f"MinerU step1 返回缺少 batch_id 或 file_urls: {data}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
            file_url = urls[0]
            if not isinstance(file_url, str) or not file_url.startswith("http"):
                msg = f"MinerU step1 无效上传 URL: {file_url!r}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
        except Exception as exc:
            msg = f"MinerU step1 failed: {exc}"
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
                    timeout=_UPLOAD_TIMEOUT,
                )
                put.raise_for_status()
                break
            except Exception as exc:
                last_put_exc = exc
                logger.warning("MinerU PUT attempt %d failed: %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                msg = f"MinerU 上传 PDF 失败（已重试）: {last_put_exc}"
                _record_error(last_error, msg)
                return None

        # Step 3: 轮询解析结果（先立即轮询一次，再按间隔等待）
        await _emit(progress, "mineru_parse", "MinerU vlm 解析中…")
        start = time.monotonic()
        zip_url: Optional[str] = None
        first_poll = True
        while time.monotonic() - start < _POLL_TIMEOUT:
            if not first_poll:
                await asyncio.sleep(_POLL_INTERVAL)
            first_poll = False
            try:
                r = await http.get(
                    f"{_BASE_URL}/extract-results/batch/{batch_id}",
                    headers=headers,
                    timeout=30.0,
                )
                r.raise_for_status()
                data = r.json()
                if data.get("code") != 0:
                    msg = f"MinerU poll error: {data}"
                    logger.warning(msg)
                    _record_error(last_error, msg)
                    return None
                results = (data.get("data") or {}).get("extract_result") or []
                if not results:
                    logger.warning("MinerU poll 暂无 extract_result，继续等待…")
                    continue
                item = results[0]
                state = item.get("state", "")
                elapsed = int(time.monotonic() - start)
                if state == "done":
                    zip_url = item.get("full_zip_url", "") or ""
                    if not zip_url:
                        msg = "MinerU 解析完成但缺少 full_zip_url"
                        logger.warning(msg)
                        _record_error(last_error, msg)
                        return None
                    await _emit(progress, "mineru_parse", f"解析完成（{elapsed}s）")
                    break
                if state == "failed":
                    err_msg = item.get("err_msg") or "unknown"
                    msg = f"MinerU 解析失败: {err_msg}"
                    logger.warning(msg)
                    _record_error(last_error, msg)
                    return None
                prog = item.get("extract_progress", {})
                pages = f" {prog.get('extracted_pages','?')}/{prog.get('total_pages','?')} 页" if prog else ""
                await _emit(progress, "mineru_parse", f"解析中…{pages}（{elapsed}s）")
            except Exception as exc:
                resp = getattr(exc, "response", None)
                status = getattr(resp, "status_code", None) if resp is not None else None
                logger.warning("MinerU poll exception (HTTP %s): %s", status, exc)
                # 单次失败不立即退出，继续轮询直到总超时
        else:
            msg = f"MinerU 解析超时（{int(_POLL_TIMEOUT)}s）"
            logger.warning(msg)
            _record_error(last_error, msg)
            return None

        # Step 4: 下载 zip，提取 Markdown
        await _emit(progress, "mineru_download", "下载解析结果包…")
        try:
            dl = await http.get(zip_url or "", timeout=_UPLOAD_TIMEOUT)
            dl.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(dl.content))
            md_name = next((n for n in z.namelist() if n.endswith("full.md")), None)
            if md_name is None:
                msg = f"MinerU zip 中未找到 full.md: {z.namelist()[:20]}"
                logger.warning(msg)
                _record_error(last_error, msg)
                return None
            raw_md = z.read(md_name).decode("utf-8", errors="replace")
        except Exception as exc:
            msg = f"MinerU 下载/解压失败: {exc}"
            logger.warning(msg)
            _record_error(last_error, msg)
            return None

        # Step 5: 后处理修复
        await _emit(progress, "mineru_fix", "应用后处理修复管道…")
        fixed = fix_all(raw_md)
        logger.info("MinerU 提取完成：%d → %d 字符", len(raw_md), len(fixed))
        return fixed


def get_mineru_chunks(markdown: str, max_chars: int = 4000) -> list[str]:
    """将 MinerU Markdown 切分为审查用的块列表。"""
    return split_markdown_into_chunks(markdown, max_chars=max_chars)
