import asyncio
import json

from modes.formalization.models import FormalizationBlueprint, FormalizationCandidate, VerificationReport
from modes.formalization.tools import (
    _build_mathlib_search_queries,
    _deterministic_repair_candidate,
    _expand_search_keywords,
    _normalize_candidate_data,
    extract_keywords,
    generate_candidate,
    retrieve_context,
    search_github_mathlib,
    validate_mathlib_match,
    verify_candidate,
)


class _FakeProc:
    def __init__(self, stderr: str, returncode: int = 1):
        self._stderr = stderr.encode("utf-8")
        self.returncode = returncode

    async def communicate(self):
        return b"", self._stderr

    def kill(self):
        return None


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses: list[_FakeResponse], observed: list[dict]):
        self._responses = list(responses)
        self._observed = observed

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None, headers=None):
        self._observed.append({
            "url": url,
            "params": params or {},
            "headers": headers or {},
        })
        if self._responses:
            return self._responses.pop(0)
        return _FakeResponse(200, {"items": []})


class _FakeTheoremHit:
    def __init__(self, name: str, body: str, *, score: float = 0.0, similarity: float = 0.0):
        self.name = name
        self.body = body
        self.slogan = ""
        self.paper_title = "TheoremSearch"
        self.link = "https://example.com/theorem"
        self.score = score
        self.similarity = similarity


def test_verify_candidate_marks_missing_mathlib_as_mathlib_skip(monkeypatch):
    async def fake_create_subprocess_exec(*args, **kwargs):
        return _FakeProc(
            "vp_tmp_demo.lean:1:0: error: unknown module prefix 'Mathlib'\n\n"
            "No directory 'Mathlib' or file 'Mathlib.olean' in the search path entries:\n"
            "c:\\Users\\runner\\.elan\\toolchains\\lean-4.26.0-windows\\lib\\lean"
        )

    monkeypatch.delenv("VP_KIMINA_URL", raising=False)
    monkeypatch.delenv("KIMINA_URL", raising=False)
    monkeypatch.delenv("KIMINA_BASE_URL", raising=False)
    monkeypatch.setattr("modes.formalization.verifier.shutil.which", lambda name: "lean.exe" if name == "lean" else None)
    monkeypatch.setattr("modes.formalization.verifier.asyncio.create_subprocess_exec", fake_create_subprocess_exec)

    report = asyncio.run(
        verify_candidate(
            "import Mathlib\n\n"
            "theorem demo (a b : ℝ) : a ^ 2 + b ^ 2 ≥ 2 * a * b := by\n"
            "  nlinarith [sq_nonneg (a - b)]\n"
        )
    )

    assert report.status == "mathlib_skip"
    assert report.failure_mode == "mathlib_unavailable"
    assert report.passed is False


def test_extract_keywords_strips_and_limits_results(monkeypatch):
    async def fake_chat_json(*args, **kwargs):
        return {
            "keywords": [" Nat.add_comm ", "commutative", "natural number", "addition", "lemma", "overflow"],
        }

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)

    keywords = asyncio.run(extract_keywords("对任意自然数 a, b，有 a + b = b + a"))

    assert keywords[0] in {"add_comm", "nat.add_comm"}
    assert "nat.add_comm" in keywords
    assert "natural_number" in keywords
    assert "nat" in keywords
    assert len(keywords) == 5


def test_extract_keywords_uses_codex_default_model(monkeypatch):
    observed = {}

    async def fake_chat_json(*args, **kwargs):
        observed["model"] = kwargs.get("model")
        return {"keywords": ["add_comm"]}

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)

    keywords = asyncio.run(extract_keywords("对任意自然数 a, b，有 a + b = b + a"))

    from core.config import formalization_model_cfg

    assert keywords
    expected = formalization_model_cfg().get("keywords") or formalization_model_cfg().get("default")
    assert observed["model"] == expected


