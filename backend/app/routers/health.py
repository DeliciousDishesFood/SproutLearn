"""健康检查：按实际数据库方言报告，Redis/Qdrant 探针失败转 503。"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.qdrant_client import qdrant_health
from app.redis_client import redis_ping
from app.utils.response import fail, success
from app.utils.time import now_str

router = APIRouter(tags=["health"])
_settings = get_settings()


def _check_db(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB 探针失败: {}", exc)
        return "error"


def _check_redis() -> str:
    try:
        return redis_ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 探针失败: {}", exc)
        return "error"


def _check_qdrant() -> str:
    try:
        return qdrant_health()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant 探针失败: {}", exc)
        return "error"


def _secret_fingerprint() -> str:
    value = (_settings.secret_key or "").encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:16]


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """API-20 健康检查：不写业务表；返回真实 db_backend/db_name，不返回 secret。"""
    db_backend = db.get_bind().dialect.name
    db_status = _check_db(db)
    checks = {
        "db": db_status,
        "mysql": db_status if db_backend == "mysql" else "n/a",
        "redis": _check_redis(),
        "qdrant": _check_qdrant(),
    }
    required_ok = db_status == "ok" and checks["redis"] == "ok"
    if _settings.vector_index_enabled and checks["qdrant"] != "ok":
        required_ok = False
    data = {
        "status": "ok" if required_ok else "error",
        "version": _settings.app_version,
        "db_backend": db_backend,
        "db_name": _settings.mysql_database if db_backend == "mysql" else "sqlite",
        "app_env": _settings.app_env,
        "jwt_secret_fingerprint": _secret_fingerprint(),
        "checks": checks,
        "timestamp": now_str(),
    }
    if not required_ok:
        return JSONResponse(
            status_code=503,
            content=fail(50301, "依赖服务不可用", data),
        )
    return success(data)
