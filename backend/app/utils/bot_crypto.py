"""M3.3 机器人 AppSecret 的 Fernet 加密工具（密钥只来自 BOT_SECRET_KEY）。"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.exceptions import AppException, ErrorCode


def _fernet() -> Fernet:
    key = (get_settings().bot_secret_key or "").strip()
    if not key:
        raise AppException(ErrorCode.INTERNAL_ERROR, "未配置 BOT_SECRET_KEY")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise AppException(ErrorCode.INTERNAL_ERROR, "未配置 BOT_SECRET_KEY") from exc


def encrypt_secret(secret: str) -> bytes:
    return _fernet().encrypt(secret.encode("utf-8"))


def decrypt_secret(cipher: bytes | None) -> str | None:
    if not cipher:
        return None
    try:
        return _fernet().decrypt(cipher).decode("utf-8")
    except InvalidToken:
        return None
    except AppException:
        return None


def secret_tail(secret: str | None) -> str | None:
    if not secret:
        return None
    return secret[-4:] if len(secret) >= 4 else secret
