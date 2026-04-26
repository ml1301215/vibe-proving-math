import json

from fastapi.testclient import TestClient

from api.server import app


def _collect_sse_events(client: TestClient, payload: dict) -> list[dict]:
    events = []
    with client.stream("POST", "/formalize", json=payload) as resp:
        assert resp.status_code == 200, resp.text
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                events.append({"kind": "done"})
                break
            obj = json.loads(raw)
            if "status" in obj:
                events.append({"kind": "status", "step": obj.get("step"), "status": obj["status"]})
            elif "final" in obj:
                events.append({"kind": "final", "data": obj["final"]})
            elif "error" in obj:
                events.append({"kind": "error", "data": obj["error"]})
            elif "chunk" in obj:
                events.append({"kind": "chunk", "data": obj["chunk"]})
    return events


def test_formalize_rejects_blank_statement():
    client = TestClient(app)
    resp = client.post("/formalize", json={"statement": "   "})
    assert resp.status_code == 422


def test_formalize_auto_repairs_until_verified(monkeypatch):
    import modes.formalization.pipeline as pipeline

    async def fake_extract_keywords(statement: str) -> list[str]:
        return ["prime", "number"]

    async def fake_search(keywords: list[str], top_k: int = 6) -> list[dict]:
        return []

    async def fake_autoformalize(statement: str, model=None, lang: str = "zh") -> dict:
        return {
            "lean_code": "theorem demo : True := by\n  exact missingProof",
            "theorem_statement": "theorem demo : True",
            "uses_mathlib": False,
            "proof_status": "complete",
            "explanation": "初版自动形式化",
            "confidence": 0.41,
        }

    repair_calls: list[dict] = []

    async def fake_repair(statement: str, lean_code: str, compile_error: str, *, model=None, lang: str = "zh") -> dict:
        repair_calls.append({
            "statement": statement,
            "lean_code": lean_code,
            "compile_error": compile_error,
            "lang": lang,
        })
        return {
            "lean_code": "theorem demo : True := by\n  trivial",
            "theorem_statement": "theorem demo : True",
            "uses_mathlib": False,
            "proof_status": "complete",
            "explanation": "根据编译错误移除了不存在的标识符",
            "confidence": 0.78,
        }

    compile_results = iter([
        {"status": "error", "error": "lean:2:8: error: unknown identifier 'missingProof'"},
        {"status": "verified", "error": ""},
    ])

    async def fake_compile(lean_code: str) -> dict:
        return next(compile_results)

    monkeypatch.setattr(pipeline, "_extract_keywords", fake_extract_keywords)
    monkeypatch.setattr(pipeline, "_search_github_mathlib", fake_search)
    monkeypatch.setattr(pipeline, "_autoformalize", fake_autoformalize)
    monkeypatch.setattr(pipeline, "_repair_formalization", fake_repair)
    monkeypatch.setattr(pipeline, "_try_compile_lean", fake_compile)

    client = TestClient(app)
    events = _collect_sse_events(client, {"statement": "True 命题", "lang": "zh", "max_iters": 4})

    status_steps = [e["step"] for e in events if e["kind"] == "status"]
    assert "generate" in status_steps
    assert "compile" in status_steps
    assert "repair" in status_steps

    final = next(e["data"] for e in events if e["kind"] == "final")
    assert final["compilation"]["status"] == "verified"
    assert final["iterations"] == 2
    assert final["auto_optimized"] is True
    assert len(final["attempt_history"]) == 2
    assert repair_calls, "应至少调用一次编译错误驱动修复"
    assert "missingProof" in repair_calls[0]["compile_error"]


