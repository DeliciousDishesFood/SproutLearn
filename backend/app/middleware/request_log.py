"""访问日志中间件（纯 ASGI，避免 BaseHTTPMiddleware 缓冲 SSE）。"""

from __future__ import annotations

from time import perf_counter

from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (perf_counter() - started) * 1000
            state = scope.get("state") or {}
            user_id = state.get("user_id")
            class_id = state.get("class_id")
            message = "{} {} | status={} | duration_ms={:.1f} | user_id={} | class_id={}"
            args = (
                scope.get("method", ""),
                scope.get("path", ""),
                status_code,
                duration_ms,
                user_id,
                class_id,
            )
            logger.info(message, *args)
            if duration_ms > get_settings().slow_request_ms:
                logger.warning(
                    "慢请求 {} {} 耗时 {:.1f}ms",
                    scope.get("method", ""),
                    scope.get("path", ""),
                    duration_ms,
                )