def test_generate_candidate_respects_explicit_model_override(monkeypatch):
    observed = {}

    async def fake_chat_json(*args, **kwargs):
        observed["model"] = kwargs.get("model")
        return {
            "lean_code": "theorem demo : True := by\n  trivial",
            "theorem_statement": "theorem demo : True",
            "uses_mathlib": False,
            "proof_status": "complete",
            "explanation": "ok",
            "confidence": 0.5,
        }

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)

    candidate = asyncio.run(
        generate_candidate(
            "任意命题",
            FormalizationBlueprint(goal_summary="任意命题", target_shape="theorem demo : True", revision=0),
            [],
            model="gpt-5.4",
        )
    )

    assert candidate.theorem_statement == "theorem demo : True"
    assert observed["model"] == "gpt-5.4"


def test_extract_keywords_fallback_uses_statement_words_and_aliases(monkeypatch):
    async def fake_chat_json(*args, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)

    keywords = asyncio.run(extract_keywords("For every natural number n, n + 0 = n"))

    assert "natural" in keywords
    assert "nat" in keywords
    assert any(keyword in keywords for keyword in {"add_zero", "nat.add_zero"})


def test_expand_search_keywords_adds_square_inequality_aliases():
    expanded = _expand_search_keywords(
        "对任意实数 a, b，有 a^2 + b^2 ≥ 2ab",
        ["am gm", "square inequality", "real number"],
    )

    assert "two_mul_le_add_sq" in expanded
    assert "sq_nonneg" in expanded
    assert "real" in expanded


def test_expand_search_keywords_adds_nat_qualified_theorem_name():
    expanded = _expand_search_keywords(
        "对任意自然数 a, b，有 a + b = b + a",
        ["add_comm", "commutative", "addition"],
    )

    assert "add_comm" in expanded
    assert "nat" in expanded
    assert "nat.add_comm" in expanded


def test_build_mathlib_search_queries_prefers_quoted_theorem_name():
    queries = _build_mathlib_search_queries(["nat.add_comm", "add_comm", "nat", "comm"])

    assert queries
    assert queries[0] == "\"nat.add_comm\""
    assert any("\"add_comm\"" in query for query in queries)


