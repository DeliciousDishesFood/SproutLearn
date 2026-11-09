"""访问日志中间件：request_id | method | path | status | duration_ms | user_id | class_id。"""

from __future__ import annotations

from time import perf_counter

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (perf_counter() - started) * 1000
            user_id = getattr(request.state, "user_id", None)
            class_id = getattr(request.state, "class_id", None)
            message = "{} {} | status={} | duration_ms={:.1f} | user_id={} | class_id={}"
            args = (
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                user_id,
                class_id,
            )
            logger.info(message, *args)
            if duration_ms > get_settings().slow_request_ms:
                logger.warning("慢请求 {} {} 耗时 {:.1f}ms", request.method, request.url.path, duration_ms)
