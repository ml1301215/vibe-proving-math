"""全局配置加载器，从 config.toml 读取所有配置。"""
from __future__ import annotations

import tomllib
from pathlib import Path
from functools import lru_cache
from typing import Any

_APP_DIR = Path(__file__).resolve().parent.parent


def _config_path() -> Path:
    return _APP_DIR / "config.toml"


def config_path() -> Path:
    return _config_path()


def clear_config_cache() -> None:
    load_config.cache_clear()


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        example = _APP_DIR / "config.example.toml"
        msg = (
            f"缺少配置文件: {path}\n"
            f"请复制示例并填写密钥:\n"
            f"  cp {_APP_DIR / 'config.example.toml'} {_APP_DIR / 'config.toml'}\n"
            "配置文件路径固定为 app/config.toml。"
        )
        if example.is_file():
            msg += f"\n（示例文件: {example}）"
        raise FileNotFoundError(msg)
    with open(path, "rb") as f:
        return tomllib.load(f)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def update_config_file(updates: dict[str, dict[str, Any]]) -> Path:
    """Update simple top-level TOML sections while preserving unrelated content."""
    path = _config_path()
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        example = _APP_DIR / "config.example.toml"
        text = example.read_text(encoding="utf-8") if example.is_file() else ""

    lines = text.splitlines()
    section_ranges: dict[str, tuple[int, int]] = {}
    current: str | None = None
    current_start = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]") and not stripped.startswith("[["):
            if current is not None:
                section_ranges[current] = (current_start, idx)
            current = stripped[1:-1].strip()
            current_start = idx
    if current is not None:
        section_ranges[current] = (current_start, len(lines))

    for section, values in updates.items():
        values = {k: v for k, v in values.items() if v is not None}
        if not values:
            continue
        if section not in section_ranges:
            if lines and lines[-1].strip():
                lines.append("")
            start = len(lines)
            lines.append(f"[{section}]")
            for key, value in values.items():
                lines.append(f"{key} = {_toml_value(value)}")
            section_ranges[section] = (start, len(lines))
            continue

        start, end = section_ranges[section]
        seen: set[str] = set()
        for idx in range(start + 1, end):
            stripped = lines[idx].strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in values:
                prefix = lines[idx].split("=", 1)[0].rstrip()
                lines[idx] = f"{prefix} = {_toml_value(values[key])}"
                seen.add(key)
        insert_at = end
        for key, value in values.items():
            if key not in seen:
                lines.insert(insert_at, f"{key} = {_toml_value(value)}")
                insert_at += 1
        delta = insert_at - end
        if delta:
            for name, (range_start, range_end) in list(section_ranges.items()):
                if range_start > start:
                    section_ranges[name] = (range_start + delta, range_end + delta)
            section_ranges[section] = (start, end + delta)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    clear_config_cache()
    return path


def llm_cfg() -> dict[str, Any]:
    return load_config()["llm"]


def ts_cfg() -> dict[str, Any]:
    return load_config()["theorem_search"]


def latrace_cfg() -> dict[str, Any]:
    return load_config().get("latrace", {})


def auth_cfg() -> dict[str, Any]:
    return load_config().get("auth", {}) or {}


def latrace_enabled() -> bool:
    cfg = latrace_cfg()
    return bool(cfg.get("enabled", False))


def paper_review_agent_cfg() -> dict[str, Any]:
    return load_config().get("paper_review_agent", {})


def nanonets_cfg() -> dict[str, Any]:
    """Nanonets OCR / 提取 API 配置。"""
    return load_config().get("nanonets", {}) or {}


def aristotle_cfg() -> dict[str, Any]:
    """Harmonic Aristotle API（https://aristotle.harmonic.fun）。"""
    return load_config().get("aristotle", {}) or {}


def mineru_cfg() -> dict[str, Any]:
    return load_config().get("mineru", {}) or {}


def formalization_cfg() -> dict[str, Any]:
    return load_config().get("formalization", {}) or {}


def kimina_cfg() -> dict[str, Any]:
    return load_config().get("kimina", {}) or {}
