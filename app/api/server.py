"""vibe_proving FastAPI 主服务。

端点：
  POST /learn     学习模式（支持 SSE 流式）
  POST /solve     研究模式-问题解决（支持 SSE 流式）
  POST /review    研究模式-论文审查
  GET  /search    TheoremSearch 透传
  POST /projects  创建项目
  GET  /projects  列出项目
  GET  /health    健康检查

启动：
  cd app/
  uvicorn api.server:app --reload --port 8080
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Optional, AsyncIterator

# 确保 app/ 在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import llm_cfg, latrace_cfg, load_config
from core.logging_setup import setup_logging
from core.theorem_search import search_theorems as _ts_search, get_cache_stats as _ts_cache_stats
from core.memory import MemoryClient
from core.knowledge_base import extract_text_file

# 初始化日志（仅调用一次）
setup_logging()

import logging
logger = logging.getLogger("api.server")

app = FastAPI(
    title="vibe_proving API",
    description="数学工作者的推理伙伴 —— 开源、低成本、双模式",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 UI 静态文件：访问 http://localhost:8080/ui/
_ui_dir = Path(__file__).parent.parent / "ui"
if _ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir), html=True), name="ui")

# ── Pydantic 模型 ────────────────────────────────────────────────────────────

class LearnRequest(BaseModel):
    statement: str
    level: str = "undergraduate"  # "undergraduate" | "graduate"
    project_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    model: Optional[str] = None
    stream: bool = True


class SolveRequest(BaseModel):
    statement: str
    project_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    model: Optional[str] = None
    stream: bool = True


class ReviewRequest(BaseModel):
    proof_text: str = ""
    max_theorems: int = 8
    user_id: Optional[str] = "anonymous"
    lang: Optional[str] = None
    mode: str = "pipeline"
    images: Optional[list[str]] = None
    check_logic: bool = True  # 是否审查逻辑漏洞
    check_citations: bool = True  # 是否核查定理引用
    check_symbols: bool = True  # 是否检查符号一致性
    extended_thinking: bool = False  # Extended Thinking
    model: Optional[str] = None


class CreateProjectRequest(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    user_id: str = "anonymous"


class FormalizeRequest(BaseModel):
    statement: str
    lang: Optional[str] = "zh"
    model: Optional[str] = None
    max_iters: int = 4
    current_code: Optional[str] = None
    compile_error: Optional[str] = None
    skip_search: bool = False


class ErrorResponse(BaseModel):
    error: dict


def _normalize_image_payload(payload: str, *, default_mime: str = "image/png") -> str:
    raw = (payload or "").strip()
    if not raw:
        return ""
    if raw.startswith("data:image/"):
        return raw
    return f"data:{default_mime};base64,{raw}"


def _upload_to_data_url(content: bytes, content_type: str | None, filename: str = "") -> str:
    mime = content_type or "application/octet-stream"
    name = (filename or "").lower()
    if mime == "application/octet-stream":
        if name.endswith(".png"):
            mime = "image/png"
        elif name.endswith(".jpg") or name.endswith(".jpeg"):
            mime = "image/jpeg"
        elif name.endswith(".webp"):
            mime = "image/webp"
        elif name.endswith(".gif"):
            mime = "image/gif"
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{encoded}"


async def _run_review_stream(review_coro_factory, *, start_status: str):
    import base64 as _b64s
    import json as _js

    async def _gen():
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL_DONE = object()

        async def _on_progress(step: str, msg: str) -> None:
            await queue.put(("status", step, msg))

        async def _on_result(payload: dict) -> None:
            await queue.put(("result", "data", payload))

        async def _runner():
            try:
                report = await review_coro_factory(_on_progress, _on_result)
                await queue.put(("final", "report", report.summary_dict()))
            except ValueError as e:
                await queue.put(("error", "err", f"参数错误: {e}"))
            except Exception as e:  # noqa: BLE001
                logger.exception("paper review pipeline failed")
                await queue.put(("error", "err", f"{type(e).__name__}: {e}"))
            finally:
                await queue.put((SENTINEL_DONE, None, None))

        task = asyncio.create_task(_runner())
        yield start_status

        try:
            while True:
                kind, k2, payload = await queue.get()
                if kind is SENTINEL_DONE:
                    break
                if kind == "status":
                    yield f"<!--vp-status:{k2}|{payload}-->"
                elif kind == "result":
                    enc = _b64s.b64encode(
                        _js.dumps(payload, ensure_ascii=False).encode("utf-8")
                    ).decode("ascii")
                    yield f"<!--vp-result:{enc}-->"
                elif kind == "final":
                    enc = _b64s.b64encode(
                        _js.dumps(payload, ensure_ascii=False).encode("utf-8")
                    ).decode("ascii")
                    yield f"<!--vp-final:{enc}-->"
                elif kind == "error":
                    yield f"\n_审查失败：{payload}_\n"
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    return StreamingResponse(
        _sse_generator(_gen()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── SSE 辅助 ─────────────────────────────────────────────────────────────────

import re as _re_status
import base64 as _b64
# 同时识别 vp-status / vp-think / vp-result / vp-final；按出现顺序处理，避免乱序
_FRAME_RE = _re_status.compile(
    r"<!--vp-(status|think|result|final):([^>]*?)-->"
)


async def _sse_generator(async_gen: AsyncIterator[str]):
    """将 async generator 的输出包装为 SSE 格式。

    支持五类帧：
      - 正文：           data: {"chunk": "..."}
      - 状态指示：       data: {"status": "...", "step": "..."}
      - 思考链：         data: {"reasoning": "..."}（base64 解码后明文）
      - keepalive：      : keepalive 注释行（plan M.4，防止反向代理切断长连接）
      - 完成/错误：       data: [DONE] / data: {"error": "..."}

    plan M.4 改造：
      - 每个 yield 后立刻 `await asyncio.sleep(0)` 让出事件循环，确保 chunk 立即下发
      - 后台 keepalive 任务每 10s 推送一行 SSE 注释，防止 nginx/cloudflare 30s 断流
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=128)
    SENTINEL_DONE = object()
    SENTINEL_ERR  = object()
    err_holder: dict = {}

    async def _producer():
        try:
            async for chunk in async_gen:
                await queue.put(("data", chunk))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            err_holder["err"] = f"{type(e).__name__}: {e}"
            await queue.put((SENTINEL_ERR, None))
            return
        await queue.put((SENTINEL_DONE, None))

    prod_task = asyncio.create_task(_producer())

    async def _emit_frame(chunk: str):
        """把 pipeline yield 的一段拆分为正文/状态/思考链 SSE 帧。"""
        if not chunk:
            return
        last_end = 0
        for m in _FRAME_RE.finditer(chunk):
            pre = chunk[last_end:m.start()]
            if pre:
                yield f"data: {json.dumps({'chunk': pre}, ensure_ascii=False)}\n\n"
            kind, payload = m.group(1), m.group(2)
            if kind == "status":
                if "|" in payload:
                    step, msg = payload.split("|", 1)
                else:
                    step, msg = "info", payload
                yield f"data: {json.dumps({'status': msg, 'step': step}, ensure_ascii=False)}\n\n"
            elif kind == "think":
                try:
                    text = _b64.b64decode(payload.encode("ascii")).decode("utf-8", errors="replace")
                except Exception:
                    text = ""
                if text:
                    yield f"data: {json.dumps({'reasoning': text}, ensure_ascii=False)}\n\n"
            elif kind in ("result", "final"):
                # payload 是 base64(JSON)
                try:
                    decoded = _b64.b64decode(payload.encode("ascii")).decode("utf-8", errors="replace")
                    obj = json.loads(decoded)
                except Exception:
                    obj = None
                if obj is not None:
                    key = "result" if kind == "result" else "final"
                    yield f"data: {json.dumps({key: obj}, ensure_ascii=False)}\n\n"
            last_end = m.end()
        tail = chunk[last_end:] if last_end else chunk
        if tail:
            yield f"data: {json.dumps({'chunk': tail}, ensure_ascii=False)}\n\n"

    try:
        # 立即发一条 retry + keepalive，让浏览器尽快建立 SSE 通道
        yield "retry: 5000\n\n"
        await asyncio.sleep(0)
        yield ": connected\n\n"

        last_activity = asyncio.get_event_loop().time()
        KEEPALIVE_INTERVAL = 10.0

        while True:
            try:
                kind, chunk = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
            except asyncio.TimeoutError:
                # 心跳：注释行（: 开头）SSE 标准支持，浏览器忽略，但可冲洗代理缓冲
                yield ": keepalive\n\n"
                await asyncio.sleep(0)
                continue

            if kind is SENTINEL_DONE:
                break
            if kind is SENTINEL_ERR:
                err = json.dumps({"error": err_holder.get("err", "unknown")}, ensure_ascii=False)
                yield f"data: {err}\n\n"
                await asyncio.sleep(0)
                break

            async for frame in _emit_frame(chunk):
                yield frame
                await asyncio.sleep(0)  # 让出事件循环，确保立刻 flush
            last_activity = asyncio.get_event_loop().time()
    except asyncio.CancelledError:
        prod_task.cancel()
        raise
    except Exception as e:
        err = json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
        yield f"data: {err}\n\n"
    finally:
        if not prod_task.done():
            prod_task.cancel()
            try:
                await prod_task
            except (asyncio.CancelledError, Exception):
                pass
        yield "data: [DONE]\n\n"


