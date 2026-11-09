"""统一响应体封装：成功/失败结构必须包含 request_id 与 timestamp。"""

from contextvars import ContextVar
from typing import Any

from app.utils.time import now_str

# 请求上下文中的 request_id；由 RequestIdMiddleware 写入
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(value: str) -> None:
    _request_id_ctx.set(value)


def get_request_id() -> str:
    return _request_id_ctx.get()


def success(data: Any = None, message: str = "ok") -> dict[str, Any]:
    """成功响应体。"""
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
        "timestamp": now_str(),
    }


def fail(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """失败响应体（供异常处理器与健康检查复用）。"""
    return {
        "code": int(code),
        "message": message,
        "data": data,
        "request_id": get_request_id(),
        "timestamp": now_str(),
    }


def page_data(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    """分页统一结构。"""
    return {"total": total, "page": page, "page_size": page_size, "list": items}
