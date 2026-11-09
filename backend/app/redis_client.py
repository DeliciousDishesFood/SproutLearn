"""Redis 连接池与健康探针；测试可替换为 fakeredis。"""

from __future__ import annotations

from typing import Any

import redis
from loguru import logger

from app.config import get_settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """获取全局 Redis 客户端（decode_responses=True，文本 JSON 读写）。"""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    return _client


def set_redis_client(client: Any) -> None:
    """测试注入 fakeredis / mock 客户端。"""
    global _client
    _client = client


def reset_redis_client() -> None:
    """关闭并清空连接池（测试或应用关闭时调用）。"""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001 - 关闭失败不影响退出
            pass
    _client = None


def redis_ping() -> str:
    """健康检查探针：成功返回 ok，失败抛异常由调用方转 50301。"""
    get_redis_client().ping()
    return "ok"


def safe_redis_call(func, *args, **kwargs):
    """限流降级辅助：Redis 异常时记 WARN 并返回 None，由调用方决定放行策略。"""
    try:
        return func(*args, **kwargs)
    except redis.RedisError as exc:
        logger.warning("Redis 调用失败，按降级策略处理: {}", exc)
        return None
