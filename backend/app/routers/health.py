"""健康检查：MySQL/Redis/Qdrant 探针，失败返回 503 + 50301。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from loguru import logger

from app.config import get_settings
from app.database import engine
from app.qdrant_client import qdrant_health
from app.redis_client import redis_ping
from app.utils.response import fail, success
from app.utils.time import now_str

router = APIRouter(tags=["health"])
_settings = get_settings()


def _check_mysql() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 - 探针失败转 error
        logger.warning("MySQL 探针失败: {}", exc)
        return "error"


def _check_redis() -> str:
    try:
        return redis_ping()
    except Exception as exc:  # noqa: BLE001 - 探针失败转 error
        logger.warning("Redis 探针失败: {}", exc)
        return "error"


def _check_qdrant() -> str:
    try:
        return qdrant_health()
    except Exception as exc:  # noqa: BLE001 - 探针失败转 error
        logger.warning("Qdrant 探针失败: {}", exc)
        return "error"


@router.get("/health")
def health():
    """API-20 健康检查：不产生写操作，探针超时 2 秒。"""
    checks = {
        "mysql": _check_mysql(),
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
    }
    required_ok = checks["mysql"] == "ok" and checks["redis"] == "ok"
    if _settings.vector_index_enabled and checks["qdrant"] != "ok":
        required_ok = False

    data = {
        "status": "ok" if required_ok else "error",
        "version": _settings.app_version,
        "checks": checks,
        "timestamp": now_str(),
    }
    if not required_ok:
        return JSONResponse(
            status_code=503,
            content=fail(50301, "依赖服务不可用", data),
        )
    return success(data)
