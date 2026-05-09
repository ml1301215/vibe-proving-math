from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from core.config import kimina_cfg
from modes.formalization.models import VerificationReport

logger = logging.getLogger("modes.formalization")

_LEAN_VERIFY_TIMEOUT_SECONDS = 60.0


@dataclass
class VerifierConfig:
    kind: str = "local"
    kimina_url: str = ""
    api_key: str = ""
    timeout_seconds: float = 120.0
    allow_local_fallback: bool = True


def get_verifier_config() -> VerifierConfig:
    cfg = kimina_cfg()
    kimina_url = str(cfg.get("url") or "").strip()
    api_key = str(cfg.get("api_key") or "").strip()
    try:
        timeout_seconds = float(cfg.get("timeout_seconds") or 120.0)
    except ValueError:
        timeout_seconds = 120.0
    allow_local_fallback = bool(cfg.get("allow_local_fallback", True))
    return VerifierConfig(
        kind="kimina" if kimina_url else "local",
        kimina_url=kimina_url,
        api_key=api_key,
        timeout_seconds=max(3.0, timeout_seconds),
        allow_local_fallback=allow_local_fallback,
    )


def classify_failure_mode(status: str, error: str) -> str:
    text = (error or "").lower()
    if status in {"verified", "mathlib_verified"}:
        return "none"
    if "sorry" in text:
        return "contains_sorry"
    if status == "unavailable":
        return "environment_unavailable"
    if status == "timeout":
        return "compile_timeout"
    if status == "mathlib_skip":
        return "mathlib_unavailable"
    if "unknown identifier" in text or "unknown constant" in text:
        return "missing_symbol"
    if "unexpected token" in text or "parser" in text or "expected" in text:
        return "syntax_error"
    if "tactic" in text:
        return "tactic_error"
    if "type mismatch" in text or "application type mismatch" in text:
        return "statement_mismatch"
    if "unsolved goals" in text:
        return "unsolved_goals"
    return "compile_error"


def _discover_mathlib_project() -> Optional[Path]:
    raw = str(kimina_cfg().get("mathlib_project") or "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    if (
        candidate.is_dir()
        and (candidate / "lean-toolchain").is_file()
        and ((candidate / "lakefile.lean").is_file() or (candidate / "lakefile.toml").is_file())
    ):
        return candidate
    return None