# ── 端点：/learn ─────────────────────────────────────────────────────────────

@app.post("/learn")
async def learn(req: LearnRequest):
    """学习模式：为数学命题生成教学性证明讲解。支持 SSE 流式。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    if len(req.statement) > 10000:
        raise HTTPException(status_code=422, detail="statement 超过最大长度限制（10000字符）")

    from modes.learning.pipeline import stream_learning_pipeline, run_learning_pipeline

    if req.stream:
        async def _gen():
            # 记忆：检索历史（若 LATRACE 可用）
            mem_client = MemoryClient(user_id=req.user_id or "anonymous")
            memories = await mem_client.retrieve(req.project_id or "default", req.statement)
            if memories:
                mem_text = mem_client.format_memories_for_prompt(memories)
                yield f"<!-- memory_retrieved: {len(memories)} items -->"

            async for chunk in stream_learning_pipeline(
                req.statement,
                level=req.level,
                model=req.model,
            ):
                yield chunk

            # 记忆：异步写入
            asyncio.create_task(
                mem_client.ingest(req.project_id or "default", [
                    {"role": "user", "text": f"学习模式: {req.statement}"},
                    {"role": "assistant", "text": f"[学习模式输出已完成]"},
                ])
            )

        return StreamingResponse(
            _sse_generator(_gen()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        result = await run_learning_pipeline(
            req.statement,
            level=req.level,
            model=req.model,
        )
        return {"markdown": result.to_markdown(), "has_all_sections": result.has_required_sections()}


# ── 端点：/solve ──────────────────────────────────────────────────────────────

@app.post("/solve")
async def solve(req: SolveRequest):
    """研究模式-问题解决：GVR 证明 pipeline。支持 SSE 流式。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    if len(req.statement) > 10000:
        raise HTTPException(status_code=422, detail="statement 超过最大长度限制（10000字符）")

    from modes.research.solver import solve as _solve

    if req.stream:
        async def _gen():
            import asyncio as _asyncio

            # 状态帧通过 Queue 异步推送（纯 status，不含 reasoning）
            status_queue: _asyncio.Queue = _asyncio.Queue()

            async def _on_progress(step: str, message: str) -> None:
                await status_queue.put((step, message))

            yield "<!--vp-status:start|启动求解 pipeline…-->"

            solve_task = _asyncio.create_task(
                _solve(req.statement, model=req.model, progress=_on_progress)
            )

            # 消费 status 队列，直到 solve_task 完成
            while not (solve_task.done() and status_queue.empty()):
                try:
                    step, msg = await _asyncio.wait_for(status_queue.get(), timeout=0.5)
                    yield f"<!--vp-status:{step}|{msg}-->"
                except _asyncio.TimeoutError:
                    if solve_task.done() and status_queue.empty():
                        break

            # ── 结果落地 ─────────────────────────────────────────────────────
            try:
                result = solve_task.result()
            except Exception as e:
                logger.exception("solve failed: %s", e)
                yield f"\n_证明流程失败：{type(e).__name__}_\n"
                return

            yield "<!--vp-status:done|证明流程完成-->"
            yield result.blueprint
            yield f"\n\n---\n\n置信度: {result.confidence:.0%} ｜ 判定: {result.verdict}\n"
            yield "\n## 引用核查\n"
            if result.references:
                for ref in result.references[:5]:
                    status_icon = "✓" if ref["status"] == "verified" else "✗"
                    yield f"- {status_icon} {ref['name'][:60]} ({ref['status']})\n"
            else:
                yield "- ✗ （未能核查到任何外部引用）(unverified)\n"
            if result.obstacles:
                yield "\n## 已知障碍\n"
                for obs in result.obstacles:
                    yield f"- {obs}\n"
            yield "<!--vp-status:done|完成-->"

        return StreamingResponse(
            _sse_generator(_gen()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        result = await _solve(req.statement, model=req.model)
        return result.to_dict()


# ── 端点：/review ──────────────────────────────────────────────────────────────

@app.post("/review")
async def review(req: ReviewRequest):
    """研究模式-论文审查：接收文本或图片，生成结构化审查报告。

    自动判别：
      - 文本含 \\begin{theorem}/\\begin{proof} → 多定理拆解审查
      - LLM 兜底解析仍失败 → 单证明降级，整段文本视为一段证明
    """
    text_input = (req.proof_text or "").strip()
    image_inputs = [_normalize_image_payload(img) for img in (req.images or []) if img]
    if not text_input and not image_inputs:
        raise HTTPException(status_code=422, detail="proof_text 或 images 至少提供一个")
    if text_input and len(text_input) > 50_000:
        raise HTTPException(
            status_code=422,
            detail="proof_text 超过最大长度限制（50000 字符）",
        )

    from modes.research.reviewer import review_text, review_paper_images

    try:
        if image_inputs and not text_input:
            report = await review_paper_images(
                image_inputs,
                source="image_upload",
                max_theorems=req.max_theorems,
                check_logic=req.check_logic,
                check_citations=req.check_citations,
                check_symbols=req.check_symbols,
                model=req.model,
                lang=req.lang or "zh",
            )
        else:
            report = await review_text(
                text_input,
                source="inline",
                max_theorems=req.max_theorems,
                check_logic=req.check_logic,
                check_citations=req.check_citations,
                check_symbols=req.check_symbols,
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("paper review failed")
        raise HTTPException(status_code=502, detail=f"论文审查失败: {str(e)[:200]}")

    return report.to_dict()


# ── 端点：/review_stream ──────────────────────────────────────────────────────

@app.post("/review_stream")
async def review_stream(req: ReviewRequest):
    """研究模式-论文审查（SSE 流式）：文本/图片输入的逐条命题审查。

    功能：
      - 逐步审查证明中的逻辑漏洞（gap、critical_error）
      - 核查引用的定理（通过 TheoremSearch）
      - 检测符号一致性与证明完备性

    SSE 帧（前端可解析的 `data:` JSON）：
      - {"status": "...", "step": "..."}     阶段进度
      - {"result": {"kind":"theorem","index":N,"data":{...}}}  单定理审查结果
      - {"final":  {...}}      最终汇总
      - "[DONE]"               结束哨兵
    """
    text_input = (req.proof_text or "").strip()
    image_inputs = [_normalize_image_payload(img) for img in (req.images or []) if img]
    if not text_input and not image_inputs:
        raise HTTPException(status_code=422, detail="proof_text 或 images 至少提供一个")
    if text_input and len(text_input) > 50_000:
        raise HTTPException(
            status_code=422,
            detail="proof_text 超过最大长度限制（50000 字符）",
        )

    from modes.research.reviewer import review_text as _review_text, review_paper_images

    async def _factory(_on_progress, _on_result):
        if image_inputs and not text_input:
            return await review_paper_images(
                image_inputs,
                source="image_upload",
                max_theorems=req.max_theorems,
                progress=_on_progress,
                result_cb=_on_result,
                check_logic=req.check_logic,
                check_citations=req.check_citations,
                check_symbols=req.check_symbols,
                model=req.model,
                lang=req.lang or "zh",
            )
        return await _review_text(
            text_input,
            source="inline",
            max_theorems=req.max_theorems,
            progress=_on_progress,
            result_cb=_on_result,
            check_logic=req.check_logic,
            check_citations=req.check_citations,
            check_symbols=req.check_symbols,
        )

    return await _run_review_stream(
        _factory,
        start_status="<!--vp-status:start|启动论文审查 pipeline…-->",
    )


@app.post("/review_pdf_stream")
async def review_pdf_stream(
    file: UploadFile = File(...),
    max_theorems: int = Form(8),
    user_id: str = Form("anonymous"),
    lang: Optional[str] = Form(None),
    mode: str = Form("pipeline"),
    check_logic: bool = Form(True),
    check_citations: bool = Form(True),
    check_symbols: bool = Form(True),
    model: Optional[str] = Form(None),
    mineru_token: Optional[str] = Form(None),
    nanonets_api_key: Optional[str] = Form(None),
):
    """论文上传审查（SSE）：支持 PDF / 图片 / tex / txt / md。

    PDF：**仅** Nanonets OCR（异步提取 Markdown）→ 大章节切分 → LLM 结构化章节审查。
    不再使用 agent/docling、MinerU、PyMuPDF 作为 PDF 解析路径；解析失败返回 ``parse_failed``，无降级。

    ``max_theorems`` / ``check_*`` / ``mode`` / ``mineru_token`` 对 PDF 路径保留为兼容字段，当前不驱动 PDF 主流程。
    """
    filename = file.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件不能为空")

    text_exts = {".tex", ".txt", ".md", ".mmd"}
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    content_type = (file.content_type or "").lower()

    from modes.research.reviewer import review_text, review_paper_images
    from modes.research.section_reviewer import run_pdf_nanonets_section_review

    import os as _os

    def _resolve_nanonets_key() -> str:
        k = (nanonets_api_key or "").strip()
        if k:
            return k
        k = (str(_os.environ.get("NANONETS_API_KEY") or "")).strip()
        if k:
            return k
        _cfg_n = load_config().get("nanonets")
        if isinstance(_cfg_n, dict):
            return str(_cfg_n.get("api_key", "")).strip()
        return ""

    async def _factory(_on_progress, _on_result):
        if suffix == ".pdf" or content_type == "application/pdf":
            return await run_pdf_nanonets_section_review(
                content,
                source=filename,
                nanonets_api_key=_resolve_nanonets_key(),
                progress=_on_progress,
                result_cb=_on_result,
                model=model,
                lang=lang or "zh",
            )

        if suffix in image_exts or content_type.startswith("image/"):
            image_payload = _upload_to_data_url(content, content_type, filename)
            return await review_paper_images(
                [image_payload],
                source=filename,
                max_theorems=max_theorems,
                progress=_on_progress,
                result_cb=_on_result,
                check_logic=check_logic,
                check_citations=check_citations,
                check_symbols=check_symbols,
                model=model,
                lang=lang or "zh",
            )
        if suffix in text_exts:
            text = extract_text_file(content, filename)
            if not text:
                raise ValueError("无法解析上传文本")
            return await review_text(
                text,
                source=filename,
                max_theorems=max_theorems,
                progress=_on_progress,
                result_cb=_on_result,
                check_logic=check_logic,
                check_citations=check_citations,
                check_symbols=check_symbols,
            )
        raise HTTPException(status_code=415, detail="仅支持 .pdf / .tex / .txt / .md / .mmd / 图片")

    return await _run_review_stream(
        _factory,
        start_status="<!--vp-status:start|启动论文上传审查…-->",
    )


# ── 端点：/formalize ──────────────────────────────────────────────────────────

@app.post("/formalize")
async def formalize(req: FormalizeRequest):
    """形式化证明（Beta）：将自然语言数学命题形式化为 Lean 4 代码。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")

    from modes.formalization.pipeline import formalize_stream

    gen = formalize_stream(
        statement=req.statement.strip(),
        lang=req.lang or "zh",
        model=req.model,
        max_iters=req.max_iters,
        current_code=req.current_code,
        compile_error=req.compile_error,
        skip_search=req.skip_search,
    )
    return StreamingResponse(
        _sse_generator(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 端点：/search ──────────────────────────────────────────────────────────────

@app.get("/search")
async def search(
    q: str = Query(..., description="搜索查询词"),
    top_k: int = Query(10, ge=1, le=50, description="返回条数"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="最低相似度"),
):
    """TheoremSearch 透传端点：直接搜索 Lean 4 定理库。"""
    from skills.search_theorems import search_theorems

    try:
        results = await search_theorems(q, top_k=top_k, min_sim=min_similarity)
        return {
            "query": q,
            "count": len(results),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TheoremSearch 查询失败: {e}")


# ── 端点：/projects ────────────────────────────────────────────────────────────

_projects_store: dict[str, dict] = {}  # MVP 阶段内存存储，生产环境替换为持久化


@app.post("/projects")
async def create_project(req: CreateProjectRequest):
    """创建书本项目（学习/研究记忆的隔离单元）。"""
    key = f"{req.user_id}:{req.project_id}"
    _projects_store[key] = {
        "project_id": req.project_id,
        "name": req.name,
        "description": req.description,
        "user_id": req.user_id,
        "memory_domain": f"project/{req.project_id}",
    }
    return {"status": "created", "project": _projects_store[key]}


@app.get("/projects")
async def list_projects(user_id: str = Query("anonymous")):
    """列出指定用户的所有项目。"""
    user_projects = [v for k, v in _projects_store.items() if v["user_id"] == user_id]
    return {"user_id": user_id, "projects": user_projects}


# ── 端点：/health ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """服务健康检查，包含 LATRACE、TheoremSearch、Kimina 状态和缓存统计。"""
    import datetime as _dt
    from core.theorem_search import _get_http_client
    from core.config import ts_cfg
    from modes.research.agent.tools import check_agent_tool_health
    from modes.formalization.verifier import check_kimina_health

    cfg = llm_cfg()

    # ── 并发检查 LATRACE 与 TheoremSearch ────────────────────────────
    async def _check_latrace() -> tuple[str, dict]:
        try:
            mem = MemoryClient()
            h = await asyncio.wait_for(mem.health(), timeout=6)
            status = h.get("status", "unknown")
            detail = {k: v for k, v in h.get("dependencies", {}).items()}
            return status, detail
        except asyncio.TimeoutError:
            logger.debug("health: LATRACE check timed out")
            return "timeout", {}
        except Exception as exc:
            logger.debug("health: LATRACE check failed: %s", exc)
            return "unavailable", {}

    async def _check_ts() -> str:
        # 如果缓存里已有条目，说明近期调用成功过 → 直接报 ok
        stats = _ts_cache_stats()
        if stats.get("size", 0) > 0:
            return "ok"
        try:
            ts_base = ts_cfg()["base_url"]
            r = await asyncio.wait_for(
                _get_http_client().get(ts_base, timeout=8),
                timeout=9,
            )
            return "ok" if r.status_code < 500 else f"error:{r.status_code}"
        except asyncio.TimeoutError:
            logger.debug("health: TheoremSearch ping timed out (service may still be usable)")
            return "timeout"
        except Exception as exc:
            logger.debug("health: TheoremSearch check failed: %s", exc)
            return "unreachable"

    (latrace_status, latrace_detail), ts_status, kimina_status, paper_review_agent = await asyncio.gather(
        _check_latrace(), _check_ts(), check_kimina_health(), check_agent_tool_health()
    )

    ts_cache = _ts_cache_stats()

    # overall 只由 LATRACE 决定（TheoremSearch 慢/超时不影响系统可用性）
    # "unavailable" / "timeout" = 完全连不上 = degraded
    # "fail" / "http_5xx" 等 = 可达但内部失败 = degraded（记忆功能受损）
    # "ok" / "pass" / "healthy" = 正常
    if latrace_status in ("unavailable", "timeout"):
        overall = "degraded"
    elif latrace_status not in ("ok", "pass", "healthy"):
        overall = "degraded"
    else:
        overall = "ok"

    result: dict = {
        "status": overall,
        "version": "0.1.0",
        "timestamp": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "llm": {
            "base_url": cfg["base_url"],
            "model": cfg["model"],
        },
        "dependencies": {
            "latrace": {
                "status": latrace_status,
                **({"dependencies": latrace_detail} if latrace_detail else {}),
            },
            "theorem_search": {
                "status": ts_status,
                "cache": ts_cache,
            },
            "kimina": kimina_status,
            "paper_review_agent": paper_review_agent,
        },
    }
    return result


# ── 错误处理 ──────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": str(exc)}},
    )
