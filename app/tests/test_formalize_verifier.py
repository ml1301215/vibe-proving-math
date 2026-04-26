import asyncio

from modes.formalization.verifier import (
    VerifierConfig,
    check_kimina_health,
    classify_failure_mode,
    verify_candidate,
    verify_candidate_kimina,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *, posts=None, gets=None):
        self._posts = list(posts or [])
        self._gets = list(gets or [])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json=None, headers=None):
        self.last_post = {"url": url, "json": json, "headers": headers}
        if self._posts:
            return self._posts.pop(0)
        return _FakeResponse(404, {})

    async def get(self, url, headers=None):
        if self._gets:
            return self._gets.pop(0)
        return _FakeResponse(404, {})


def test_classify_failure_mode_marks_sorry():
    assert classify_failure_mode("error", "proof still contains sorry") == "contains_sorry"


def test_verify_candidate_kimina_rejects_sorry_after_success(monkeypatch):
    fake_client = _FakeAsyncClient(
        posts=[
            _FakeResponse(
                200,
                {
                    "results": [
                        {
                            "custom_id": "formalization-0",
                            "response": {"messages": [], "sorries": []},
                        }
                    ]
                },
            )
        ]
    )
    monkeypatch.setattr(
        "modes.formalization.verifier.httpx.AsyncClient",
        lambda timeout=30.0: fake_client,
    )

    report = asyncio.run(
        verify_candidate_kimina(
            "theorem demo : True := by\n  sorry",
            config=VerifierConfig(kind="kimina", kimina_url="https://kimina.example", timeout_seconds=5.0),
        )
    )

    assert report.passed is False
    assert report.failure_mode == "contains_sorry"
    assert report.verifier.startswith("kimina:")
    assert fake_client.last_post["json"]["codes"][0]["code"].startswith("theorem demo")


def test_verify_candidate_kimina_accepts_real_verify_response(monkeypatch):
    monkeypatch.setattr(
        "modes.formalization.verifier.httpx.AsyncClient",
        lambda timeout=30.0: _FakeAsyncClient(
            posts=[
                _FakeResponse(
                    200,
                    {
                        "results": [
                            {
                                "custom_id": "formalization-0",
                                "response": {
                                    "messages": [{"severity": "info", "data": "Nat : Type"}],
                                    "sorries": [],
                                },
                            }
                        ]
                    },
                )
            ]
        ),
    )

    report = asyncio.run(
        verify_candidate_kimina(
            "#check Nat",
            config=VerifierConfig(kind="kimina", kimina_url="https://kimina.example/verify", timeout_seconds=5.0),
        )
    )

    assert report.passed is True
    assert report.failure_mode == "none"


def test_verify_candidate_kimina_maps_lean_error_from_verify_response(monkeypatch):
    monkeypatch.setattr(
        "modes.formalization.verifier.httpx.AsyncClient",
        lambda timeout=30.0: _FakeAsyncClient(
            posts=[
                _FakeResponse(
                    200,
                    {
                        "results": [
                            {
                                "custom_id": "formalization-0",
                                "response": {
                                    "messages": [{"severity": "error", "data": "unknown identifier 'Foo.bar'"}],
                                    "sorries": [],
                                },
                            }
                        ]
                    },
                )
            ]
        ),
    )

    report = asyncio.run(
        verify_candidate_kimina(
            "theorem demo : True := by\n  exact Foo.bar",
            config=VerifierConfig(kind="kimina", kimina_url="https://kimina.example", timeout_seconds=5.0),
        )
    )

    assert report.passed is False
    assert report.failure_mode == "missing_symbol"


def test_verify_candidate_falls_back_to_local_when_kimina_unavailable(monkeypatch):
    monkeypatch.setenv("VP_KIMINA_URL", "https://kimina.example")
    monkeypatch.setenv("VP_KIMINA_FALLBACK_TO_LOCAL", "1")

    async def fake_remote(lean_code: str, config=None):
        from modes.formalization.models import VerificationReport

        return VerificationReport(
            status="unavailable",
            error="remote down",
            failure_mode="environment_unavailable",
            verifier="kimina",
            passed=False,
        )

    async def fake_local(lean_code: str):
        from modes.formalization.models import VerificationReport

        return VerificationReport(
            status="verified",
            error="",
            failure_mode="none",
            verifier="local_lean",
            passed=True,
        )

    monkeypatch.setattr("modes.formalization.verifier.verify_candidate_kimina", fake_remote)
    monkeypatch.setattr("modes.formalization.verifier.verify_candidate_local", fake_local)

    report = asyncio.run(verify_candidate("theorem demo : True := by\n  trivial"))

    assert report.passed is True
    assert report.verifier == "local_lean"


def test_check_kimina_health_reports_ok(monkeypatch):
    monkeypatch.setenv("VP_KIMINA_URL", "https://kimina.example")
    monkeypatch.setattr(
        "modes.formalization.verifier.httpx.AsyncClient",
        lambda timeout=8.0: _FakeAsyncClient(gets=[_FakeResponse(200, {"status": "ok"})]),
    )

    health = asyncio.run(check_kimina_health())

    assert health["status"] == "ok"
    assert health["configured"] is True
