"""统一日志配置。

设计文档第 15 节强调可观测性；这里提供最小可用的结构化日志初始化，
方便定位采集失败、LLM 调用异常、邮件发送失败等关键环节。
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """初始化根日志（幂等）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """获取带命名空间的 logger。"""
    setup_logging()
    return logging.getLogger(name)
