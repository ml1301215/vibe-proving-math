"""全局配置加载器，从 config.toml 读取所有配置。"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from functools import lru_cache
from typing import Any

_APP_DIR = Path(__file__).resolve().parent.parent


def _config_path() -> Path:
    raw = (os.environ.get("VP_CONFIG_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return _APP_DIR / "config.toml"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        example = _APP_DIR / "config.example.toml"
        msg = (
            f"缺少配置文件: {path}\n"
            f"请复制示例并填写密钥:\n"
            f"  cp {_APP_DIR / 'config.example.toml'} {_APP_DIR / 'config.toml'}\n"
            "或通过环境变量 VP_CONFIG_PATH 指向配置文件路径。"
        )
        if example.is_file():
            msg += f"\n（示例文件: {example}）"
        raise FileNotFoundError(msg)
    with open(path, "rb") as f:
        return tomllib.load(f)


def llm_cfg() -> dict[str, Any]:
    return load_config()["llm"]


def ts_cfg() -> dict[str, Any]:
    return load_config()["theorem_search"]


def latrace_cfg() -> dict[str, Any]:
    return load_config()["latrace"]


def paper_review_agent_cfg() -> dict[str, Any]:
    return load_config().get("paper_review_agent", {})


def nanonets_cfg() -> dict[str, Any]:
    """Nanonets OCR / 提取 API 配置。"""
    return load_config().get("nanonets", {}) or {}


def formalization_model_cfg() -> dict[str, Any]:
    return load_config().get("formalization_models", {})
