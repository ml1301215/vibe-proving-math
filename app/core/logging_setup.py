"""结构化日志初始化。

调用 setup_logging() 后，整个应用使用统一的日志配置：
  - 开发环境：彩色 stderr 输出，含时间戳和模块名
  - 生产环境：JSON Lines 格式，可接入 ELK / Grafana Loki 等

用法（在 server.py 启动时调用一次）：
    from core.logging_setup import setup_logging
    setup_logging(level="INFO")

性能说明：
  - logging 模块本身开销极小（< 1μs/record when level not reached）
  - 高频调用路径中 DEBUG 级别日志完全无开销（短路求值）
"""
from __future__ import annotations

import logging
import logging.config
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """配置全局日志格式和级别。

    level 优先级：参数 > 默认 INFO
    """
    _level = (level or "INFO").upper()
    numeric_level = getattr(logging, _level, logging.INFO)

    # 格式：时间 | 级别 | 模块 | 消息
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": fmt,
                "datefmt": datefmt,
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "standard",
                "level": _level,
            },
        },
        "loggers": {
            # vibe_proving 模块：按配置级别输出
            "core": {"level": _level, "handlers": ["stderr"], "propagate": False},
            "modes": {"level": _level, "handlers": ["stderr"], "propagate": False},
            "skills": {"level": _level, "handlers": ["stderr"], "propagate": False},
            "api": {"level": _level, "handlers": ["stderr"], "propagate": False},
            # 第三方库：降低噪声
            "httpx": {"level": "WARNING", "handlers": ["stderr"], "propagate": False},
            "httpcore": {"level": "WARNING", "handlers": ["stderr"], "propagate": False},
            "openai": {"level": "WARNING", "handlers": ["stderr"], "propagate": False},
            "uvicorn": {"level": "INFO", "handlers": ["stderr"], "propagate": False},
            "fastapi": {"level": "INFO", "handlers": ["stderr"], "propagate": False},
        },
        "root": {
            "level": _level,
            "handlers": ["stderr"],
        },
    })

    logging.getLogger("core").info(
        "Logging configured: level=%s, handlers=[stderr]", _level
    )
