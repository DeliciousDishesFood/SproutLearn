"""模型路由错误分类：不携带任何密钥/鉴权头。"""

from __future__ import annotations


class LLMConfigError(RuntimeError):
    """厂商标识未知或配置非法（启动期应直接失败）。"""


class LLMError(Exception):
    """统一的上游错误分类。"""

    RATE_LIMITED = "RATE_LIMITED"
    AUTH_FAILED = "AUTH_FAILED"
    SERVER_ERROR = "SERVER_ERROR"
    TIMEOUT = "TIMEOUT"
    BAD_REQUEST = "BAD_REQUEST"

    def __init__(
        self,
        category: str,
        message: str,
        *,
        status_code: int | None = None,
        biz_code: str | None = None,
    ) -> None:
        self.category = category
        self.message = message
        self.status_code = status_code
        self.biz_code = biz_code
        super().__init__(self.__str__())

    def __str__(self) -> str:
        parts = [self.category]
        if self.status_code is not None:
            parts.append(f"http={self.status_code}")
        if self.biz_code:
            parts.append(f"biz={self.biz_code}")
        parts.append(self.message[:300])
        return " | ".join(parts)