def test_search_github_mathlib_uses_multiple_queries_and_deduplicates(monkeypatch):
    observed: list[dict] = []
    responses = [
        _FakeResponse(
            200,
            {
                "items": [
                    {
                        "name": "Basic.lean",
                        "path": "Mathlib/Algebra/Order/Field/Basic.lean",
                        "html_url": "https://example.com/mathlib/two_mul_le_add_sq",
                        "text_matches": [{"fragment": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by"}],
                    }
                ]
            },
        ),
        _FakeResponse(
            200,
            {
                "items": [
                    {
                        "name": "Basic.lean",
                        "path": "Mathlib/Algebra/Order/Field/Basic.lean",
                        "html_url": "https://example.com/mathlib/two_mul_le_add_sq",
                        "text_matches": [{"fragment": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by"}],
                    }
                ]
            },
        ),
    ]

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        "modes.formalization.tools.httpx.AsyncClient",
        lambda timeout=15.0: _FakeAsyncClient(responses, observed),
    )

    candidates = asyncio.run(search_github_mathlib(["two_mul_le_add_sq", "real", "sq_nonneg", "pow_two"], top_k=6))

    assert len(candidates) == 1
    assert candidates[0]["path"] == "Mathlib/Algebra/Order/Field/Basic.lean"
    assert len(observed) >= 2
    assert all("repo:leanprover-community/mathlib4" in req["params"]["q"] for req in observed)
    assert observed[0]["headers"]["Authorization"] == "Bearer test-token"


def test_search_github_mathlib_returns_empty_on_401(monkeypatch):
    observed: list[dict] = []
    monkeypatch.setattr(
        "modes.formalization.tools.httpx.AsyncClient",
        lambda timeout=15.0: _FakeAsyncClient([_FakeResponse(401, {})], observed),
    )

    candidates = asyncio.run(search_github_mathlib(["nat", "add_comm"], top_k=3))

    assert candidates == []
    assert len(observed) == 1


def test_validate_mathlib_match_returns_none_when_model_says_no(monkeypatch):
    async def fake_chat_json(*args, **kwargs):
        return {"match": False, "score": 0.2, "lean_name": ""}

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)

    best, score = asyncio.run(
        validate_mathlib_match(
            "证明一个命题",
            [{"name": "Basic.lean", "path": "Mathlib/Data/Nat/Basic.lean", "snippet": "theorem demo : True := by"}],
        )
    )

    assert best is None
    assert score == 0.0


def test_validate_mathlib_match_selects_candidate_from_lean_name_tail(monkeypatch):
    async def fake_chat_json(*args, **kwargs):
        return {
            "match": True,
            "score": 0.94,
            "lean_name": "Mathlib.Algebra.Order.Field.Basic.two_mul_le_add_sq",
            "explanation": "命中标准平方不等式",
        }

    monkeypatch.setattr("modes.formalization.tools.chat_json", fake_chat_json)
    monkeypatch.setattr("modes.formalization.tools._HEURISTIC_FAST_MATCH_THRESHOLD", 0.99)

    candidates = [
        {
            "name": "Other.lean",
            "path": "Mathlib/Algebra/Order/Ring/Unrelated.lean",
            "snippet": "theorem add_sq (a b : α) : (a + b)^2 = a^2 + 2 * a * b + b^2 := by ring",
        },
        {
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/Order/Field/Basic.lean",
            "snippet": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by nlinarith",
        },
    ]

    best, score = asyncio.run(validate_mathlib_match("对任意实数 a, b，有 a^2 + b^2 ≥ 2ab", candidates))

    assert score >= 0.94
    assert best is not None
    assert best["path"].endswith("Field/Basic.lean")
    assert best["lean_name"].endswith("two_mul_le_add_sq")


def test_validate_mathlib_match_uses_heuristic_fast_path_without_llm(monkeypatch):
    async def fail_chat_json(*args, **kwargs):
        raise AssertionError("heuristic fast path 应该提前返回，不应调用 LLM")

    monkeypatch.setattr("modes.formalization.tools.chat_json", fail_chat_json)

    candidates = [
        {
            "name": "Basic.lean",
            "path": "Mathlib/Algebra/Divisibility/Basic.lean",
            "snippet": "theorem dvd_trans {a b c : Nat} : a ∣ b → b ∣ c → a ∣ c := by",
            "source": "leansearch",
        }
    ]

    best, score = asyncio.run(validate_mathlib_match("若 a ∣ b 且 b ∣ c，则 a ∣ c", candidates))

    assert best is not None
    assert score >= 0.95
    assert best["lean_name"].endswith("dvd_trans")
    assert best["match_explanation"].startswith("heuristic:")


def test_validate_mathlib_match_fallbacks_to_heuristic_when_llm_errors(monkeypatch):
    async def fail_chat_json(*args, **kwargs):
        raise RuntimeError("llm timeout")

    monkeypatch.setattr("modes.formalization.tools.chat_json", fail_chat_json)

    candidates = [
        {
            "name": "Basic.lean",
            "path": "Mathlib/Data/Nat/Basic.lean",
            "snippet": "theorem Nat.add_comm (a b : Nat) : a + b = b + a := by",
            "source": "github_mathlib",
        }
    ]

    best, score = asyncio.run(validate_mathlib_match("对任意自然数 a,b，a+b=b+a", candidates))

    assert best is not None
    assert score >= 0.9
    assert "add_comm" in best["lean_name"]


def test_retrieve_context_uses_injected_search_and_expands_keywords():
    observed = {}

    async def fake_github_search(keywords: list[str], top_k: int = 6):
        observed["keywords"] = list(keywords)
        return [
            {
                "name": "Basic.lean",
                "path": "Mathlib/Algebra/Order/Field/Basic.lean",
                "html_url": "https://example.com/mathlib/two_mul_le_add_sq",
                "snippet": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by nlinarith",
            }
        ]

    async def fake_theorem_search(*args, **kwargs):
        return [_FakeTheoremHit("sq_nonneg", "0 ≤ x^2", score=0.8, similarity=0.8)]

    async def fake_external_search(statement: str, keywords: list[str], top_k: int = 4):
        observed["external_keywords"] = list(keywords)
        return [
            {
                "name": "two_mul_le_add_sq",
                "path": "Mathlib/Algebra/Order/Field/Basic.lean",
                "html_url": "https://leansearch.example/two_mul_le_add_sq",
                "snippet": "theorem two_mul_le_add_sq (a b : α) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by",
                "source": "leansearch",
                "score": 0.77,
                "lean_name": "two_mul_le_add_sq",
            }
        ]

    hits, github_candidates = asyncio.run(
        retrieve_context(
            "对任意实数 a, b，有 a^2 + b^2 ≥ 2ab",
            keywords=["am gm", "square inequality", "real number"],
            github_search=fake_github_search,
            external_search=fake_external_search,
            theorem_search=fake_theorem_search,
        )
    )

    assert "two_mul_le_add_sq" in observed["keywords"]
    assert "sq_nonneg" in observed["keywords"]
    assert observed["external_keywords"] == observed["keywords"]
    assert github_candidates[0]["path"].endswith("Field/Basic.lean")
    assert hits[0].kind == "theorem_search"
    assert any(hit.kind == "leansearch_mathlib" for hit in hits)


def test_normalize_candidate_data_unescapes_literal_newlines() -> None:
    candidate = _normalize_candidate_data(
        {
            "lean_code": "import Mathlib\\n\\ntheorem demo : True := by\\n  trivial\\n",
            "theorem_statement": "",
            "uses_mathlib": True,
        }
    )

    assert "\\n" not in candidate.lean_code
    assert "theorem demo : True := by\n  trivial" in candidate.lean_code


def test_normalize_candidate_data_collapses_mathlib_submodule_imports() -> None:
    candidate = _normalize_candidate_data(
        {
            "lean_code": (
                "import Mathlib.Data.Real.Basic\n"
                "import Mathlib.Tactic.Nlinarith\n\n"
                "theorem demo (a b : ℝ) : a ^ 2 + b ^ 2 ≥ 2 * a * b := by\n"
                "  nlinarith\n"
            ),
            "theorem_statement": "",
            "uses_mathlib": True,
        }
    )

    assert candidate.lean_code.startswith("import Mathlib\n\n")
    assert "Mathlib.Tactic.Nlinarith" not in candidate.lean_code


def test_deterministic_repair_candidate_fixes_square_inequality() -> None:
    candidate = FormalizationCandidate(
        lean_code=(
            "import Mathlib\n\n"
            "theorem sq_add_sq_ge_two_mul (a b : ℝ) : a ^ 2 + b ^ 2 ≥ 2 * a * b := by\n"
            "  rw [← sub_nonneg]\n"
        ),
        theorem_statement="theorem sq_add_sq_ge_two_mul (a b : ℝ) : a ^ 2 + b ^ 2 ≥ 2 * a * b",
        uses_mathlib=True,
        proof_status="complete",
        explanation="broken",
        confidence=0.2,
        origin="generated",
        blueprint_revision=0,
    )
    verification = VerificationReport(
        status="error",
        error="rewrite failed",
        failure_mode="tactic_error",
        diagnostics=["rewrite failed"],
        passed=False,
    )

    repaired = _deterministic_repair_candidate(candidate, verification)

    assert repaired is not None
    assert "have h : (a - b) ^ 2 ≥ 0 := sq_nonneg (a - b)" in repaired.lean_code
    assert "nlinarith" in repaired.lean_code
