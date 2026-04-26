"""Phase 6 验收测试：FastAPI 端点"""
import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8080"

# ── 工具函数 ─────────────────────────────────────────────────────────────────

def _get(path: str, timeout: int = 30) -> dict:
    import urllib.request
    r = urllib.request.urlopen(f"{BASE_URL}{path}", timeout=timeout)
    return json.loads(r.read())


def _post(path: str, data: dict, timeout: int = 120) -> dict:
    import urllib.request
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())


def _check_server():
    try:
        _get("/health", timeout=15)
        return True
    except Exception:
        return False


# ── 6.1 端点齐全 ─────────────────────────────────────────────────────────────

def test_health_endpoint():
    """6.1a /health 端点可访问"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动（运行 uvicorn api.server:app --port 8080）")

    result = _get("/health")
    assert result.get("status") == "ok", f"health status 异常: {result}"
    assert "version" in result
    assert "llm" in result
    assert "dependencies" in result
    print(f"\n/health: {result}")


def test_projects_endpoint():
    """6.1b /projects 端点可访问"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    # POST
    created = _post("/projects", {
        "project_id": "test-api-proj",
        "name": "Test API Project",
        "user_id": "test-user-6",
    })
    assert created.get("status") == "created"

    # GET
    listed = _get("/projects?user_id=test-user-6")
    assert "projects" in listed
    assert len(listed["projects"]) >= 1
    print(f"\n/projects: created={created['status']}, listed={len(listed['projects'])} projects")


@pytest.mark.slow
def test_search_endpoint():
    """6.1c /search 端点可访问且返回合理结果"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    result = _get("/search?q=group+theory&top_k=5", timeout=90)
    assert "results" in result
    assert "count" in result
    print(f"\n/search: {result['count']} 条结果")


@pytest.mark.slow
def test_solve_endpoint_non_stream():
    """6.1d /solve 端点（非流式）返回 JSON 含 blueprint, verdict, confidence"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    result = _post("/solve", {
        "statement": "Every group of order 4 is abelian",
        "stream": False,
    }, timeout=120)

    assert "blueprint" in result, f"缺少 blueprint: {result.keys()}"
    assert "verdict" in result
    assert "confidence" in result
    print(f"\n/solve: verdict={result['verdict']}, confidence={result['confidence']:.2f}")


@pytest.mark.slow
def test_learn_endpoint_non_stream():
    """6.1e /learn 端点（非流式）返回 Markdown"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    result = _post("/learn", {
        "statement": "Prove that a group of prime order is cyclic.",
        "level": "undergraduate",
        "stream": False,
    }, timeout=300)

    assert "markdown" in result
    assert len(result["markdown"]) > 200
    assert "## 前置知识" in result["markdown"] or "## 证明" in result["markdown"]
    print(f"\n/learn: markdown length={len(result['markdown'])}")


# ── 6.2 SSE 流式 ─────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_solve_sse_stream():
    """6.2 /solve SSE 流式输出可实时接收 token"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.request

    data = json.dumps({"statement": "Prove Fermat's little theorem", "stream": True}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/solve", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )

    chunks_received = 0
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                chunk_data = line_str[5:].strip()
                if chunk_data == "[DONE]":
                    break
                chunks_received += 1
                if chunks_received >= 3:
                    break

    assert chunks_received >= 1, "SSE 流式未返回任何数据"
    print(f"\nSSE 流式: 收到 {chunks_received} 个 data 事件")


# ── 6.3 错误格式 ─────────────────────────────────────────────────────────────

def test_error_format():
    """6.3 缺少必填参数时返回合理错误"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.error

    # /review 不提供任何参数
    try:
        _post("/review", {}, timeout=10)
        assert False, "应该返回错误"
    except urllib.error.HTTPError as e:
        assert e.code in (422, 400, 500), f"错误码异常: {e.code}"
        print(f"\n错误格式测试: HTTP {e.code} (符合预期)")


# ── 6.4 /review proof_text 新接口 ────────────────────────────────────────────

def test_review_empty_proof_text():
    """6.4a /review proof_text 为空 → 422"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.error
    try:
        _post("/review", {"proof_text": "   "}, timeout=10)
        assert False, "应该返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422, f"期望 422，实际 {e.code}"


def test_review_too_long_proof_text():
    """6.4b /review proof_text 超长 → 422"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.error
    huge = "a" * 60_000
    try:
        _post("/review", {"proof_text": huge}, timeout=10)
        assert False, "应该返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422, f"期望 422，实际 {e.code}"


@pytest.mark.slow
def test_review_proof_text_single_proof():
    """6.4c /review 接受 proof_text（单证明降级路径）"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    proof = (
        "证明：1 + 1 = 2。由 Peano 公理，0 的后继定义为 1，1 的后继定义为 2。"
        "由加法定义 a + S(b) = S(a + b)，所以 1 + 1 = 1 + S(0) = S(1 + 0) = S(1) = 2。"
    )
    result = _post("/review", {"proof_text": proof, "max_theorems": 3}, timeout=180)

    assert "overall_verdict" in result, f"缺少 overall_verdict: {result}"
    assert result["overall_verdict"] in ("Correct", "Partial", "Incorrect", "NotChecked"), \
        f"verdict 不合法: {result['overall_verdict']}"
    assert "theorem_reviews" in result
    assert "stats" in result
    assert result["stats"].get("theorems_checked", 0) >= 1
    print(f"\n/review (proof_text) verdict={result['overall_verdict']}, "
          f"stats={result['stats']}")


