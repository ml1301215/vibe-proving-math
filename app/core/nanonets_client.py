"""Nanonets Document Extraction API：PDF → Markdown（OCR-3 路径）。

策略：
  - 同步接口仅支持 ≤5 页；论文 PDF 普遍更长，因此 **默认走 async + 轮询**。
  - 仍使用与文档一致的 `extraction-api.nanonets.com` 服务，仅端点从 `/extract/sync`
    换为 `/extract/async` + `GET /extract/results/{record_id}`。

失败时返回结构化结果，由上层映射为 `parse_failed`，不做 MinerU / PyMuPDF 降级。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

NANONETS_BASE_URL = "https://extraction-api.nanonets.com"
EXTRACT_ASYNC_PATH = "/api/v1/extract/async"
RESULTS_PATH = "/api/v1/extract/results/{record_id}"


@dataclass
class NanonetsExtractResult:
    ok: bool
    markdown: str
    """解析出的 Markdown 正文（失败时为空字符串）。"""

    hierarchy: Optional[dict[str, Any]] = None
    """当请求 `markdown,json` 且 `json_options=hierarchy_output` 时可能存在的层级 JSON。"""

    error_code: str = ""
    """机器可读错误码：missing_api_key | http_error | job_failed | empty_markdown | timeout 等。"""

    error_message: str = ""
    """人类可读说明。"""

    record_id: str = ""
    raw_status: str = ""
    pages_processed: int = 0


def _markdown_from_body(body: dict[str, Any]) -> str:
    result = body.get("result") or {}
    md_block = result.get("markdown") or {}
    content = md_block.get("content", "")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _hierarchy_from_body(body: dict[str, Any]) -> Optional[dict[str, Any]]:
    result = body.get("result") or {}
    js = result.get("json") or {}
    content = js.get("content")
    if isinstance(content, dict):
        return content
    return None


async def extract_pdf_markdown_nanonets(
    pdf_bytes: bytes,
    *,
    api_key: str,
    filename: str = "document.pdf",
    httpx_timeout: float = 120.0,
    poll_interval: float = 2.0,
    max_poll_seconds: float = 900.0,
    include_hierarchy_json: bool = True,
) -> NanonetsExtractResult:
    """上传 PDF，异步提取 Markdown（可选 hierarchy JSON）。"""
    key = (api_key or "").strip()
    if not key:
        return NanonetsExtractResult(
            ok=False,
            markdown="",
            error_code="missing_api_key",
            error_message="未配置 Nanonets API Key（表单 nanonets_api_key / config.toml [nanonets].api_key）。",
        )

    headers = {"Authorization": f"Bearer {key}"}
    # markdown + json 以支持 hierarchy_output（见 Nanonets OpenAPI 说明）
    form: dict[str, Any] = {
        "output_format": "markdown,json" if include_hierarchy_json else "markdown",
    }
    if include_hierarchy_json:
        form["json_options"] = "hierarchy_output"

    timeout = httpx.Timeout(httpx_timeout, connect=30.0)
    async with httpx.AsyncClient(base_url=NANONETS_BASE_URL, timeout=timeout) as client:
        try:
            resp = await client.post(
                EXTRACT_ASYNC_PATH,
                headers=headers,
                data=form,
                files={"file": (filename, pdf_bytes, "application/pdf")},
            )
        except httpx.TimeoutException as exc:
            logger.warning("Nanonets async extract timeout: %s", exc)
            return NanonetsExtractResult(
                ok=False,
                markdown="",
                error_code="timeout",
                error_message=f"请求 Nanonets 超时: {exc}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Nanonets async extract request failed")
            return NanonetsExtractResult(
                ok=False,
                markdown="",
                error_code="request_error",
                error_message=f"{type(exc).__name__}: {exc}",
            )

        if resp.status_code not in (200, 202):
            detail = _safe_detail(resp)
            return NanonetsExtractResult(
                ok=False,
                markdown="",
                error_code="http_error",
                error_message=f"HTTP {resp.status_code}: {detail}",
            )

        try:
            body = resp.json()
        except Exception as exc:  # noqa: BLE001
            return NanonetsExtractResult(
                ok=False,
                markdown="",
                error_code="bad_response",
                error_message=f"无法解析 Nanonets JSON: {exc}; raw={resp.text[:500]!r}",
            )

        record_id = str(body.get("record_id") or "")
        if not record_id:
            return NanonetsExtractResult(
                ok=False,
                markdown="",
                error_code="no_record_id",
                error_message="Nanonets 响应缺少 record_id",
                raw_status=str(body.get("status") or ""),
            )

        # 若队列极快，async 响应里可能已带 completed 结果
        if body.get("success") and (body.get("status") == "completed"):
            md = _markdown_from_body(body).strip()
            if not md:
                return NanonetsExtractResult(
                    ok=False,
                    markdown="",
                    error_code="empty_markdown",
                    error_message="Nanonets 返回 completed 但 Markdown 为空",
                    record_id=record_id,
                    raw_status="completed",
                    pages_processed=int(body.get("pages_processed") or 0),
                )
            return NanonetsExtractResult(
                ok=True,
                markdown=_markdown_from_body(body),
                hierarchy=_hierarchy_from_body(body),
                record_id=record_id,
                raw_status="completed",
                pages_processed=int(body.get("pages_processed") or 0),
            )

        # 轮询结果（首次立即查询，之后按间隔休眠）
        elapsed = 0.0
        path = RESULTS_PATH.format(record_id=record_id)
        first_poll = True
        while elapsed <= max_poll_seconds:
            if not first_poll:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            first_poll = False
            try:
                r2 = await client.get(path, headers=headers, params={"include_content": "true"})
            except httpx.TimeoutException:
                continue
            if r2.status_code != 200:
                logger.debug("Nanonets poll HTTP %s: %s", r2.status_code, r2.text[:300])
                continue
            try:
                b2 = r2.json()
            except Exception:
                continue

            status = str(b2.get("status") or "").lower()
            message = str(b2.get("message") or "")
            # Results endpoint may return success=false while the async job is
            # still queued/processing. Only terminal failed states should abort.
            if status in ("processing", "queued", "pending", "running") or "still processing" in message.lower():
                continue

            if status == "failed" or b2.get("success") is False:
                msg = message or "Nanonets job failed"
                return NanonetsExtractResult(
                    ok=False,
                    markdown="",
                    error_code="job_failed",
                    error_message=msg,
                    record_id=record_id,
                    raw_status=status,
                )

            if status == "completed" and b2.get("success"):
                md = _markdown_from_body(b2).strip()
                if not md:
                    return NanonetsExtractResult(
                        ok=False,
                        markdown="",
                        error_code="empty_markdown",
                        error_message="解析完成但 Markdown 为空",
                        record_id=record_id,
                        raw_status=status,
                        pages_processed=int(b2.get("pages_processed") or 0),
                    )
                return NanonetsExtractResult(
                    ok=True,
                    markdown=_markdown_from_body(b2),
                    hierarchy=_hierarchy_from_body(b2),
                    record_id=record_id,
                    raw_status=status,
                    pages_processed=int(b2.get("pages_processed") or 0),
                )

        return NanonetsExtractResult(
            ok=False,
            markdown="",
            error_code="timeout",
            error_message=f"等待 Nanonets 结果超过 {max_poll_seconds:.0f}s（record_id={record_id}）",
            record_id=record_id,
            raw_status="polling_timeout",
        )


def _safe_detail(resp: httpx.Response) -> str:
    try:
        j = resp.json()
        if isinstance(j, dict) and "detail" in j:
            return str(j["detail"])[:800]
        return str(j)[:800]
    except Exception:
        return (resp.text or "")[:800]
