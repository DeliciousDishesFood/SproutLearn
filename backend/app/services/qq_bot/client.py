"""QQ 官方机器人 HTTP 客户端：token 内存缓存、群/私聊消息、8s 超时。"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from loguru import logger

from app.config import get_settings

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API_BASE = "https://api.sgroup.qq.com"
TIMEOUT_SECONDS = 8.0


class QQBotError(Exception):
    """QQ 接口错误；safe_message 不含 token/secret。"""

    def __init__(self, safe_message: str, *, code: str | None = None, status: int | None = None):
        self.safe_message = safe_message
        self.code = code
        self.status = status
        super().__init__(safe_message)


_lock = threading.Lock()
_token: str | None = None
_token_expires_at = 0.0


def _error_from(data: Any) -> tuple[str | None, str]:
    if not isinstance(data, dict):
        return None, "QQ 返回非 JSON"
    code = data.get("code") or data.get("errcode")
    message = data.get("message") or data.get("msg") or "QQ 请求失败"
    return (str(code) if code is not None else None, str(message)[:200])


def get_app_access_token(*, force: bool = False) -> dict[str, Any]:
    global _token, _token_expires_at
    settings = get_settings()
    app_id = (settings.qq_bot_app_id or "").strip()
    secret = (settings.qq_bot_app_secret or "").strip()
    if not app_id or not secret:
        raise QQBotError("未配置 QQ_BOT_APP_ID/QQ_BOT_APP_SECRET")
    with _lock:
        if not force and _token and time.monotonic() < _token_expires_at - 30:
            return {"access_token": _token, "expires_in": int(_token_expires_at - time.monotonic())}
        try:
            response = httpx.post(
                TOKEN_URL,
                json={"appId": app_id, "clientSecret": secret},
                timeout=TIMEOUT_SECONDS,
            )
            data = response.json()
        except httpx.TimeoutException as exc:
            raise QQBotError("QQ token 请求超时（8s）") from exc
        except httpx.HTTPError as exc:
            raise QQBotError("QQ token 接口连接失败") from exc
        except ValueError as exc:
            raise QQBotError("QQ token 返回非 JSON") from exc
        if response.status_code != 200 or not isinstance(data, dict) or not data.get("access_token"):
            code, message = _error_from(data)
            raise QQBotError(
                f"QQ 错误码 {code}: {message}" if code else message,
                code=code,
                status=response.status_code,
            )
        token = str(data["access_token"])
        expires = int(data.get("expires_in") or 7200)
        _token = token
        _token_expires_at = time.monotonic() + expires
        logger.info("qq token refreshed app_id_tail={} expires_in={}", app_id[-4:], expires)
        return {"access_token": token, "expires_in": expires}


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}


def send_group_message(
    group_openid: str,
    content: str,
    *,
    msg_id: str | None = None,
    msg_seq: int = 1,
    mention_openids: list[str] | None = None,
) -> dict[str, Any]:
    token = get_app_access_token()["access_token"]
    body: dict[str, Any] = {"content": content, "msg_type": 0}
    if msg_id:
        body["msg_id"] = msg_id
        body["msg_seq"] = int(msg_seq or 1)
    mentions = [openid for openid in (mention_openids or []) if openid]
    if mentions:
        body["content"] = "".join(f"<@{openid}> " for openid in mentions) + content
    try:
        response = httpx.post(
            f"{API_BASE}/v2/groups/{group_openid}/messages",
            headers=_auth_headers(token),
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
    except httpx.TimeoutException as exc:
        raise QQBotError("QQ 群消息超时（8s）") from exc
    except httpx.HTTPError as exc:
        raise QQBotError("QQ 群消息连接失败") from exc
    except ValueError as exc:
        raise QQBotError("QQ 群消息返回非 JSON") from exc
    if response.status_code not in (200, 201) or not isinstance(data, dict):
        code, message = _error_from(data)
        raise QQBotError(
            f"QQ 错误码 {code}: {message}" if code else message,
            code=code,
            status=response.status_code,
        )
    return {
        "message_id": str(data.get("id") or ""),
        "mentions_supported": bool(mentions),
        "raw_keys": sorted(data.keys()),
    }


def send_c2c_message(
    user_openid: str,
    content: str,
    *,
    msg_id: str | None = None,
    msg_seq: int = 1,
) -> dict[str, Any]:
    token = get_app_access_token()["access_token"]
    body: dict[str, Any] = {"content": content, "msg_type": 0}
    if msg_id:
        body["msg_id"] = msg_id
        body["msg_seq"] = int(msg_seq or 1)
    try:
        response = httpx.post(
            f"{API_BASE}/v2/users/{user_openid}/messages",
            headers=_auth_headers(token),
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
    except httpx.TimeoutException as exc:
        raise QQBotError("QQ 私聊消息超时（8s）") from exc
    except httpx.HTTPError as exc:
        raise QQBotError("QQ 私聊消息连接失败") from exc
    except ValueError as exc:
        raise QQBotError("QQ 私聊消息返回非 JSON") from exc
    if response.status_code not in (200, 201) or not isinstance(data, dict):
        code, message = _error_from(data)
        raise QQBotError(
            f"QQ 错误码 {code}: {message}" if code else message,
            code=code,
            status=response.status_code,
        )
    return {"message_id": str(data.get("id") or "")}
