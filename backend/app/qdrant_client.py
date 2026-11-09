"""Qdrant 探针（M1 仅健康检查，不写向量）。"""

from __future__ import annotations

import httpx
from loguru import logger

from app.config import get_settings


def qdrant_health() -> str:
    """VECTOR_INDEX_ENABLED=false 返回 skipped；启用时探测 /healthz。"""
    settings = get_settings()
    if not settings.vector_index_enabled:
        return "skipped"
    headers = {}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key
    try:
        response = httpx.get(
            f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz",
            headers=headers,
            timeout=2.0,
        )
        response.raise_for_status()
        return "ok"
    except Exception as exc:  # noqa: BLE001 - 探针失败统一转 50301
        logger.warning("Qdrant 探针失败: {}", exc)
        raise


def ensure_collection() -> None:
    """M3 启用向量时确保 collection 存在；M1 默认关闭，不产生写操作。"""
    settings = get_settings()
    if not settings.vector_index_enabled:
        return
    headers = {}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key
    payload = {
        "vectors": {
            "size": settings.vector_dim,
            "distance": settings.vector_distance,
        }
    }
    response = httpx.put(
        f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{settings.qdrant_collection}",
        headers=headers,
        json=payload,
        timeout=2.0,
    )
    response.raise_for_status()