async def _resolve_project_binaries(project_root: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
    elan_bin = shutil.which("elan")
    if not elan_bin:
        return None, None, None

    async def _run_which(tool: str) -> Optional[str]:
        proc = await asyncio.create_subprocess_exec(
            elan_bin,
            "which",
            tool,
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        path = stdout.decode("utf-8", errors="replace").strip()
        return path or None

    lean_bin = await _run_which("lean")
    lake_bin = await _run_which("lake")
    toolchain_bin = str(Path(lean_bin).parent) if lean_bin else None
    return lean_bin, lake_bin, toolchain_bin


def _contains_sorry(lean_code: str) -> bool:
    return bool(re.search(r"\bsorry\b", lean_code or ""))


def _normalize_diagnostics(text: str) -> str:
    return re.sub(r"[^\s]+\.lean:", "lean:", (text or "")).strip()


def _is_mathlib_missing(error_text: str) -> bool:
    lower = (error_text or "").lower()
    return (
        "unknown package 'mathlib'" in lower
        or "unknown module prefix 'mathlib'" in lower
        or "no directory 'mathlib'" in lower
        or ("mathlib" in lower and "object file" in lower)
        or ("mathlib" in lower and "no such file or directory" in lower)
    )


async def verify_candidate_local(lean_code: str) -> VerificationReport:
    candidate_uses_mathlib = bool(re.search(r"^\s*import\s+Mathlib", lean_code, flags=re.MULTILINE))
    project_root = _discover_mathlib_project() if candidate_uses_mathlib else None
    lean_bin = None
    lake_bin = None
    toolchain_bin = None

    if project_root is not None:
        try:
            lean_bin, lake_bin, toolchain_bin = await _resolve_project_binaries(project_root)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to resolve project binaries from %s: %s", project_root, exc)

    if not lean_bin:
        lean_bin = shutil.which("lean")
    if not lean_bin:
        candidate = os.path.expanduser(r"~\.elan\toolchains\lean-4.26.0-windows\bin\lean.exe")
        if os.path.isfile(candidate):
            lean_bin = candidate
    if not lean_bin:
        return VerificationReport(
            status="unavailable",
            error="Lean 4 未安装或不在 PATH 中",
            failure_mode="environment_unavailable",
            verifier="local_lean",
            passed=False,
        )

    tmp = None
    try:
        tmp_dir = str(project_root) if project_root else None
        with tempfile.NamedTemporaryFile(suffix=".lean", mode="w", encoding="utf-8", delete=False, dir=tmp_dir) as handle:
            handle.write(lean_code)
            tmp = handle.name
        env = os.environ.copy()
        if toolchain_bin:
            env["PATH"] = toolchain_bin + os.pathsep + env.get("PATH", "")

        if candidate_uses_mathlib and project_root and lake_bin:
            cmd = [lake_bin, "env", "lean", tmp]
            cwd = str(project_root)
        else:
            cmd = [lean_bin, tmp]
            cwd = None

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_LEAN_VERIFY_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.communicate()
            except Exception:  # noqa: BLE001
                pass
            return VerificationReport(
                status="timeout",
                error=f"编译超时（>{int(_LEAN_VERIFY_TIMEOUT_SECONDS)}s），请在线验证",
                failure_mode="compile_timeout",
                verifier="local_lean",
                passed=False,
            )

        out_text = (stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")).strip()
        if proc.returncode == 0 and "error:" not in out_text.lower():
            if _contains_sorry(lean_code):
                return VerificationReport(
                    status="error",
                    error="编译通过，但结果仍包含 sorry",
                    failure_mode="contains_sorry",
                    diagnostics=["编译通过，但结果仍包含 sorry"],
                    verifier="local_lean",
                    passed=False,
                )
            return VerificationReport(
                status="verified",
                error="",
                failure_mode="none",
                diagnostics=[],
                verifier="local_lean",
                passed=True,
            )

        clean = _normalize_diagnostics(out_text)
        if candidate_uses_mathlib and _is_mathlib_missing(clean):
            return VerificationReport(
                status="mathlib_skip",
                error=clean[:600],
                failure_mode="mathlib_unavailable",
                diagnostics=[clean[:600]],
                verifier="local_lean",
                passed=False,
            )
        failure_mode = classify_failure_mode("error", clean)
        return VerificationReport(
            status="error",
            error=clean[:600],
            failure_mode=failure_mode,
            diagnostics=[clean[:600]],
            verifier="local_lean",
            passed=False,
        )
    except Exception as exc:  # noqa: BLE001
        return VerificationReport(
            status="unavailable",
            error=str(exc),
            failure_mode="environment_unavailable",
            diagnostics=[str(exc)],
            verifier="local_lean",
            passed=False,
        )
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:  # noqa: BLE001
                pass


def _candidate_kimina_urls(base_url: str) -> list[str]:
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        return []
    parsed = urlparse(raw)
    path = parsed.path or ""
    if path.endswith("/verify") or path.endswith("/api/check"):
        return [raw]
    return [f"{raw}/verify", f"{raw}/api/check", raw]


def _kimina_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key
    return headers


def _coerce_text_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                msg = str(
                    item.get("message")
                    or item.get("text")
                    or item.get("error")
                    or item.get("stderr")
                    or ""
                ).strip()
                if msg:
                    items.append(msg)
        return items
    if isinstance(value, dict):
        msg = str(
            value.get("message")
            or value.get("text")
            or value.get("error")
            or value.get("stderr")
            or ""
        ).strip()
        return [msg] if msg else []
    text = str(value).strip()
    return [text] if text else []


def _collect_kimina_messages(response: dict) -> list[str]:
    diagnostics: list[str] = []
    for message in response.get("messages") or []:
        if not isinstance(message, dict):
            continue
        text = str(message.get("data") or message.get("message") or "").strip()
        severity = str(message.get("severity") or "").strip()
        if text:
            diagnostics.append(f"{severity}: {text}" if severity else text)
    for sorry in response.get("sorries") or []:
        if not isinstance(sorry, dict):
            continue
        goal = str(sorry.get("goal") or "").strip()
        if goal:
            diagnostics.append(f"sorry: {goal}")
    return diagnostics


def _parse_kimina_verify_results(lean_code: str, payload: dict, *, endpoint: str) -> Optional[VerificationReport]:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None

    first = results[0] if isinstance(results[0], dict) else {}
    verifier_name = f"kimina:{endpoint}"
    top_error = str(first.get("error") or "").strip()
    response = first.get("response")
    if top_error:
        normalized_error = _normalize_diagnostics(top_error)[:600]
        return VerificationReport(
            status="timeout" if "timed out" in normalized_error.lower() else "error",
            error=normalized_error,
            failure_mode=(
                "compile_timeout"
                if "timed out" in normalized_error.lower()
                else classify_failure_mode("error", normalized_error)
            ),
            diagnostics=[normalized_error],
            verifier=verifier_name,
            passed=False,
        )

    if not isinstance(response, dict):
        return VerificationReport(
            status="error",
            error="Kimina 返回了空 response",
            failure_mode="compile_error",
            diagnostics=["Kimina 返回了空 response"],
            verifier=verifier_name,
            passed=False,
        )

    if "message" in response:
        repl_error = _normalize_diagnostics(str(response.get("message") or ""))[:600]
        return VerificationReport(
            status="error",
            error=repl_error,
            failure_mode="compile_timeout" if "timed out" in repl_error.lower() else "compile_error",
            diagnostics=[repl_error],
            verifier=verifier_name,
            passed=False,
        )

    diagnostics = [_normalize_diagnostics(item)[:600] for item in _collect_kimina_messages(response) if item]
    has_error = any(
        isinstance(message, dict) and str(message.get("severity") or "").strip().lower() == "error"
        for message in (response.get("messages") or [])
    )
    has_sorry = bool(response.get("sorries"))

    if has_error:
        error = diagnostics[0] if diagnostics else "Kimina 返回 Lean error"
        return VerificationReport(
            status="error",
            error=error,
            failure_mode=classify_failure_mode("error", error),
            diagnostics=diagnostics or [error],
            verifier=verifier_name,
            passed=False,
        )

    if has_sorry or _contains_sorry(lean_code):
        return VerificationReport(
            status="error",
            error="Kimina 编译通过，但结果仍包含 sorry",
            failure_mode="contains_sorry",
            diagnostics=diagnostics or ["Kimina 编译通过，但结果仍包含 sorry"],
            verifier=verifier_name,
            passed=False,
        )

    return VerificationReport(
        status="verified",
        error="",
        failure_mode="none",
        diagnostics=diagnostics,
        verifier=verifier_name,
        passed=True,
    )


def _parse_kimina_report(lean_code: str, payload: dict, *, endpoint: str) -> VerificationReport:
    payload = payload or {}
    parsed_verify = _parse_kimina_verify_results(lean_code, payload, endpoint=endpoint)
    if parsed_verify is not None:
        return parsed_verify

    diagnostics = []
    for key in ("diagnostics", "errors", "messages", "warnings", "stderr", "stdout", "output"):
        diagnostics.extend(_coerce_text_list(payload.get(key)))
    diagnostics = [_normalize_diagnostics(item)[:600] for item in diagnostics if item]
    error = (
        str(payload.get("error") or payload.get("message") or payload.get("stderr") or "").strip()
        or (diagnostics[0] if diagnostics else "")
    )
    status_hint = str(payload.get("status") or "").strip().lower()
    passed_hint = bool(
        payload.get("passed")
        or payload.get("ok")
        or payload.get("success")
        or status_hint in {"verified", "ok", "success", "pass"}
    )
    verifier_name = f"kimina:{endpoint}"

    if passed_hint and not error:
        if _contains_sorry(lean_code):
            return VerificationReport(
                status="error",
                error="Kimina 编译通过，但结果仍包含 sorry",
                failure_mode="contains_sorry",
                diagnostics=["Kimina 编译通过，但结果仍包含 sorry"],
                verifier=verifier_name,
                passed=False,
            )
        return VerificationReport(
            status="verified",
            error="",
            failure_mode="none",
            diagnostics=[],
            verifier=verifier_name,
            passed=True,
        )

    if status_hint == "timeout":
        return VerificationReport(
            status="timeout",
            error=error or "Kimina 验证超时",
            failure_mode="compile_timeout",
            diagnostics=diagnostics or ([error] if error else []),
            verifier=verifier_name,
            passed=False,
        )

    candidate_uses_mathlib = bool(re.search(r"^\s*import\s+Mathlib", lean_code, flags=re.MULTILINE))
    if candidate_uses_mathlib and _is_mathlib_missing(error or "\n".join(diagnostics)):
        return VerificationReport(
            status="mathlib_skip",
            error=(error or "Kimina 缺少 Mathlib 环境")[:600],
            failure_mode="mathlib_unavailable",
            diagnostics=diagnostics or ([error] if error else []),
            verifier=verifier_name,
            passed=False,
        )

    normalized_error = _normalize_diagnostics(error)[:600]
    return VerificationReport(
        status="error",
        error=normalized_error,
        failure_mode=classify_failure_mode("error", normalized_error or "\n".join(diagnostics)),
        diagnostics=diagnostics or ([normalized_error] if normalized_error else []),
        verifier=verifier_name,
        passed=False,
    )


async def verify_candidate_kimina(lean_code: str, config: Optional[VerifierConfig] = None) -> VerificationReport:
    cfg = config or get_verifier_config()
    if not cfg.kimina_url:
        return VerificationReport(
            status="unavailable",
            error="Kimina endpoint 未配置",
            failure_mode="environment_unavailable",
            verifier="kimina",
            passed=False,
        )

    headers = _kimina_headers(cfg.api_key)
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
        for endpoint in _candidate_kimina_urls(cfg.kimina_url):
            if endpoint.rstrip("/").endswith("/verify"):
                payload = {
                    "codes": [{"custom_id": "formalization-0", "code": lean_code}],
                    "timeout": int(cfg.timeout_seconds),
                    "disable_cache": False,
                    "infotree_type": "original",
                }
            elif endpoint.rstrip("/").endswith("/api/check"):
                payload = {
                    "snippets": [{"id": "formalization-0", "code": lean_code}],
                    "timeout": int(cfg.timeout_seconds),
                    "debug": False,
                    "reuse": True,
                    "infotree": "original",
                }
            else:
                payload = {
                    "codes": [{"custom_id": "formalization-0", "code": lean_code}],
                    "timeout": int(cfg.timeout_seconds),
                    "disable_cache": False,
                    "infotree_type": "original",
                }
            try:
                resp = await client.post(endpoint, json=payload, headers=headers)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{endpoint}: {exc}")
                continue
            if resp.status_code >= 500:
                errors.append(f"{endpoint}: HTTP {resp.status_code}")
                continue
            if resp.status_code == 404:
                errors.append(f"{endpoint}: HTTP 404")
                continue
            if resp.status_code >= 400:
                body = resp.text.strip()
                errors.append(f"{endpoint}: HTTP {resp.status_code} {body[:200]}")
                continue
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {"status": "error", "error": resp.text}
            return _parse_kimina_report(lean_code, data, endpoint=endpoint)

    joined = " | ".join(errors)[:600]
    return VerificationReport(
        status="unavailable",
        error=joined or "Kimina verifier 不可用",
        failure_mode="environment_unavailable",
        diagnostics=[joined] if joined else [],
        verifier="kimina",
        passed=False,
    )


async def verify_candidate(lean_code: str) -> VerificationReport:
    cfg = get_verifier_config()
    if cfg.kimina_url:
        report = await verify_candidate_kimina(lean_code, config=cfg)
        if report.status != "unavailable" or not cfg.allow_local_fallback:
            return report
        logger.warning("kimina verifier unavailable, falling back to local Lean: %s", report.error)
    return await verify_candidate_local(lean_code)


async def check_kimina_health() -> dict[str, object]:
    cfg = get_verifier_config()
    if not cfg.kimina_url:
        return {"status": "disabled", "configured": False}

    headers = _kimina_headers(cfg.api_key)
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=min(cfg.timeout_seconds, 8.0)) as client:
        for endpoint in _candidate_kimina_urls(cfg.kimina_url):
            base = endpoint[:-7] if endpoint.endswith("/verify") else endpoint
            probe_urls = [f"{base.rstrip('/')}/health", endpoint]
            for probe in probe_urls:
                try:
                    resp = await client.get(probe, headers=headers)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{probe}: {exc}")
                    continue
                if resp.status_code < 500:
                    return {
                        "status": "ok" if resp.status_code < 400 else f"error:{resp.status_code}",
                        "configured": True,
                        "base_url": cfg.kimina_url,
                        "probe": probe,
                    }
                errors.append(f"{probe}: HTTP {resp.status_code}")
    return {
        "status": "unreachable",
        "configured": True,
        "base_url": cfg.kimina_url,
        "error": " | ".join(errors)[:300],
    }
