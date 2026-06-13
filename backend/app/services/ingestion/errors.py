"""采集相关异常。"""

from __future__ import annotations


class IngestSourceError(Exception):
    """单个平台采集失败（限流、超时、网络等）。"""

    def __init__(self, platform: str, message: str) -> None:
        self.platform = platform
        self.message = message
        super().__init__(message)
