"""X-Request-Id 注入与透传中间件（纯 ASGI，避免 BaseHTTPMiddleware 缓冲 SSE）。"""

from __future__ import annotations

from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings
from app.utils.response import set_request_id


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        settings = get_settings()
        header_name = settings.request_id_header
        headers = dict(scope.get("headers") or [])
        request_id = (
            headers.get(header_name.lower().encode(), b"").decode() or str(uuid4())
        )
        set_request_id(request_id)
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[header_name] = request_id
            await send(message)

        await self.app(scope, receive, send_wrapper)
