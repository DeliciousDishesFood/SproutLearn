"""基于 Redis 的固定窗口限流与登录失败计数（Redis 异常时降级放行）。"""

from __future__ import annotations

import redis
from fastapi import Request
from loguru import logger

from app.exceptions import AppException, ErrorCode
from app.redis_client import get_redis_client


def parse_rule(rule: str) -> tuple[int, int]:
    """解析 `次数/窗口秒` 配置；格式错误时抛 ValueError（启动期尽早暴露）。"""
    limit_text, window_text = rule.split("/", 1)
    limit = int(limit_text)
    window = int(window_text)
    if limit <= 0 or window <= 0:
        raise ValueError(f"非法限流规则: {rule}")
    return limit, window


def client_ip(request: Request) -> str:
    """优先取反代透传的真实 IP，缺省回退直连地址。"""
    forwarded = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hit(key: str, rule: str) -> bool:
    """固定窗口计数；返回 True 表示放行。Redis 异常时 WARN 并放行。"""
    limit, window = parse_rule(rule)
    try:
        client = get_redis_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, window)
        return int(count) <= limit
    except redis.RedisError as exc:
        logger.warning("限流 Redis 不可用，降级放行 key={}: {}", key, exc)
        return True


def enforce(key: str, rule: str) -> None:
    """命中限流抛 42901。"""
    if not hit(key, rule):
        raise AppException(ErrorCode.RATE_LIMITED, "请求过于频繁，请稍后再试")


def failure_count(key: str) -> int:
    try:
        raw = get_redis_client().get(key)
        return int(raw or 0)
    except (redis.RedisError, TypeError, ValueError) as exc:
        logger.warning("读取登录失败计数失败，按 0 处理: {}", exc)
        return 0


def is_failure_blocked(key: str, rule: str) -> bool:
    limit, _ = parse_rule(rule)
    return failure_count(key) >= limit


def record_failure(key: str, rule: str) -> None:
    _, window = parse_rule(rule)
    try:
        client = get_redis_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, window)
    except redis.RedisError as exc:
        logger.warning("记录登录失败计数失败: {}", exc)


def clear_failure(key: str) -> None:
    try:
        get_redis_client().delete(key)
    except redis.RedisError as exc:
        logger.warning("清理登录失败计数失败: {}", exc)