@pytest.mark.slow
def test_review_proof_text_with_theorem_env():
    """6.4d /review 接受含 \\begin{theorem}/\\begin{proof} 的 LaTeX 片段"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    tex = (
        r"\begin{theorem}\label{thm:test}"
        r"For any prime $p > 3$, $p^2 \equiv 1 \pmod{24}$."
        r"\end{theorem}"
        r"\begin{proof}"
        r"Since $p > 3$, $p$ is coprime to 24. By Euler's theorem ..."
        r"\end{proof}"
    )
    result = _post("/review", {"proof_text": tex, "max_theorems": 2}, timeout=180)

    assert "overall_verdict" in result
    assert result["overall_verdict"] in ("Correct", "Partial", "Incorrect")
    assert result["stats"].get("theorems_checked", 0) >= 1
    # 多定理路径不应有 fallback 字段
    assert result["stats"].get("fallback") is None or \
           result["stats"].get("fallback") != "single_proof", \
           "含 theorem 环境时不应走 single_proof 降级"
    print(f"\n/review (theorem env) verdict={result['overall_verdict']}, "
          f"stats={result['stats']}")


# ── 6.5 /review_stream SSE ───────────────────────────────────────────────────

import re as _re_lite

# 残留检测：除 `$...$` 数学块外，不应出现裸 `\xxx`
_LEAK_RE = _re_lite.compile(r"\\[a-zA-Z]+")


def _no_residual_latex(s):
    if not isinstance(s, str) or not s:
        return True
    stripped = _re_lite.sub(r"\$\$[\s\S]+?\$\$|\$[^$\n]+?\$", "", s)
    return _LEAK_RE.search(stripped) is None


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _walk_strings(x)


def _consume_sse(path, body, *, timeout=180, max_events=200):
    """通用 SSE 消费器：返回按 kind 分类的 events list。

    kind ∈ {status, result, final, chunk, reasoning, error, done}
    """
    import urllib.request
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    events = []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            if payload == "[DONE]":
                events.append({"kind": "done"})
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            if "status" in obj:
                events.append({"kind": "status", **obj})
            elif "result" in obj:
                events.append({"kind": "result", "data": obj["result"]})
            elif "final" in obj:
                events.append({"kind": "final", "data": obj["final"]})
            elif "chunk" in obj:
                events.append({"kind": "chunk", "data": obj["chunk"]})
            elif "reasoning" in obj:
                events.append({"kind": "reasoning", "data": obj["reasoning"]})
            elif "error" in obj:
                events.append({"kind": "error", "data": obj["error"]})
            if len(events) >= max_events:
                break
    return events


def test_review_stream_empty_proof_text():
    """6.5a /review_stream proof_text 为空 → 422（流式入参校验和非流式同源）"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.error
    try:
        _post("/review_stream", {"proof_text": "  "}, timeout=10)
        assert False, "应该返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422, f"期望 422，实际 {e.code}"


def test_review_stream_too_long_proof_text():
    """6.5b /review_stream proof_text 超长 → 422"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    import urllib.error
    huge = "a" * 60_000
    try:
        _post("/review_stream", {"proof_text": huge}, timeout=10)
        assert False, "应该返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422, f"期望 422，实际 {e.code}"


@pytest.mark.slow
def test_review_stream_emits_status_result_final():
    """6.5c /review_stream 必须依次下发 status / result / final / [DONE]，
    且每帧字符串不得残留裸 LaTeX 控制序列。"""
    if not _check_server():
        pytest.skip("FastAPI 服务器未启动")

    proof = (
        "证明：1 + 1 = 2。由 Peano 公理，0 的后继定义为 1，1 的后继定义为 2。"
        "由加法定义 a + S(b) = S(a + b)，所以 1 + 1 = 1 + S(0) = S(1 + 0) = S(1) = 2。"
    )
    events = _consume_sse(
        "/review_stream",
        {"proof_text": proof, "max_theorems": 2},
        timeout=240,
    )

    kinds = [e["kind"] for e in events]
    assert "status" in kinds, f"缺少 status 帧: {kinds}"
    assert "result" in kinds, f"缺少 result 帧: {kinds}"
    assert "final" in kinds, f"缺少 final 帧: {kinds}"
    assert "done" in kinds, f"缺少 [DONE] 哨兵: {kinds}"

    # 顺序：第一个 status → 至少一个 result → final → done
    idx_status = next(i for i, e in enumerate(events) if e["kind"] == "status")
    idx_result = next(i for i, e in enumerate(events) if e["kind"] == "result")
    idx_final = next(i for i, e in enumerate(events) if e["kind"] == "final")
    idx_done = next(i for i, e in enumerate(events) if e["kind"] == "done")
    assert idx_status < idx_result < idx_final < idx_done, \
        f"SSE 顺序错乱: status@{idx_status} result@{idx_result} final@{idx_final} done@{idx_done}"

    # LaTeX 卫生：所有 result/final 帧的字符串内容都不能残留
    for ev in events:
        if ev["kind"] not in ("result", "final"):
            continue
        for s in _walk_strings(ev.get("data")):
            assert _no_residual_latex(s), \
                f"SSE {ev['kind']} 帧残留 LaTeX: {s!r}"

    # final.summary_dict 应至少含 overall_verdict 与 stats
    final = next(e for e in events if e["kind"] == "final")
    summary = final["data"]
    assert "overall_verdict" in summary
    assert summary["overall_verdict"] in ("Correct", "Partial", "Incorrect", "NotChecked")
    assert "stats" in summary
    print(
        f"\n/review_stream: status={kinds.count('status')} "
        f"result={kinds.count('result')} final=1 done=1 "
        f"verdict={summary['overall_verdict']}"
    )
