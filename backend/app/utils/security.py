"""安全工具：bcrypt 密码哈希与 JWT 签发/校验。"""

from __future__ import annotations

from uuid import uuid4

import bcrypt
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import get_settings
from app.utils.time import utc_now_epoch


class TokenExpiredError(Exception):
    """JWT 已过期（与签名错误区分，便于返回 40102）。"""


class TokenInvalidError(Exception):
    """JWT 无法解析或签名错误。"""


_dummy_hash: bytes | None = None


def hash_password(password: str) -> str:
    """bcrypt 哈希；cost 来自 BCRYPT_ROUNDS。"""
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """bcrypt 比对；空哈希直接 False（调用方应先做等时 dummy 比对）。"""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def burn_password_check(password: str) -> None:
    """账号不存在时也执行一次 bcrypt，降低账号枚举的时序差异。"""
    global _dummy_hash
    if _dummy_hash is None:
        rounds = get_settings().bcrypt_rounds
        _dummy_hash = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt(rounds=rounds))
    bcrypt.checkpw(password.encode("utf-8"), _dummy_hash)


def create_access_token(
    *, user_id: int, role: str, class_id: int | None, auth_version: int = 1
) -> tuple[str, str, int]:
    """签发 JWT，返回 (token, jti, exp)。payload 字段严格按契约 §4.4。"""
    settings = get_settings()
    jti = uuid4().hex
    iat = utc_now_epoch()
    exp = iat + settings.access_token_seconds
    payload = {
        "sub": str(user_id),
        "role": role,
        "class_id": class_id,
        "auth_version": int(auth_version),
        "iat": iat,
        "exp": exp,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, exp


def decode_access_token(token: str) -> dict:
    """校验签名与过期；过期抛 TokenExpiredError，其余非法抛 TokenInvalidError。"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("token expired") from exc
    except InvalidTokenError as exc:
        raise TokenInvalidError("invalid token") from exc


def remaining_ttl(exp: int) -> int:
    """JWT 剩余有效期（秒），最小 0。"""
    return max(0, int(exp) - utc_now_epoch())
