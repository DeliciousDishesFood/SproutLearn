"""FastAPI 依赖注入：JWT + Redis 会话鉴权、角色校验、机器人密钥校验。"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

import redis
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.config import get_settings
from app.database import get_db
from app.exceptions import ErrorCode, AppException
from app.redis_client import get_redis_client
from app.utils import cache_keys
from app.utils.security import (
    TokenExpiredError,
    TokenInvalidError,
    decode_access_token,
)

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """鉴权后的请求用户上下文（来自 JWT + Redis 会话）。"""

    user_id: int
    role: str
    class_id: int | None
    jti: str
    exp: int


def _redis_error(exc: Exception) -> AppException:
    logger.error("Redis 不可用，鉴权失败: {}", exc)
    return AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用", data=None)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """校验 Bearer token：签名/过期 → 黑名单 → Redis 会话 → 滑动续期。"""
    if credentials is None or not credentials.credentials:
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期") from exc
    except TokenInvalidError as exc:
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录") from exc

    jti = payload.get("jti")
    subject = payload.get("sub")
    if not jti or not subject:
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录")

    client = get_redis_client()
    try:
        if client.get(cache_keys.jwt_blacklist_key(jti)):
            raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
        raw_session = client.get(cache_keys.session_key(jti))
        if not raw_session:
            raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
        try:
            session = json.loads(raw_session)
        except (TypeError, ValueError) as exc:
            raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期") from exc
        if str(session.get("user_id")) != str(subject) or session.get("role") != payload.get("role"):
            raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
        # 滑动过期：每次鉴权刷新 TTL
        client.expire(cache_keys.session_key(jti), get_settings().session_idle_seconds)
    except redis.RedisError as exc:
        raise _redis_error(exc) from exc

    current = CurrentUser(
        user_id=int(subject),
        role=str(session.get("role")),
        class_id=session.get("class_id"),
        jti=jti,
        exp=int(payload.get("exp", 0)),
    )
    request.state.user_id = current.user_id
    request.state.class_id = current.class_id
    return current


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """仅校验 JWT 签名/过期，不要求 Redis 会话；供幂等登出使用。"""
    if credentials is None or not credentials.credentials:
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录")
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期") from exc
    except TokenInvalidError as exc:
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录") from exc
    if not payload.get("jti") or not payload.get("sub"):
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录")
    return payload


def get_token_claims_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """登出用：无 token/坏 token 也返回 None，由路由按幂等成功处理。"""
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except (TokenExpiredError, TokenInvalidError):
        return None
    if not payload.get("jti") or not payload.get("sub"):
        return None
    return payload


def require_teacher(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """教师角色依赖；学生调用教师接口返回 40301。"""
    if current.role != "teacher":
        raise AppException(ErrorCode.ROLE_FORBIDDEN, "角色无权限")
    return current


def require_student(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """学生角色依赖；教师调用学生接口返回 40301。"""
    if current.role != "student":
        raise AppException(ErrorCode.ROLE_FORBIDDEN, "角色无权限")
    return current


def require_bot_secret(
    x_bot_secret: str | None = Header(default=None, alias="X-Bot-Secret"),
) -> None:
    """QQ 机器人回调鉴权：X-Bot-Secret 必须等于 BOT_SHARED_SECRET。"""
    expected = get_settings().bot_shared_secret
    if not expected or not x_bot_secret or not secrets.compare_digest(x_bot_secret, expected):
        raise AppException(ErrorCode.UNAUTHORIZED, "未登录")


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_token_claims",
    "require_teacher",
    "require_student",
    "require_bot_secret",
    "get_db",
]
