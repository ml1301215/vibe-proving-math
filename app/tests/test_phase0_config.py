"""Phase 0 验收 0.1 + 0.2：目录结构 + config.toml 读取"""
import pytest
from pathlib import Path


APP_ROOT = Path(__file__).parent.parent


def test_directory_structure():
    """0.1 验证必须存在的目录和文件"""
    required = [
        "core", "skills", "modes", "api", "tests",
        "config.example.toml", "docker-compose.yml", "requirements.txt",
    ]
    for name in required:
        assert (APP_ROOT / name).exists(), f"缺少: {name}"


def test_config_llm_section():
    """0.2 config.toml 能读取 [llm] 段"""
    from core.config import llm_cfg
    cfg = llm_cfg()
    assert "base_url" in cfg, "缺少 llm.base_url"
    assert "api_key" in cfg, "缺少 llm.api_key"
    assert "model" in cfg, "缺少 llm.model"
    assert cfg["base_url"].startswith("http"), f"base_url 格式异常: {cfg['base_url']}"


def test_config_theorem_search_section():
    """config.toml 能读取 [theorem_search] 段"""
    from core.config import ts_cfg
    cfg = ts_cfg()
    assert "base_url" in cfg


def test_config_latrace_section():
    """config.toml 能读取 [latrace] 段"""
    from core.config import latrace_cfg
    cfg = latrace_cfg()
    assert "base_url" in cfg
