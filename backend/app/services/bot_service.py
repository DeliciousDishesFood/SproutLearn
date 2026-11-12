"""M3.3 班级 QQ 机器人配置：保存/读取/凭证连通性测试。"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.class_bot_config import ClassBotConfig
from app.schemas.bot import BotConfigUpdateRequest
from app.services.class_service import require_owned_class
from app.utils.bot_crypto import decrypt_secret, encrypt_secret, secret_tail
from app.utils.time import fmt_dt, now_naive

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
TIMEOUT_SECONDS = 8.0


def _empty(class_id: int) -> dict[str, Any]:
    return {
        "class_id": class_id,
        "app_id": None,
        "callback_url": None,
        "enabled": False,
        "last_check_at": None,
        "last_check_status": "never",
        "has_secret": False,
        "secret_tail": None,
    }


def _view(config: ClassBotConfig | None, class_id: int) -> dict[str, Any]:
    if config is None:
        return _empty(class_id)
    tail = secret_tail(decrypt_secret(config.app_secret_cipher))
    return {
        "class_id": config.class_id,
        "app_id": config.app_id,
        "callback_url": config.callback_url,
        "enabled": bool(config.enabled),
        "last_check_at": fmt_dt(config.last_check_at),
        "last_check_status": config.last_check_status or "never",
        "has_secret": bool(config.app_secret_cipher),
        "secret_tail": tail,
    }


def get_config(
    db: Session, current: CurrentUser, *, class_id: int
) -> dict[str, Any]:
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
    require_owned_class(db, class_id, current.user_id)
    config = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()
    secret = payload.app_secret or ""
    if config is None and not secret:
        raise AppException(ErrorCode.VALIDATION_ERROR, "首次保存必须填写 AppSecret")
    if config is None:
        config = ClassBotConfig(
            class_id=class_id,
            app_id=payload.app_id,
            app_secret_cipher=encrypt_secret(secret),
            callback_url=payload.callback_url,
            enabled=1 if payload.enabled else 0,
            last_check_status="never",
            created_by=current.user_id,
        )
        db.add(config)
    else:
        config.app_id = payload.app_id
        config.callback_url = payload.callback_url
        config.enabled = 1 if payload.enabled else 0
        if secret:
            config.app_secret_cipher = encrypt_secret(secret)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(config)
    return _view(config, class_id)


def _qq_error(data: dict[str, Any]) -> tuple[str | None, str]:
    code = data.get("code") or data.get("errcode")
    message = data.get("message") or data.get("msg") or "QQ 返回失败"
    return (str(code) if code is not None else None, str(message)[:200])


def test_config(
    db: Session, current: CurrentUser, *, class_id: int
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    config = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()
    if config is None:
        raise AppException(ErrorCode.VALIDATION_ERROR, "请先保存机器人配置")
    secret = decrypt_secret(config.app_secret_cipher)
    if not secret:
        raise AppException(ErrorCode.INTERNAL_ERROR, "机器人 Secret 无法解密，请重新保存")

    ok = False
    message = "连接失败"
    expires_in: int | None = None
    try:
        response = httpx.post(
            TOKEN_URL,
            json={"appId": config.app_id, "clientSecret": secret},
            timeout=TIMEOUT_SECONDS,
        )
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code == 200 and isinstance(data, dict) and data.get("access_token"):
            ok = True
            message = "连接成功"
            raw_expires = data.get("expires_in")
            try:
                expires_in = int(raw_expires) if raw_expires is not None else None
            except (TypeError, ValueError):
                expires_in = None
        else:
            code, detail = _qq_error(data if isinstance(data, dict) else {})
            message = f"QQ 错误码 {code}: {detail}" if code else detail
    except httpx.TimeoutException:
        message = "请求超时（8s）"
    except httpx.HTTPError:
        message = "QQ 接口连接失败"
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
        config.app_id[-4:],
        ok,
    )
    return {
        "ok": ok,
        "message": message,
        "expires_in": expires_in,
        "last_check_at": fmt_dt(config.last_check_at),
        "last_check_status": config.last_check_status,
    }
