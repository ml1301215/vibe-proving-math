"""pytest 全局配置。"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# 确保 app/ 在 sys.path 中，使所有模块可直接 import
_APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_APP_DIR))


def _ensure_test_config() -> None:
    """CI / 新克隆仓库无 config.toml 时，从示例复制到临时路径并设置 VP_CONFIG_PATH。"""
    if os.environ.get("VP_CONFIG_PATH", "").strip():
        return
    cfg = _APP_DIR / "config.toml"
    if cfg.is_file():
        return
    example = _APP_DIR / "config.example.toml"
    if not example.is_file():
        return
    td = Path(tempfile.mkdtemp(prefix="vp_test_cfg_"))
    dest = td / "config.toml"
    shutil.copy(example, dest)
    os.environ["VP_CONFIG_PATH"] = str(dest)


_ensure_test_config()

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: 标记为慢速测试（调用真实 API，可用 -m 'not slow' 跳过）"
    )