def test_formalize_continue_optimization_skips_search(monkeypatch):
    import modes.formalization.pipeline as pipeline

    called = {
        "extract": 0,
        "search": 0,
        "auto": 0,
        "repair": 0,
    }

    async def fail_extract(statement: str) -> list[str]:
        called["extract"] += 1
        raise AssertionError("continue 优化路径不应重新提取关键词")

    async def fail_search(keywords: list[str], top_k: int = 6) -> list[dict]:
        called["search"] += 1
        raise AssertionError("continue 优化路径不应重新搜索 mathlib")

    async def fail_auto(statement: str, model=None, lang: str = "zh") -> dict:
        called["auto"] += 1
        raise AssertionError("continue 优化路径不应重新走首次 autoformalize")

    async def fake_repair(statement: str, lean_code: str, compile_error: str, *, model=None, lang: str = "zh") -> dict:
        called["repair"] += 1
        assert "unknown constant" in compile_error
        return {
            "lean_code": "theorem demo : True := by\n  trivial",
            "theorem_statement": "theorem demo : True",
            "uses_mathlib": False,
            "proof_status": "complete",
            "explanation": "继续优化成功",
            "confidence": 0.8,
        }

    compile_results = iter([
        {"status": "error", "error": "lean:2:2: error: unknown constant Foo.bar"},
        {"status": "verified", "error": ""},
    ])

    async def fake_compile(lean_code: str) -> dict:
        return next(compile_results)

    monkeypatch.setattr(pipeline, "_extract_keywords", fail_extract)
    monkeypatch.setattr(pipeline, "_search_github_mathlib", fail_search)
    monkeypatch.setattr(pipeline, "_autoformalize", fail_auto)
    monkeypatch.setattr(pipeline, "_repair_formalization", fake_repair)
    monkeypatch.setattr(pipeline, "_try_compile_lean", fake_compile)

    client = TestClient(app)
    events = _collect_sse_events(
        client,
        {
            "statement": "True 命题",
            "lang": "zh",
            "max_iters": 3,
            "skip_search": True,
            "current_code": "theorem demo : True := by\n  exact Foo.bar",
            "compile_error": "lean:2:2: error: unknown constant Foo.bar",
        },
    )

    final = next(e["data"] for e in events if e["kind"] == "final")
    assert final["compilation"]["status"] == "verified"
    assert final["iterations"] == 2
    assert called["extract"] == 0
    assert called["search"] == 0
    assert called["auto"] == 0
    assert called["repair"] == 1


def test_formalize_returns_mathlib_match_before_generation(monkeypatch):
    import modes.formalization.pipeline as pipeline

    called = {
        "extract": 0,
        "validate": 0,
    }

    async def fake_extract(statement: str) -> list[str]:
        called["extract"] += 1
        return ["square", "inequality"]

    async def fake_retrieve(statement: str, *, keywords: list[str]):
        return [], [{"path": "Mathlib/Algebra/Order/Field/Basic.lean", "name": "demo", "html_url": "https://example.com/mathlib"}]

    async def fake_validate(statement: str, candidates: list[dict]):
        called["validate"] += 1
        return ({
            "path": "Mathlib/Algebra/Order/Field/Basic.lean",
            "name": "sqineq",
            "html_url": "https://example.com/mathlib",
            "snippet": "theorem sqineq (a b : ℝ) : a ^ 2 + b ^ 2 ≥ 2 * a * b := by\n  nlinarith [sq_nonneg (a - b)]",
            "lean_name": "sqineq",
            "match_explanation": "已匹配到 mathlib 定理",
        }, 0.93)

    monkeypatch.setattr(pipeline, "_extract_keywords", fake_extract)
    monkeypatch.setattr(pipeline, "_retrieve_context", fake_retrieve)
    monkeypatch.setattr(pipeline, "_validate_match", fake_validate)

    client = TestClient(app)
    events = _collect_sse_events(
        client,
        {
            "statement": "对任意实数 a, b，证明 a^2 + b^2 ≥ 2ab。",
            "lang": "zh",
            "max_iters": 2,
        },
    )

    status_steps = [e["step"] for e in events if e["kind"] == "status"]
    assert "search" in status_steps
    assert "validate" in status_steps
    assert "found" in status_steps
    assert "generate" not in status_steps

    final = next(e["data"] for e in events if e["kind"] == "final")
    assert final["source"] == "mathlib4"
    assert final["compilation"]["status"] == "mathlib_verified"
    assert final["selected_candidate"]["origin"] == "mathlib4"
    assert called == {"extract": 1, "validate": 1}
