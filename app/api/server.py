"""vibe_proving FastAPI 主服务。

端点：
  POST /learn     学习模式（支持 SSE 流式）
  POST /learn/section  学习模式单卡重生成
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
import time
from pathlib import Path
from typing import Optional, AsyncIterator

# 确保 app/ 在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Request, Response, Depends
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.config import clear_config_cache, config_path, llm_cfg, load_config, update_config_file
from core.logging_setup import setup_logging
from core.theorem_search import search_theorems as _ts_search, get_cache_stats as _ts_cache_stats
from core.knowledge_base import extract_text_file
from core.user_store import (
    create_session,
    create_user,
    delete_session,
    get_settings,
    get_user_by_session,
    update_settings,
    consume_quota,
    add_chat_session,
    list_chat_sessions,
    delete_chat_session,
    clear_chat_sessions,
    authenticate_user,
)

# 运行时可热更新的配置覆盖（由 POST /config/llm 和 /config/nanonets 写入）
_runtime_config_overrides: dict = {}

# 初始化日志（仅调用一次）
try:
    _startup_config = load_config()
except FileNotFoundError:
    _startup_config = {}
setup_logging(level=(_startup_config.get("app") or {}).get("log_level", "INFO"))

import logging
logger = logging.getLogger("api.server")


def _configured(value: object) -> str:
    return "yes" if str(value or "").strip() else "no"


def _log_startup_summary(cfg: dict) -> None:
    llm = cfg.get("llm") or {}
    auth = cfg.get("auth") or {}
    theorem_search = cfg.get("theorem_search") or {}
    nanonets = cfg.get("nanonets") or {}
    mineru = cfg.get("mineru") or {}
    aristotle = cfg.get("aristotle") or {}
    logger.info(
        "Startup config: config=%s, llm_model=%s, llm_base=%s, llm_key=%s, superuser=%s, quota_default=%s",
        config_path(),
        llm.get("model") or "",
        llm.get("base_url") or "",
        _configured(llm.get("api_key")),
        auth.get("superuser_username") or "dev_user",
        auth.get("default_quota", 50),
    )
    logger.info(
        "External services: theorem_search=%s, nanonets_key=%s, mineru_base=%s, aristotle_key=%s",
        theorem_search.get("base_url") or "",
        _configured(nanonets.get("api_key")),
        mineru.get("base_url") or "",
        _configured(aristotle.get("api_key")),
    )


_log_startup_summary(_startup_config)


async def _ingest_memory_best_effort(user_id: str, project_id: str, turns: list[dict]) -> None:
    """Run LATRACE ingest outside the response path and always close its client."""
    try:
        from core.config import latrace_enabled
        if not latrace_enabled():
            return
        from core.memory import MemoryClient
        mem_client = MemoryClient(user_id=user_id or "anonymous")
    except Exception as exc:
        logger.debug("memory ingest disabled/skipped: %s", exc)
        return
    try:
        await asyncio.wait_for(mem_client.ingest(project_id or "default", turns), timeout=2.0)
    except Exception as exc:
        logger.debug("memory ingest skipped: %s", exc)
    finally:
        try:
            await mem_client.aclose()
        except Exception:
            pass

app = FastAPI(
    title="vibe_proving API",
    description="数学工作者的推理伙伴 —— 开源、低成本、双模式",
    version="0.1.0",
)

_AUTH_COOKIE = "vp_session"
_PROTECTED_PATH_PREFIXES = (
    "/learn",
    "/solve",
    "/review",
    "/search",
    "/projects",
    "/config",
    "/history",
    "/sessions",
    "/user",
)
_PUBLIC_PATH_PREFIXES = (
    "/auth",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/ui",
    "/static",
    "/favicon",
    "/assets",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_public_user(user: dict) -> dict:
    quota_unlimited = bool(user.get("is_admin", False))
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "quota_limit": user["quota_limit"],
        "quota_used": user["quota_used"],
        "quota_remaining": user["quota_remaining"],
        "quota_unlimited": quota_unlimited,
        "is_admin": quota_unlimited,
    }


def _request_user(request: Request) -> Optional[dict]:
    cached = getattr(request.state, "user", None)
    if cached:
        return cached
    token = request.cookies.get(_AUTH_COOKIE, "")
    user = get_user_by_session(token)
    if user:
        request.state.user = user
    return user


def current_user(request: Request) -> dict:
    user = _request_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_quota(user: dict) -> dict:
    if user.get("is_admin"):
        return user
    try:
        updated = consume_quota(int(user["id"]), 1)
        user.update(updated)
        return user
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="对话次数已用完，请联系管理员") from exc
    except Exception as exc:
        raise HTTPException(status_code=403, detail="用户不可用") from exc


def _apply_user_llm_context(user: dict):
    import core.llm as _llm_mod
    return _llm_mod.set_request_config(_effective_llm_cfg(user))


def _reset_user_llm_context(token) -> None:
    import core.llm as _llm_mod
    _llm_mod.reset_request_config(token)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/" or any(path.startswith(prefix) for prefix in _PUBLIC_PATH_PREFIXES):
        return await call_next(request)
    if any(path.startswith(prefix) for prefix in _PROTECTED_PATH_PREFIXES):
        if not _request_user(request):
            return JSONResponse(status_code=401, content={"detail": "请先登录"})
    return await call_next(request)


_LOGGED_PATH_PREFIXES = (
    "/learn",
    "/solve",
    "/review",
    "/formalize",
    "/search",
    "/config",
    "/history",
    "/projects",
    "/auth/login",
    "/auth/register",
    "/auth/logout",
)


def _should_log_request(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _LOGGED_PATH_PREFIXES)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "-"


def _request_user_label(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        return "anonymous"
    username = user.get("username") or user.get("id") or "unknown"
    role = "admin" if user.get("is_admin") else "user"
    return f"{username}({role})"


def _user_label(user: dict | None) -> str:
    if not user:
        return "anonymous"
    username = user.get("username") or user.get("id") or "unknown"
    role = "admin" if user.get("is_admin") else "user"
    return f"{username}({role})"


def _quota_label(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        return "-"
    if user.get("is_admin"):
        return "unlimited"
    remaining = user.get("quota_remaining")
    limit = user.get("quota_limit")
    return f"{remaining}/{limit}"


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    path = request.url.path
    log_this = _should_log_request(path)
    started = time.perf_counter()
    if log_this:
        if not getattr(request.state, "user", None) and not path.startswith("/auth/"):
            _request_user(request)
        logger.info(
            "Request start: %s %s user=%s client=%s",
            request.method,
            path,
            _request_user_label(request),
            _client_ip(request),
        )
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if log_this:
            logger.exception(
                "Request failed: %s %s user=%s elapsed_ms=%d",
                request.method,
                path,
                _request_user_label(request),
                elapsed_ms,
            )
        raise
    if log_this:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Request done: %s %s status=%d elapsed_ms=%d quota=%s",
            request.method,
            path,
            response.status_code,
            elapsed_ms,
            _quota_label(request),
        )
    return response

# 挂载 UI 静态文件：访问 http://localhost:8080/ui/
_ui_dir = Path(__file__).parent.parent / "ui"
if _ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def _root_redirect_to_ui():
        return RedirectResponse(url="/ui/", status_code=307)

# ── Pydantic 模型 ────────────────────────────────────────────────────────────

class LearnRequest(BaseModel):
    statement: str
    level: str = "undergraduate"  # "undergraduate" | "graduate"
    project_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    model: Optional[str] = None
    stream: bool = True
    lang: Optional[str] = None


class LearnSectionRequest(BaseModel):
    """单卡重生成：background | prereq | proof | examples"""

    statement: str
    section: str
    level: str = "undergraduate"
    model: Optional[str] = None
    lang: Optional[str] = None


class SolveRequest(BaseModel):
    statement: str
    project_id: Optional[str] = "default"
    user_id: Optional[str] = "anonymous"
    model: Optional[str] = None
    stream: bool = True
    lang: Optional[str] = None
    text_attachments: Optional[list[str]] = None


class SolveLatexRequest(BaseModel):
    blueprint: str
    statement: str = ""
    model: Optional[str] = None


class ReviewRequest(BaseModel):
    proof_text: str = ""
    max_theorems: int = Field(default=8, ge=1, le=50)
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
    # aristotle: Harmonic Aristotle API；pipeline: 本地 LLM + 验证
    mode: Optional[str] = "aristotle"


class ErrorResponse(BaseModel):
    error: dict


class AuthRequest(BaseModel):
    username: str
    password: str


class SaveSessionRequest(BaseModel):
    title: str = "chat"
    mode: str = "learning"
    messages: list[dict] = Field(default_factory=list)


# ── 端点：/auth / /history ───────────────────────────────────────────────────

@app.get("/auth/me")
async def auth_me(request: Request):
    user = _request_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    can_configure_api = bool(user.get("is_admin"))
    return {
        "user": _safe_public_user(user),
        "auth": {
            "allow_register": bool((load_config().get("auth", {}) or {}).get("allow_register", True)),
            "can_configure_api": can_configure_api,
        },
    }


@app.post("/auth/login")
async def auth_login(req: AuthRequest, response: Response, request: Request):
    user = authenticate_user(req.username, req.password)
    if not user:
        logger.info("Auth login failed: username=%s client=%s", req.username, _client_ip(request))
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token, expires = create_session(int(user["id"]))
    response.set_cookie(
        _AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=bool((load_config().get("auth", {}) or {}).get("cookie_secure", False)),
        max_age=max(1, expires - int(time.time())),
        path="/",
    )
    logger.info("Auth login succeeded: user=%s client=%s", _user_label(user), _client_ip(request))
    return {"user": _safe_public_user(user)}


@app.post("/auth/register")
async def auth_register(req: AuthRequest, response: Response, request: Request):
    cfg = load_config().get("auth", {}) or {}
    if not bool(cfg.get("allow_register", True)):
        logger.info("Auth register blocked: username=%s client=%s", req.username, _client_ip(request))
        raise HTTPException(status_code=403, detail="注册已关闭")
    try:
        user = create_user(req.username, req.password)
    except ValueError as exc:
        logger.info("Auth register failed: username=%s client=%s detail=%s", req.username, _client_ip(request), exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    token, expires = create_session(int(user["id"]))
    response.set_cookie(
        _AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=bool((load_config().get("auth", {}) or {}).get("cookie_secure", False)),
        max_age=max(1, expires - int(time.time())),
        path="/",
    )
    logger.info("Auth register succeeded: user=%s client=%s", _user_label(user), _client_ip(request))
    return {"user": _safe_public_user(user)}


@app.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    user = _request_user(request)
    delete_session(request.cookies.get(_AUTH_COOKIE, ""))
    response.delete_cookie(_AUTH_COOKIE, path="/")
    logger.info("Auth logout: user=%s client=%s", _user_label(user), _client_ip(request))
    return {"ok": True}


@app.get("/history")
async def history_list(user: dict = Depends(current_user)):
    return {"sessions": list_chat_sessions(int(user["id"]), limit=50)}


@app.post("/history")
async def history_add(req: SaveSessionRequest, user: dict = Depends(current_user)):
    session = add_chat_session(int(user["id"]), req.title, req.mode, req.messages)
    return {"session": session}


@app.delete("/history/{session_id}")
async def history_delete(session_id: int, user: dict = Depends(current_user)):
    delete_chat_session(int(user["id"]), session_id)
    return {"ok": True}


@app.delete("/history")
async def history_clear(user: dict = Depends(current_user)):
    clear_chat_sessions(int(user["id"]))
    return {"ok": True}


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
            # 清理特殊字符避免截断HTML注释帧
            safe_msg = str(msg).replace('>', ' ').replace('-->', ' ').replace('\n', ' ') if msg else msg
            await queue.put(("status", step, safe_msg))

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
                    # 再次确保payload不含特殊字符（双重保护）
                    safe_payload = str(payload).replace('>', ' ').replace('-->', ' ').replace('\n', ' ') if payload else payload
                    yield f"<!--vp-status:{k2}|{safe_payload}-->"
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
                    # 使用 vp-status 帧传递错误，_sse_generator 会将其转为
                    # {"status": msg, "step": "error"}，前端识别后抛出异常
                    # 清理 > 和 -- 避免截断 HTML 注释帧
                    safe_err = str(payload).replace('>', ' ').replace('-->', '').replace('\n', ' ')
                    yield f"<!--vp-status:error|{safe_err}-->"
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
    r"<!--vp-(status|think|result|final|section-error):([^>]*?)-->"
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
    started = time.perf_counter()
    data_chunks = 0
    keepalives = 0
    terminal_logged = False

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
        nonlocal data_chunks
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
            elif kind == "section-error":
                if "|" in payload:
                    sid, msg = payload.split("|", 1)
                else:
                    sid, msg = "unknown", payload
                yield (
                    "data: "
                    + json.dumps(
                        {"section_error": {"id": sid.strip(), "message": msg.strip()}},
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
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
                keepalives += 1
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
                data_chunks += 1
                yield frame
                await asyncio.sleep(0)  # 让出事件循环，确保立刻 flush
            last_activity = asyncio.get_event_loop().time()
    except asyncio.CancelledError:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "SSE stream cancelled: elapsed_ms=%d frames=%d keepalives=%d",
            elapsed_ms,
            data_chunks,
            keepalives,
        )
        terminal_logged = True
        prod_task.cancel()
        raise
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("SSE stream failed: elapsed_ms=%d frames=%d", elapsed_ms, data_chunks)
        terminal_logged = True
        err = json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
        yield f"data: {err}\n\n"
    finally:
        if not prod_task.done():
            prod_task.cancel()
            try:
                await prod_task
            except (asyncio.CancelledError, Exception):
                pass
        if not terminal_logged:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "SSE stream finished: elapsed_ms=%d frames=%d keepalives=%d",
                elapsed_ms,
                data_chunks,
                keepalives,
            )
        yield "data: [DONE]\n\n"


# ── 端点：/learn ─────────────────────────────────────────────────────────────

@app.post("/learn")
async def learn(req: LearnRequest, user: dict = Depends(current_user)):
    """学习模式：为数学命题生成教学性证明讲解。支持 SSE 流式。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    if len(req.statement) > 10000:
        raise HTTPException(status_code=422, detail="statement 超过最大长度限制（10000字符）")
    user = require_quota(user)
    req.user_id = str(user["id"])

    from modes.learning.pipeline import stream_learning_pipeline, run_learning_pipeline

    if req.stream:
        async def _gen():
            llm_token = _apply_user_llm_context(user)
            try:
                # 记忆：检索历史（若 LATRACE 可用，静默降级）
                mem_client = None
                kb_text = None
                try:
                    from core.config import latrace_enabled
                    if latrace_enabled():
                        from core.memory import MemoryClient
                        mem_client = MemoryClient(user_id=req.user_id or "anonymous")
                        memories = await asyncio.wait_for(
                            mem_client.retrieve(req.project_id or "default", req.statement),
                            timeout=2.0,
                        )
                        if memories:
                            kb_text = mem_client.format_memories_for_prompt(memories)
                            yield f"<!-- memory_retrieved: {len(memories)} items -->"
                except Exception as exc:
                    logger.debug("learn: memory retrieve skipped (LATRACE unavailable)")
                finally:
                    if mem_client is not None:
                        try:
                            await mem_client.aclose()
                        except Exception:
                            pass

                async for chunk in stream_learning_pipeline(
                    req.statement,
                    level=req.level,
                    model=req.model,
                    kb_context=kb_text,
                    lang=req.lang,
                ):
                    yield chunk

                # 记忆：异步写入（静默降级）
                asyncio.create_task(_ingest_memory_best_effort(
                    req.user_id or "anonymous",
                    req.project_id or "default",
                    [
                        {"role": "user", "text": f"学习模式: {req.statement}"},
                        {"role": "assistant", "text": f"[学习模式输出已完成]"},
                    ],
                ))
            finally:
                _reset_user_llm_context(llm_token)

        return StreamingResponse(
            _sse_generator(_gen()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        llm_token = _apply_user_llm_context(user)
        try:
            result = await run_learning_pipeline(
                req.statement,
                level=req.level,
                model=req.model,
                lang=req.lang,
            )
        finally:
            _reset_user_llm_context(llm_token)
        return {"markdown": result.to_markdown(), "has_all_sections": result.has_required_sections()}


@app.post("/learn/section")
async def learn_section(req: LearnSectionRequest, user: dict = Depends(current_user)):
    """学习模式单卡重生成，SSE 流式，仅返回该 section 的 Markdown 片段。"""
    from modes.learning.pipeline import SECTION_IDS, stream_learning_section

    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    if len(req.statement) > 10000:
        raise HTTPException(status_code=422, detail="statement 超过最大长度限制（10000字符）")
    sid = (req.section or "").strip().lower()
    if sid not in SECTION_IDS:
        raise HTTPException(
            status_code=422,
            detail=f"section 必须是其一：{', '.join(sorted(SECTION_IDS))}",
        )
    user = require_quota(user)

    async def _gen():
        async for chunk in stream_learning_section(
            sid,
            req.statement,
            level=req.level,
            model=req.model,
            lang=req.lang,
        ):
            yield chunk

    return StreamingResponse(
        _sse_generator(_gen()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 端点：/solve ──────────────────────────────────────────────────────────────

@app.post("/solve")
async def solve(req: SolveRequest, user: dict = Depends(current_user)):
    """研究模式-问题解决：GVR 证明 pipeline。支持 SSE 流式。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    if len(req.statement) > 10000:
        raise HTTPException(status_code=422, detail="statement 超过最大长度限制（10000字符）")
    user = require_quota(user)
    req.user_id = str(user["id"])

    from modes.research.solver import solve as _solve

    extra_ctx = "\n\n".join(req.text_attachments or [])

    if req.stream:
        async def _gen():
            import asyncio as _asyncio
            llm_token = _apply_user_llm_context(user)
            try:
                # 状态帧通过 Queue 异步推送（纯 status，不含 reasoning）
                status_queue: _asyncio.Queue = _asyncio.Queue()

                async def _on_progress(step: str, message: str) -> None:
                    # 清理特殊字符避免截断HTML注释帧
                    safe_message = str(message).replace('>', ' ').replace('-->', ' ').replace('\n', ' ') if message else message
                    await status_queue.put((step, safe_message))

                yield "<!--vp-status:start|启动求解 pipeline…-->"

                solve_task = _asyncio.create_task(
                    _solve(req.statement, model=req.model, progress=_on_progress,
                           lang=req.lang, extra_context=extra_ctx)
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
            finally:
                _reset_user_llm_context(llm_token)

        return StreamingResponse(
            _sse_generator(_gen()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        llm_token = _apply_user_llm_context(user)
        try:
            result = await _solve(req.statement, model=req.model,
                                  lang=req.lang, extra_context=extra_ctx)
        finally:
            _reset_user_llm_context(llm_token)
        return result.to_dict()


@app.post("/solve_latex")
async def solve_latex(req: SolveLatexRequest, user: dict = Depends(current_user)):
    """将证明蓝图转换为可编译的 LaTeX 代码（流式 SSE）。"""
    if not req.blueprint or not req.blueprint.strip():
        raise HTTPException(status_code=422, detail="blueprint 不能为空")
    user = require_quota(user)

    from modes.research.solver import generate_proof_latex

    async def _gen():
        llm_token = _apply_user_llm_context(user)
        try:
            async for chunk in generate_proof_latex(req.blueprint, statement=req.statement, model=req.model):
                yield chunk
        finally:
            _reset_user_llm_context(llm_token)

    return StreamingResponse(
        _sse_generator(_gen()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 端点：/review ──────────────────────────────────────────────────────────────

@app.post("/review")
async def review(req: ReviewRequest, user: dict = Depends(current_user)):
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
    user = require_quota(user)
    req.user_id = str(user["id"])

    from modes.research.reviewer import review_text, review_paper_images

    llm_token = _apply_user_llm_context(user)
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
                lang=req.lang or "zh",
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("paper review failed")
        raise HTTPException(status_code=502, detail=f"论文审查失败: {str(e)[:200]}")
    finally:
        _reset_user_llm_context(llm_token)

    return report.to_dict()


# ── 端点：/review_stream ──────────────────────────────────────────────────────

@app.post("/review_stream")
async def review_stream(req: ReviewRequest, user: dict = Depends(current_user)):
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
    user = require_quota(user)
    req.user_id = str(user["id"])

    from modes.research.reviewer import review_text as _review_text, review_paper_images

    async def _factory(_on_progress, _on_result):
        llm_token = _apply_user_llm_context(user)
        try:
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
                lang=req.lang or "zh",
            )
        finally:
            _reset_user_llm_context(llm_token)

    return await _run_review_stream(
        _factory,
        start_status="<!--vp-status:start|启动论文审查 pipeline…-->",
    )


@app.post("/review_pdf_stream")
async def review_pdf_stream(
    file: UploadFile = File(...),
    max_theorems: int = Form(8, ge=1, le=50),
    user_id: str = Form("anonymous"),
    lang: Optional[str] = Form(None),
    mode: str = Form("pipeline"),
    check_logic: bool = Form(True),
    check_citations: bool = Form(True),
    check_symbols: bool = Form(True),
    model: Optional[str] = Form(None),
    mineru_token: Optional[str] = Form(None),
    nanonets_api_key: Optional[str] = Form(None),
    user: dict = Depends(current_user),
):
    """论文上传审查（SSE）：支持 PDF / 图片 / tex / txt / md。

    PDF：**仅** Nanonets OCR（异步提取 Markdown）→ 大章节切分 → LLM 结构化章节审查。
    不再使用 agent/docling、MinerU、PyMuPDF 作为 PDF 解析路径；解析失败返回 ``parse_failed``，无降级。

    ``max_theorems`` / ``check_*`` / ``mode`` / ``mineru_token`` 对 PDF 路径保留为兼容字段，当前不驱动 PDF 主流程。
    MinerU 已切到 Agent Lightweight Extract API，无需 token。
    """
    filename = file.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件不能为空")

    # 文件大小限制（在 SSE 流开始前校验，保证返回正确 HTTP 状态码）
    _MAX_PDF_BYTES = 50 * 1024 * 1024   # 50 MB
    _MAX_TEXT_BYTES = 1 * 1024 * 1024   # 1 MB
    _MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB
    text_exts = {".tex", ".txt", ".md", ".mmd"}
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    content_type = (file.content_type or "").lower()

    is_pdf = (suffix == ".pdf" or content_type == "application/pdf")
    is_image = (suffix in image_exts or content_type.startswith("image/"))
    is_text = (suffix in text_exts or content_type in {"text/plain", "text/markdown"})

    if not (is_pdf or is_image or is_text):
        raise HTTPException(status_code=415, detail="仅支持 .pdf / .tex / .txt / .md / .mmd / 图片")

    if is_pdf and len(content) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"PDF 文件超过 50 MB 限制")
    if is_text and not is_pdf and len(content) > _MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail=f"文本文件超过 1 MB 限制")
    if is_image and not is_pdf and len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"图片文件超过 20 MB 限制")
    user = require_quota(user)
    user_id = str(user["id"])

    from modes.research.reviewer import review_text, review_paper_images
    from modes.research.section_reviewer import run_pdf_nanonets_section_review

    def _resolve_nanonets_key() -> str:
        k = (nanonets_api_key or "").strip()
        if k:
            return k
        user_nanonets = _effective_nanonets_cfg(user)
        k = str(user_nanonets.get("api_key", "")).strip()
        if k:
            return k
        # 运行时覆盖（通过 POST /config/nanonets 写入）
        k = str(_runtime_config_overrides.get("nanonets", {}).get("api_key", "")).strip()
        if k:
            return k
        _cfg_n = load_config().get("nanonets")
        if isinstance(_cfg_n, dict):
            return str(_cfg_n.get("api_key", "")).strip()
        return ""

    async def _factory(_on_progress, _on_result):
        llm_token = _apply_user_llm_context(user)
        try:
            if is_pdf:
                return await run_pdf_nanonets_section_review(
                    content,
                    source=filename,
                    nanonets_api_key=_resolve_nanonets_key(),
                    progress=_on_progress,
                    result_cb=_on_result,
                    model=model,
                    lang=lang or "zh",
                )

            if is_image:
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
            # is_text（已在流外校验，此处必然为文本类型）
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
                model=model,
                lang=lang or "zh",
            )
        finally:
            _reset_user_llm_context(llm_token)

    return await _run_review_stream(
        _factory,
        start_status="<!--vp-status:start|启动论文上传审查…-->",
    )


# ── 端点：/formalize ──────────────────────────────────────────────────────────

@app.post("/formalize")
async def formalize(req: FormalizeRequest, user: dict = Depends(current_user)):
    """形式化证明（Beta）：将自然语言数学命题形式化为 Lean 4 代码。"""
    if not req.statement or not req.statement.strip():
        raise HTTPException(status_code=422, detail="statement 不能为空")
    user = require_quota(user)

    from modes.formalization.pipeline import formalize_stream

    async def _gen():
        llm_token = _apply_user_llm_context(user)
        try:
            async for chunk in formalize_stream(
                statement=req.statement.strip(),
                lang=req.lang or "zh",
                model=req.model,
                max_iters=req.max_iters,
                current_code=req.current_code,
                compile_error=req.compile_error,
                skip_search=req.skip_search,
                mode=(req.mode or "aristotle").strip().lower(),
            ):
                yield chunk
        finally:
            _reset_user_llm_context(llm_token)

    return StreamingResponse(
        _sse_generator(_gen()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/formalize/status/{job_id}")
async def formalize_aristotle_status(job_id: str):
    """查询 Harmonic Aristotle 任务状态（project_id）。"""
    from aristotlelib.project import Project

    from core.aristotle_client import ensure_aristotle_api_key_set, get_job_snapshot

    try:
        ensure_aristotle_api_key_set()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        project = await Project.from_id(job_id)
        await project.refresh()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Aristotle 查询失败: {e}") from e

    snap = get_job_snapshot(job_id)
    created = project.created_at.isoformat() if hasattr(project.created_at, "isoformat") else str(project.created_at)
    updated = project.last_updated_at.isoformat() if hasattr(project.last_updated_at, "isoformat") else str(
        project.last_updated_at
    )
    st = project.status.value if hasattr(project.status, "value") else str(project.status)
    return {
        "project_id": project.project_id,
        "status": st,
        "percent_complete": project.percent_complete,
        "created_at": created,
        "last_updated_at": updated,
        "output_summary": project.output_summary,
        "cached": snap,
    }


# ── 端点：/search ──────────────────────────────────────────────────────────────

@app.get("/search")
async def search(
    q: str = Query(..., description="搜索查询词"),
    top_k: int = Query(10, ge=1, le=50, description="返回条数"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="最低相似度"),
    user: dict = Depends(current_user),
):
    """TheoremSearch 透传端点：直接搜索 Lean 4 定理库。"""
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="q 不能为空")
    user = require_quota(user)
    from core.config import ts_cfg
    from skills.search_theorems import search_theorems

    timeout_s = float(ts_cfg().get("timeout", 10) or 10)
    outer_timeout_s = timeout_s + 3.0
    user_label = user.get("username") or user.get("id") or "unknown"
    started = time.perf_counter()
    last_timeout: asyncio.TimeoutError | None = None
    last_error: Exception | None = None

    try:
        # 底层 TheoremSearch HTTP client 使用配置中的 timeout。
        # 这里的外层超时只作为兜底，必须略大于底层 timeout，避免冷连接 9.x 秒成功时被外层刚好截断。
        for attempt in range(1, 3):
            attempt_started = time.perf_counter()
            try:
                results = await asyncio.wait_for(
                    search_theorems(q, top_k=top_k, min_sim=min_similarity),
                    timeout=outer_timeout_s,
                )
                logger.info(
                    "TheoremSearch request ok: user=%s query=%r top_k=%d attempt=%d elapsed=%.2fs total=%.2fs",
                    user_label,
                    q[:80],
                    top_k,
                    attempt,
                    time.perf_counter() - attempt_started,
                    time.perf_counter() - started,
                )
                break
            except asyncio.TimeoutError as exc:
                last_timeout = exc
                logger.warning(
                    "TheoremSearch request timeout: user=%s query=%r attempt=%d elapsed=%.2fs timeout=%.1fs",
                    user_label,
                    q[:80],
                    attempt,
                    time.perf_counter() - attempt_started,
                    outer_timeout_s,
                )
                if attempt >= 2:
                    raise
                await asyncio.sleep(0.25)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "TheoremSearch request failed: user=%s query=%r attempt=%d elapsed=%.2fs error=%s",
                    user_label,
                    q[:80],
                    attempt,
                    time.perf_counter() - attempt_started,
                    exc,
                )
                if attempt >= 2:
                    raise
                await asyncio.sleep(0.25)
        return {
            "query": q,
            "count": len(results),
            "results": [r.to_dict() for r in results],
        }
    except asyncio.TimeoutError:
        if last_timeout:
            logger.warning(
                "TheoremSearch request gave up after timeout: user=%s query=%r total=%.2fs",
                user_label,
                q[:80],
                time.perf_counter() - started,
            )
        raise HTTPException(
            status_code=504,
            detail="TheoremSearch 查询超时，请稍后重试或检查网络连接"
        )
    except Exception as e:
        if last_error:
            logger.warning(
                "TheoremSearch request gave up after error: user=%s query=%r total=%.2fs error=%s",
                user_label,
                q[:80],
                time.perf_counter() - started,
                e,
            )
        raise HTTPException(status_code=502, detail=f"TheoremSearch 查询失败: {e}")


# ── 端点：/projects ────────────────────────────────────────────────────────────

_projects_store: dict[str, dict] = {}  # MVP 阶段内存存储，生产环境替换为持久化


@app.post("/projects")
async def create_project(req: CreateProjectRequest, user: dict = Depends(current_user)):
    """创建书本项目（学习/研究记忆的隔离单元）。"""
    req.user_id = str(user["id"])
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
async def list_projects(user: dict = Depends(current_user)):
    """列出指定用户的所有项目。"""
    user_id = str(user["id"])
    user_projects = [v for k, v in _projects_store.items() if v["user_id"] == user_id]
    return {"user_id": user_id, "projects": user_projects}


# ── 端点：/health ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health(request: Request):
    """服务健康检查，包含 LLM、TheoremSearch、Kimina、Aristotle 状态和缓存统计。"""
    import datetime as _dt
    from core.theorem_search import _get_http_client
    from core.config import ts_cfg
    from modes.research.agent.tools import check_agent_tool_health
    from modes.formalization.verifier import check_kimina_health
    from core.aristotle_client import check_aristotle_health

    user = _request_user(request)
    cfg = _effective_llm_cfg(user)

    # ── LLM 连通检查 ──────────────────────────────────────────────
    async def _check_llm() -> tuple[str, str, str]:
        """向 LLM base_url/models 发 GET 探测，返回 (status, base_url, model)。"""
        base_url = cfg.get("base_url", "")
        model = cfg.get("model", "")
        if not base_url:
            return "not_configured", base_url, model
        try:
            probe_url = base_url.rstrip("/") + "/models"
            r = await asyncio.wait_for(
                _get_http_client().get(probe_url, timeout=8),
                timeout=9,
            )
            status = "ok" if r.status_code < 500 else f"error:{r.status_code}"
        except asyncio.TimeoutError:
            logger.debug("health: LLM check timed out")
            status = "timeout"
        except Exception as exc:
            logger.debug("health: LLM check failed: %s", exc)
            status = "unreachable"
        return status, base_url, model

    async def _check_ts() -> str:
        # 如果缓存里已有条目，说明近期调用成功过 → 直接报 ok
        stats = _ts_cache_stats()
        if stats.get("total", 0) > 0:  # total 是 get_cache_stats() 返回的实际键名
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

    (
        (llm_status, llm_base_url, llm_model),
        ts_status,
        kimina_status,
        paper_review_agent,
        aristotle_status,
    ) = await asyncio.gather(
        _check_llm(),
        _check_ts(),
        check_kimina_health(),
        check_agent_tool_health(),
        check_aristotle_health(),
    )

    ts_cache = _ts_cache_stats()
    nanonets = _effective_nanonets_cfg(user)
    nanonets_configured = bool(str(nanonets.get("api_key", "")).strip())

    # overall 由 LLM 连通性决定（TheoremSearch 超时不影响系统可用性）
    overall = "ok" if llm_status == "ok" else "degraded"

    result: dict = {
        "status": overall,
        "version": "0.1.0",
        "timestamp": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "llm": {
            "base_url": llm_base_url,
            "model": llm_model,
        },
        "dependencies": {
            "llm": {
                "status": llm_status,
                "base_url": llm_base_url,
                "model": llm_model,
            },
            "theorem_search": {
                "status": ts_status,
                "cache": ts_cache,
            },
            "kimina": kimina_status,
            "nanonets": {
                "status": "ok" if nanonets_configured else "not_configured",
                "api_key_configured": nanonets_configured,
            },
            "paper_review_agent": {
                k: v for k, v in paper_review_agent.items()
                if k not in {"mathpix", "mistral_ocr", "grobid"}
            },
            "aristotle": aristotle_status,
        },
    }
    return result


# ── 端点：/config/llm  /config/nanonets ───────────────────────────────────────

def _effective_llm_cfg(user: dict | None = None) -> dict:
    """返回合并了运行时覆盖的 LLM 配置。"""
    base = dict(llm_cfg())
    base.update(_runtime_config_overrides.get("llm", {}))
    if user:
        settings = get_settings(int(user["id"]))
        user_llm = settings.get("llm") if isinstance(settings, dict) else None
        if isinstance(user_llm, dict):
            base.update({k: v for k, v in user_llm.items() if v})
    return base


def _effective_nanonets_cfg(user: dict | None = None) -> dict:
    """返回合并了运行时覆盖的 Nanonets 配置。"""
    from core.config import nanonets_cfg
    base = dict(nanonets_cfg())
    base.update(_runtime_config_overrides.get("nanonets", {}))
    if user:
        settings = get_settings(int(user["id"]))
        user_nanonets = settings.get("nanonets") if isinstance(settings, dict) else None
        if isinstance(user_nanonets, dict):
            base.update({k: v for k, v in user_nanonets.items() if v})
    return base


@app.get("/config")
async def get_config(user: dict = Depends(current_user)):
    """返回 UI 可展示的脱敏配置。API key 只返回是否已配置。"""
    llm = _effective_llm_cfg(user)
    nanonets = _effective_nanonets_cfg(user)
    settings = get_settings(int(user["id"]))
    can_configure_api = bool(user.get("is_admin"))
    return {
        "config_path": str(config_path()),
        "auth": {
            "can_configure_api": can_configure_api,
        },
        "llm": {
            "base_url": llm.get("base_url", ""),
            "model": llm.get("model", ""),
            "api_key_configured": bool(str(llm.get("api_key", "")).strip()),
        },
        "nanonets": {
            "api_key_configured": bool(str(nanonets.get("api_key", "")).strip()),
        },
        "settings": {
            "wait_tips": (settings.get("ui") or {}).get("wait_tips"),
        },
        "user": _safe_public_user(user),
    }


@app.post("/config/llm")
async def update_llm_config(body: dict, user: dict = Depends(current_user)):
    """保存当前用户的 LLM 配置。"""
    if not bool(user.get("is_admin")):
        raise HTTPException(status_code=403, detail="当前用户模式不允许修改 API 配置")
    patch: dict = {}
    for key in ("base_url", "api_key", "model"):
        if key in body and isinstance(body[key], str) and body[key].strip():
            patch[key] = body[key].strip()
    if not patch:
        raise HTTPException(status_code=422, detail="至少提供 base_url / api_key / model 之一")
    update_settings(int(user["id"]), {"llm": patch})
    logger.info("LLM config saved: %s", {k: ("***" if k == "api_key" else v) for k, v in patch.items()})
    return {"ok": True, "updated": list(patch.keys()), "config_path": str(config_path())}


@app.post("/config/nanonets")
async def update_nanonets_config(body: dict, user: dict = Depends(current_user)):
    """保存当前用户的 Nanonets API Key。"""
    if not bool(user.get("is_admin")):
        raise HTTPException(status_code=403, detail="当前用户模式不允许修改 API 配置")
    api_key = (body.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="api_key 不能为空")
    update_settings(int(user["id"]), {"nanonets": {"api_key": api_key}})
    logger.info("Nanonets API key saved")
    return {"ok": True, "config_path": str(config_path())}


@app.post("/config/ui")
async def update_ui_config(body: dict, user: dict = Depends(current_user)):
    """保存当前用户的 UI 偏好。"""
    patch: dict = {}
    if "wait_tips" in body:
        patch["wait_tips"] = bool(body.get("wait_tips"))
    if not patch:
        raise HTTPException(status_code=422, detail="没有可保存的 UI 设置")
    update_settings(int(user["id"]), {"ui": patch})
    return {"ok": True}


# ── 错误处理 ──────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": str(exc)}},
    )
