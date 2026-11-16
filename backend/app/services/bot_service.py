"""班级 QQ 机器人配置：保存/读取/凭证连通性测试。

AppSecret 只从环境变量读取，绝不入库、回显或写日志。
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import redis
from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.class_bot_config import ClassBotConfig
from app.schemas.bot import BotConfigUpdateRequest
from app.services.class_service import require_active_class, require_owned_class
from app.services.qq_bot import client as qq_client
from app.utils import cache_keys
from app.utils.time import fmt_dt, now, now_naive

_settings = get_settings()
TIMEOUT_SECONDS = 8.0


def _redis() -> redis.Redis:
    from app.redis_client import get_redis_client

    return get_redis_client()


def _empty(class_id: int) -> dict[str, Any]:
    return {
        "class_id": class_id,
        "app_id": None,
        "callback_url": None,
        "enabled": False,
        "group_openid": None,
        "teacher_openid": None,
        "teacher_bound_at": None,
        "binding_enabled": True,
        "notify_assignment": True,
        "notify_due_soon": True,
        "mention_missing": False,
        "allow_query_assignments": True,
        "allow_query_scores": False,
        "bot_chat_mode": "balanced",
        "bot_chat_enabled": True,
        "bot_chat_max_chars": 1200,
        "last_check_at": None,
        "last_check_status": "never",
        "secret_managed_by_env": True,
    }


def _view(config: ClassBotConfig | None, class_id: int) -> dict[str, Any]:
    if config is None:
        return _empty(class_id)
    return {
        "class_id": config.class_id,
        "app_id": config.app_id,
        "callback_url": config.callback_url,
        "enabled": bool(config.enabled),
        "group_openid": config.group_openid,
        "teacher_openid": config.teacher_openid,
        "teacher_bound_at": fmt_dt(config.teacher_bound_at),
        "binding_enabled": bool(config.binding_enabled),
        "notify_assignment": bool(config.notify_assignment),
        "notify_due_soon": bool(config.notify_due_soon),
        "mention_missing": bool(config.mention_missing),
        "allow_query_assignments": bool(config.allow_query_assignments),
        "allow_query_scores": bool(config.allow_query_scores),
        "bot_chat_mode": config.bot_chat_mode or "balanced",
        "bot_chat_enabled": bool(config.bot_chat_enabled),
        "bot_chat_max_chars": int(config.bot_chat_max_chars or 1200),
        "last_check_at": fmt_dt(config.last_check_at),
        "last_check_status": config.last_check_status or "never",
        "secret_managed_by_env": True,
    }


def get_config(db: Session, current: CurrentUser, *, class_id: int) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    config = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()
    return _view(config, class_id)


def save_config(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    payload: BotConfigUpdateRequest,
) -> dict[str, Any]:
    require_active_class(db, class_id, current.user_id)
    config = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()
    if config is None:
        config = ClassBotConfig(
            class_id=class_id,
            app_id=payload.app_id,
            callback_url=payload.callback_url,
            enabled=1 if payload.enabled else 0,
            binding_enabled=1 if payload.binding_enabled else 0,
            notify_assignment=1 if payload.notify_assignment else 0,
            notify_due_soon=1 if payload.notify_due_soon else 0,
            mention_missing=1 if payload.mention_missing else 0,
            allow_query_assignments=1 if payload.allow_query_assignments else 0,
            allow_query_scores=1 if payload.allow_query_scores else 0,
            bot_chat_mode=payload.bot_chat_mode,
            bot_chat_enabled=1 if payload.bot_chat_enabled else 0,
            bot_chat_max_chars=payload.bot_chat_max_chars,
            last_check_status="never",
            created_by=current.user_id,
        )
        db.add(config)
    else:
        config.app_id = payload.app_id
        config.callback_url = payload.callback_url
        config.enabled = 1 if payload.enabled else 0
        config.binding_enabled = 1 if payload.binding_enabled else 0
        config.notify_assignment = 1 if payload.notify_assignment else 0
        config.notify_due_soon = 1 if payload.notify_due_soon else 0
        config.mention_missing = 1 if payload.mention_missing else 0
        config.allow_query_assignments = 1 if payload.allow_query_assignments else 0
        config.allow_query_scores = 1 if payload.allow_query_scores else 0
        config.bot_chat_mode = payload.bot_chat_mode
        config.bot_chat_enabled = 1 if payload.bot_chat_enabled else 0
        config.bot_chat_max_chars = payload.bot_chat_max_chars
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(config)
    return _view(config, class_id)


def test_config(db: Session, current: CurrentUser, *, class_id: int) -> dict[str, Any]:
    require_active_class(db, class_id, current.user_id)
    config = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()
    if config is None:
        raise AppException(ErrorCode.VALIDATION_ERROR, "请先保存机器人配置")
    app_id = (_settings.qq_bot_app_id or "").strip()
    credential = (_settings.qq_bot_app_secret or "").strip()
    if not app_id or not credential:
        raise AppException(
            ErrorCode.INTERNAL_ERROR, "未配置 QQ_BOT_APP_ID/QQ_BOT_APP_SECRET"
        )

    ok = False
    message = "连接失败"
    expires_in: int | None = None
    try:
        token_data = qq_client.get_app_access_token()
        ok = bool(token_data.get("access_token"))
        if ok:
            message = "连接成功"
            raw = token_data.get("expires_in")
            expires_in = int(raw) if raw is not None else None
        else:
            message = str(token_data.get("message") or "QQ 返回失败")[:200]
    except qq_client.QQBotError as exc:
        message = exc.safe_message
    except Exception:  # noqa: BLE001 - 第三方异常绝不透传
        message = "QQ 接口请求失败"

    config.last_check_at = now_naive()
    config.last_check_status = "ok" if ok else "failed"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info(
        "bot test class_id={} app_id_tail={} ok={}",
        class_id,
        app_id[-4:],
        ok,
    )
    return {
        "ok": ok,
        "message": message,
        "expires_in": expires_in,
        "last_check_at": fmt_dt(config.last_check_at),
        "last_check_status": config.last_check_status,
    }


def generate_group_code(
    db: Session, current: CurrentUser, *, class_id: int
) -> dict[str, Any]:
    require_active_class(db, class_id, current.user_id)
    ttl = 600
    try:
        client = _redis()
        code = ""
        for _ in range(10):
            from app.services.code_service import generate_bind_code

            code = generate_bind_code()
            if client.set(
                cache_keys.qq_group_bind_key(code),
                json.dumps({"class_id": class_id, "teacher_id": current.user_id}),
                ex=ttl,
                nx=True,
            ):
                break
        else:
            raise AppException(ErrorCode.INTERNAL_ERROR, "群绑定码生成失败，请重试")
    except redis.RedisError as exc:
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
    expires_at = now().replace(microsecond=0) + timedelta(seconds=ttl)
    return {"code": code, "expires_in": ttl, "expires_at": fmt_dt(expires_at)}


def consume_group_code(code: str) -> dict | None:
    try:
        raw = _redis().getdel(cache_keys.qq_group_bind_key(code))
    except redis.RedisError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return {"class_id": int(data["class_id"]), "teacher_id": int(data.get("teacher_id") or 0)}
    except (TypeError, ValueError, KeyError):
        return None
