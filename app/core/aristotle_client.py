"""Harmonic Aristotle API 封装（aristotlelib · Lean 4 形式化与证明）。"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from core.config import aristotle_cfg

logger = logging.getLogger(__name__)

_JOB_SNAPSHOTS: dict[str, dict[str, Any]] = {}


def _read_api_key() -> str:
    cfg = aristotle_cfg()
    return str(cfg.get("api_key") or "").strip()


def is_aristotle_enabled() -> bool:
    return bool(_read_api_key())


def ensure_aristotle_api_key_set() -> None:
    from aristotlelib import set_api_key

    key = _read_api_key()
    if not key:
        raise ValueError("Aristotle API key 未配置（config.toml [aristotle].api_key）")
    set_api_key(key)


def aristotle_runtime_settings() -> dict[str, Any]:
    cfg = aristotle_cfg()
    return {
        "formalize_timeout_seconds": float(cfg.get("formalize_timeout_seconds") or 1800),
        "prove_timeout_seconds": float(cfg.get("prove_timeout_seconds") or 1800),
        "poll_interval_seconds": float(cfg.get("poll_interval_seconds") or 15),
    }


def register_job_snapshot(project_id: str, payload: dict[str, Any]) -> None:
    _JOB_SNAPSHOTS[project_id] = {"project_id": project_id, **payload}


def get_job_snapshot(project_id: str) -> Optional[dict[str, Any]]:
    return _JOB_SNAPSHOTS.get(project_id)


def extract_lean_from_tar(path: Path) -> str:
    import tarfile

    chunks: list[str] = []
    try:
        with tarfile.open(path, "r:*") as tar:
            for m in tar.getmembers():
                if m.isfile() and str(m.name).endswith(".lean"):
                    f = tar.extractfile(m)
                    if f:
                        chunks.append(f.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("extract lean from tar failed: %s", exc)
        return ""
    return "\n\n".join(chunks) if chunks else ""


async def download_lean_from_project(project: Any) -> str:
    """项目完成后下载 result tarball 并拼接所有 .lean 源码。"""
    from aristotlelib.project import ProjectStatus

    if project.status == ProjectStatus.FAILED:
        return ""
    if project.status not in (
        ProjectStatus.COMPLETE,
        ProjectStatus.COMPLETE_WITH_ERRORS,
        ProjectStatus.OUT_OF_BUDGET,
    ):
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        await project.get_solution(destination=tmp_path)
        return extract_lean_from_tar(tmp_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("download_lean_from_project failed: %s", exc)
        return ""
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


async def poll_until_terminal(
    project: Any,
    *,
    poll_interval: float,
    max_seconds: float,
    phase: str,
    on_elapsed: Optional[Any] = None,
) -> tuple[Any, Optional[str]]:
    """轮询直到终态或超时。返回 (project, None) 或 (project, 'timeout')。"""
    from aristotlelib.project import ProjectStatus

    start = time.monotonic()
    await project.refresh()
    register_job_snapshot(
        project.project_id,
        {"phase": phase, "status": project.status.value if hasattr(project.status, "value") else str(project.status)},
    )

    running = {ProjectStatus.QUEUED, ProjectStatus.IN_PROGRESS}
    while project.status in running:
        elapsed = time.monotonic() - start
        if elapsed >= max_seconds:
            return project, "timeout"
        if on_elapsed:
            try:
                await on_elapsed(project, elapsed)
            except Exception:  # noqa: BLE001
                pass
        await asyncio.sleep(max(poll_interval, 1.0))
        await project.refresh()
        register_job_snapshot(
            project.project_id,
            {"phase": phase, "status": project.status.value if hasattr(project.status, "value") else str(project.status)},
        )

    return project, None


async def check_aristotle_health() -> dict[str, object]:
    if not is_aristotle_enabled():
        return {"status": "disabled", "configured": False}

    ensure_aristotle_api_key_set()
    try:
        from aristotlelib.api_request import AristotleRequestClient

        async with AristotleRequestClient() as client:
            resp = await client.get("/project", params={"limit": 1})
            if resp.status_code < 500:
                return {"status": "ok", "configured": True}
            return {"status": f"error:{resp.status_code}", "configured": True}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unreachable", "configured": True, "error": str(exc)[:300]}
