import base64
import json

from fastapi.testclient import TestClient

from api.server import app
from modes.formalization.models import (
    FormalizationBlueprint,
    FormalizationCandidate,
    RetrievalHit,
    VerificationReport,
)
from modes.formalization.orchestrator import MATHLIB_MATCH_THRESHOLD, run_formalization
from modes.formalization.tools import FormalizationTools


async def _collect_pipeline(async_gen) -> tuple[list[str], dict]:
    chunks = []
    final = None
    async for chunk in async_gen:
        chunks.append(chunk)
        if chunk.startswith("<!--vp-final:"):
            payload = chunk[len("<!--vp-final:"):-3]
            final = json.loads(base64.b64decode(payload.encode("ascii")).decode("utf-8"))
    assert final is not None
    return chunks, final


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
                break
            obj = json.loads(raw)
            events.append(obj)
    return events


async def test_orchestrator_happy_path_includes_blueprint_and_retrieval_context():
    retrieval_hits = [
        RetrievalHit(
            kind="theorem_search",
            title="Nat.add_comm",
            body="a + b = b + a",
            source="mathlib4",
            source_url="https://example.com/add_comm",
            score=0.93,
        )
    ]
    blueprint = FormalizationBlueprint(
        goal_summary="把交换律形式化为 Nat 上加法交换",
        target_shape="theorem add_comm_demo (a b : Nat) : a + b = b + a",
        definitions=["Nat.add"],
        intermediate_lemmas=["Nat.add_comm"],
        strategy="直接调用已知交换律",
        revision=0,
    )
    candidate = FormalizationCandidate(
        lean_code="theorem add_comm_demo (a b : Nat) : a + b = b + a := by simpa using Nat.add_comm a b",
        theorem_statement="theorem add_comm_demo (a b : Nat) : a + b = b + a",
        uses_mathlib=False,
        proof_status="complete",
        explanation="使用 Nat.add_comm 直接完成证明",
        confidence=0.88,
        blueprint_revision=0,
    )

    async def extract_keywords(statement: str) -> list[str]:
        return ["nat", "addition", "commutative"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return retrieval_hits, []

    async def plan_blueprint(statement: str, retrieval_hits_arg, **kwargs):
        assert retrieval_hits_arg == retrieval_hits
        return blueprint

    async def generate_candidate(statement: str, blueprint_arg, retrieval_hits_arg, **kwargs):
        assert blueprint_arg == blueprint
        assert retrieval_hits_arg == retrieval_hits
        return candidate

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    chunks, final = await _collect_pipeline(
        run_formalization(
            "自然数加法满足交换律",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert any("vp-status:blueprint" in c for c in chunks)
    assert any("vp-status:generate" in c for c in chunks)
    assert final["blueprint"]["goal_summary"] == blueprint.goal_summary
    assert final["selected_candidate"]["theorem_statement"] == candidate.theorem_statement
    assert final["retrieval_context"][0]["title"] == "Nat.add_comm"
    assert final["verification_trace"][0]["action"] == "generate"
    assert final["next_action_hint"]


async def test_orchestrator_replans_after_statement_mismatch():
    plan_revisions = []
    generated_revisions = []

    async def extract_keywords(statement: str) -> list[str]:
        return ["succ", "injective"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], []

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        revision = kwargs.get("revision", 0)
        plan_revisions.append(revision)
        return FormalizationBlueprint(
            goal_summary=f"rev-{revision}",
            target_shape="theorem demo : True",
            strategy=f"strategy-{revision}",
            revision=revision,
        )

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        generated_revisions.append(blueprint.revision)
        return FormalizationCandidate(
            lean_code=f"theorem demo_rev_{blueprint.revision} : True := by\n  trivial",
            theorem_statement=f"theorem demo_rev_{blueprint.revision} : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation=f"candidate from revision {blueprint.revision}",
            confidence=0.7 + blueprint.revision * 0.1,
            blueprint_revision=blueprint.revision,
        )

    verify_reports = iter([
        VerificationReport(
            status="error",
            error="lean:1:1: error: type mismatch",
            failure_mode="statement_mismatch",
            diagnostics=["type mismatch"],
            passed=False,
        ),
        VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True),
    ])

    async def verify_candidate(_: str) -> VerificationReport:
        return next(verify_reports)

    chunks, final = await _collect_pipeline(
        run_formalization(
            "形式化一个命题",
            max_iters=3,
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert plan_revisions == [0, 1]
    assert generated_revisions == [0, 1]
    assert any("蓝图修订" in c for c in chunks)
    assert final["iterations"] == 2
    assert final["verification_trace"][0]["verification"]["failure_mode"] == "statement_mismatch"
    assert final["verification_trace"][1]["action"] == "replan"
    assert final["selected_candidate"]["blueprint_revision"] == 1


async def test_orchestrator_mathlib_unavailable_surfaces_failure_mode_and_hint():
    async def extract_keywords(statement: str) -> list[str]:
        return ["mathlib"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], []

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(
            status="mathlib_skip",
            error="unknown package 'mathlib'",
            failure_mode="mathlib_unavailable",
            diagnostics=["unknown package 'mathlib'"],
            passed=False,
        )

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="import Mathlib\n\ntheorem demo : True := by\n  trivial",
            theorem_statement="theorem demo : True",
            uses_mathlib=True,
            proof_status="complete",
            explanation="需要 Mathlib",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, planned_imports=["Mathlib"], revision=0)

    _, final = await _collect_pipeline(
        run_formalization(
            "需要 Mathlib 的命题",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["compilation"]["status"] == "mathlib_skip"
    assert final["failure_mode"] == "mathlib_unavailable"
    assert "Mathlib" in final["next_action_hint"]


async def test_orchestrator_returns_mathlib_result_at_threshold_boundary():
    github_candidates = [
        {
            "name": "Basic.lean",
            "path": "Mathlib/Data/Nat/Basic.lean",
            "html_url": "https://example.com/mathlib/nat/add_comm",
            "snippet": "theorem Nat.add_comm (a b : Nat) : a + b = b + a := by omega",
        }
    ]

    async def extract_keywords(statement: str) -> list[str]:
        return ["nat.add_comm", "commutative", "nat"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], github_candidates

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        return (
            {
                **candidates[0],
                "lean_name": "Nat.add_comm",
                "match_explanation": "直接命中 mathlib 定理",
            },
            MATHLIB_MATCH_THRESHOLD,
        )

    async def fail_plan_blueprint(*args, **kwargs):
        raise AssertionError("达到阈值时不应继续走 blueprint")

    _, final = await _collect_pipeline(
        run_formalization(
            "自然数加法交换律",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=fail_plan_blueprint,
            ),
        )
    )

    assert final["status"] == "found_mathlib"
    assert final["source"] == "mathlib4"
    assert final["theorem_name"] == "Nat.add_comm"


async def test_orchestrator_below_threshold_continues_generation_path():
    blueprint_called = False
    generate_called = False
    verify_called = False
    github_candidates = [
        {
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/BigOperators/Basic.lean",
            "html_url": "https://example.com/mathlib/sum_range",
            "snippet": "theorem Finset.sum_range_succ : ...",
        }
    ]

    async def extract_keywords(statement: str) -> list[str]:
        return ["gauss_sum", "sum_range", "nat"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], github_candidates

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        return (
            {
                **candidates[0],
                "lean_name": "Finset.sum_range_succ",
                "match_explanation": "相关但不是最终结论",
            },
            MATHLIB_MATCH_THRESHOLD - 0.01,
        )

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        nonlocal blueprint_called
        blueprint_called = True
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem demo : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        nonlocal generate_called
        generate_called = True
        return FormalizationCandidate(
            lean_code="theorem demo : True := by\n  trivial",
            theorem_statement="theorem demo : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="继续生成路径",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def verify_candidate(_: str) -> VerificationReport:
        nonlocal verify_called
        verify_called = True
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    _, final = await _collect_pipeline(
        run_formalization(
            "对任意自然数 n，有 1 + 2 + ... + n = n(n+1)/2",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert blueprint_called is True
    assert generate_called is True
    assert verify_called is True
    assert final["status"] == "generated"


async def test_orchestrator_rejects_plausibility_mismatch_even_if_score_high():
    async def extract_keywords(statement: str) -> list[str]:
        return ["gauss_sum", "sum_range", "nat"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], [{
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/BigOperators/Basic.lean",
            "html_url": "https://example.com/mathlib/sum_range",
            "snippet": "theorem sum_range : ...",
            "lean_name": "sum_range",
        }]

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        return ({
            **candidates[0],
            "lean_name": "sum_range",
            "match_explanation": "相关但并非最终结论",
        }, MATHLIB_MATCH_THRESHOLD + 0.2)

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem gauss_sum : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem gauss_sum : True := by\n  trivial",
            theorem_statement="theorem gauss_sum : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="继续生成路径",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    _, final = await _collect_pipeline(
        run_formalization(
            "For n, 1 + 2 + ... + n = n*(n+1)/2 (gauss sum)",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["status"] == "generated"


async def test_orchestrator_rejects_gauss_sumrange_for_chinese_pattern():
    async def extract_keywords(statement: str) -> list[str]:
        return ["gauss_sum", "sum_range", "nat"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], [{
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/BigOperators/Basic.lean",
            "html_url": "https://example.com/mathlib/sum_range",
            "snippet": "theorem Finset.sum_range_succ : ...",
            "lean_name": "Finset.sum_range_succ",
        }]

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        return ({
            **candidates[0],
            "lean_name": "Finset.sum_range_succ",
            "match_explanation": "相关但并非最终结论",
        }, MATHLIB_MATCH_THRESHOLD + 0.15)

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem gauss_sum : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem gauss_sum : True := by\n  trivial",
            theorem_statement="theorem gauss_sum : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="继续生成路径",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    _, final = await _collect_pipeline(
        run_formalization(
            "对任意自然数 n，有 1 + 2 + ... + n = n(n+1)/2",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["status"] == "generated"


async def test_orchestrator_rejects_real_template_for_integer_statement():
    async def extract_keywords(statement: str) -> list[str]:
        return ["two_mul_le_add_sq", "int"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], [{
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/Order/Field/Basic.lean",
            "html_url": "https://example.com/mathlib/two_mul_le_add_sq_real",
            "snippet": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by nlinarith",
            "lean_name": "two_mul_le_add_sq",
        }]

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        return ({
            **candidates[0],
            "lean_name": "two_mul_le_add_sq",
            "match_explanation": "疑似跨域误配",
        }, MATHLIB_MATCH_THRESHOLD + 0.12)

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem int_ineq : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem int_ineq : True := by\n  trivial",
            theorem_statement="theorem int_ineq : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="继续生成路径",
            confidence=0.5,
            blueprint_revision=0,
        )

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    _, final = await _collect_pipeline(
        run_formalization(
            "对任意整数 a, b，有 a^2 + b^2 ≥ 2ab",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["status"] == "generated"


async def test_orchestrator_beam_selects_better_candidate_within_same_attempt(monkeypatch):
    import modes.formalization.orchestrator as orchestrator

    monkeypatch.setattr(orchestrator, "_BEAM_WIDTH", 2)

    async def extract_keywords(statement: str) -> list[str]:
        return ["nat", "add_comm"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        return [], []

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem demo : True", revision=0)

    generated = {"count": 0}

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        generated["count"] += 1
        if generated["count"] == 1:
            return FormalizationCandidate(
                lean_code="theorem demo : True := by\n  sorry",
                theorem_statement="theorem demo : True",
                uses_mathlib=False,
                proof_status="partial",
                explanation="bad candidate",
                confidence=0.2,
                blueprint_revision=0,
            )
        return FormalizationCandidate(
            lean_code="theorem demo : True := by\n  trivial",
            theorem_statement="theorem demo : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="good candidate",
            confidence=0.8,
            blueprint_revision=0,
        )

    async def verify_candidate(code: str) -> VerificationReport:
        if "trivial" in code:
            return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)
        return VerificationReport(
            status="error",
            error="contains sorry",
            failure_mode="contains_sorry",
            diagnostics=["contains sorry"],
            passed=False,
        )

    _, final = await _collect_pipeline(
        run_formalization(
            "任意命题",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["status"] == "generated"
    assert final["iterations"] == 1
    assert "trivial" in final["lean_code"]
    assert generated["count"] == 2


async def test_orchestrator_refreshes_retrieval_after_failure_and_can_early_return():
    retrieve_calls = []

    async def extract_keywords(statement: str) -> list[str]:
        if "Latest verification feedback" in statement:
            return ["dvd_trans", "divides", "nat"]
        return ["divides", "nat"]

    async def retrieve_context(statement: str, *, keywords: list[str]):
        retrieve_calls.append(list(keywords))
        if len(retrieve_calls) == 1:
            return [], []
        return (
            [],
            [
                {
                    "name": "Basic.lean",
                    "path": "Mathlib/Algebra/Divisibility/Basic.lean",
                    "html_url": "https://example.com/mathlib/dvd_trans",
                    "snippet": "theorem dvd_trans : a ∣ b -> b ∣ c -> a ∣ c := by",
                    "source": "loogle",
                }
            ],
        )

    async def validate_mathlib_match(statement: str, candidates: list[dict]):
        if not candidates:
            return None, 0.0
        return (
            {
                **candidates[0],
                "lean_name": "dvd_trans",
                "match_explanation": "失败后重新检索命中传递性定理",
            },
            MATHLIB_MATCH_THRESHOLD + 0.05,
        )

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem demo : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem demo : True := by\n  sorry",
            theorem_statement="theorem demo : True",
            uses_mathlib=True,
            proof_status="partial",
            explanation="先给一个占位证明",
            confidence=0.1,
            blueprint_revision=0,
        )

    verify_reports = iter([
        VerificationReport(
            status="error",
            error="lean:1:1: error: unknown identifier 'dvd_trans'",
            failure_mode="missing_symbol",
            diagnostics=["unknown identifier 'dvd_trans'"],
            passed=False,
        )
    ])

    async def verify_candidate(_: str) -> VerificationReport:
        return next(verify_reports)

    _, final = await _collect_pipeline(
        run_formalization(
            "若 a ∣ b 且 b ∣ c，则 a ∣ c",
            max_iters=3,
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                validate_mathlib_match=validate_mathlib_match,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert len(retrieve_calls) == 2
    assert final["status"] == "found_mathlib"
    assert final["source"] == "loogle"
    assert final["theorem_name"] == "dvd_trans"


async def test_orchestrator_keyword_stage_failure_falls_back_and_still_generates():
    async def extract_keywords(statement: str) -> list[str]:
        raise TimeoutError("keyword stage timeout")

    async def retrieve_context(statement: str, *, keywords: list[str]):
        assert keywords == []
        return [], []

    async def plan_blueprint(statement: str, retrieval_hits, **kwargs):
        return FormalizationBlueprint(goal_summary=statement, target_shape="theorem demo : True", revision=0)

    async def generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem demo : True := by\n  trivial",
            theorem_statement="theorem demo : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="fallback path",
            confidence=0.4,
            blueprint_revision=0,
        )

    async def verify_candidate(_: str) -> VerificationReport:
        return VerificationReport(status="verified", error="", failure_mode="none", diagnostics=[], passed=True)

    _, final = await _collect_pipeline(
        run_formalization(
            "任意命题",
            tools=FormalizationTools(
                extract_keywords=extract_keywords,
                retrieve_context=retrieve_context,
                plan_blueprint=plan_blueprint,
                generate_candidate=generate_candidate,
                verify_candidate=verify_candidate,
            ),
        )
    )

    assert final["status"] == "generated"
    assert final["selected_candidate"]["theorem_statement"] == "theorem demo : True"


def test_formalize_api_sse_payload_keeps_extended_fields(monkeypatch):
    import modes.formalization.pipeline as pipeline
    from modes.formalization.models import FormalizationBlueprint, FormalizationCandidate, RetrievalHit

    async def fake_extract_keywords(statement: str) -> list[str]:
        return ["group", "identity"]

    async def fake_retrieve_context(statement: str, *, keywords: list[str]):
        return (
            [RetrievalHit(kind="github_mathlib", title="Group/basic.lean", body="mul_assoc", source="mathlib4")],
            [],
        )

    async def fake_plan_blueprint(statement: str, retrieval_hits: list, **kwargs):
        return FormalizationBlueprint(
            goal_summary="群单位元唯一",
            target_shape="theorem identity_unique ...",
            intermediate_lemmas=["left identity", "right identity"],
            strategy="先展开定义再代换",
            revision=0,
        )

    async def fake_generate_candidate(statement: str, blueprint, retrieval_hits, **kwargs):
        return FormalizationCandidate(
            lean_code="theorem identity_unique : True := by\n  trivial",
            theorem_statement="theorem identity_unique : True",
            uses_mathlib=False,
            proof_status="complete",
            explanation="按 blueprint 生成",
            confidence=0.82,
            blueprint_revision=0,
        )

    async def fake_compile(lean_code: str) -> dict:
        return {"status": "verified", "error": "", "failure_mode": "none", "passed": True}

    monkeypatch.setattr(pipeline, "_extract_keywords", fake_extract_keywords)
    monkeypatch.setattr(pipeline, "_retrieve_context", fake_retrieve_context)
    monkeypatch.setattr(pipeline, "_plan_blueprint", fake_plan_blueprint)
    monkeypatch.setattr(pipeline, "_generate_candidate", fake_generate_candidate)
    monkeypatch.setattr(pipeline, "_try_compile_lean", fake_compile)

    client = TestClient(app)
    events = _collect_sse_events(client, {"statement": "群单位元唯一", "lang": "zh", "max_iters": 2})
    final = next(e["final"] for e in events if "final" in e)

    assert final["status"] == "generated"
    assert final["source"] == "generated"
    assert final["blueprint"]["goal_summary"] == "群单位元唯一"
    assert final["selected_candidate"]["theorem_statement"] == "theorem identity_unique : True"
    assert final["retrieval_context"][0]["title"] == "Group/basic.lean"
    assert final["verification_trace"][0]["verification"]["status"] == "verified"
    assert any("status" in e and e["step"] == "blueprint" for e in events)
