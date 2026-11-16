"""QQ 官方 WebSocket 网关：心跳、重连、READY / 群@ / C2C 事件。"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import httpx
from loguru import logger
from websockets import connect

from app.config import get_settings
from app.services.bot_chat_service import split_for_qq
from app.services.qq_bot import client

GATEWAY_URL = "https://api.sgroup.qq.com/gateway"
INTENTS = 1 << 25  # GROUP_AT_MESSAGE_CREATE / C2C 消息事件
RECONNECT_SECONDS = 5


async def fetch_gateway_url(token: str) -> str:
    configured = (get_settings().qq_bot_gateway_url or "").strip()
    if configured:
        return configured
    try:
        response = await asyncio.to_thread(
            httpx.get,
            GATEWAY_URL,
            headers={"Authorization": f"QQBot {token}"},
            timeout=8.0,
        )
        data = response.json()
        url = data.get("url") if isinstance(data, dict) else None
        return str(url or "wss://api.sgroup.qq.com/websocket")
    except Exception:  # noqa: BLE001
        return "wss://api.sgroup.qq.com/websocket"


async def _heartbeat(ws, interval: float, state: dict[str, Any]) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await ws.send(json.dumps({"op": 1, "d": state.get("seq")}))
        except Exception:  # noqa: BLE001
            return


async def run_gateway(on_event: Callable[[dict[str, Any]], Any]) -> None:
    while True:
        token = ""
        try:
            token = client.get_app_access_token()["access_token"]
            url = await fetch_gateway_url(token)
            async with connect(url, ping_interval=None, close_timeout=5) as ws:
                hello = json.loads(await ws.recv())
                interval = float((hello.get("d") or {}).get("heartbeat_interval", 30000)) / 1000
                state: dict[str, Any] = {"seq": None}
                hb = asyncio.create_task(_heartbeat(ws, max(1.0, interval), state))
                await ws.send(
                    json.dumps(
                        {
                            "op": 2,
                            "d": {
                                "token": f"QQBot {token}",
                                "intents": INTENTS,
                                "shard": [0, 1],
                                "properties": {},
                            },
                        }
                    )
                )
                try:
                    async for raw in ws:
                        payload = json.loads(raw)
                        if payload.get("s") is not None:
                            state["seq"] = payload["s"]
                        op = payload.get("op")
                        if op == 10:
                            continue
                        if op == 0 and payload.get("t") == "READY":
                            logger.info("qq gateway READY")
                            continue
                        if op == 0 and payload.get("t") in (
                            "GROUP_AT_MESSAGE_CREATE",
                            "C2C_MESSAGE_CREATE",
                        ):
                            event_d = payload.get("d") or {}
                            reply = await asyncio.to_thread(on_event, payload)
                            if reply:
                                _attach_event_ref(reply, event_d)
                                await _send_reply(reply)
                finally:
                    hb.cancel()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - 网关失败重连
            logger.warning("qq gateway disconnected: {}", type(exc).__name__)
            await asyncio.sleep(RECONNECT_SECONDS)


def _attach_event_ref(reply: dict[str, Any], event_d: dict[str, Any]) -> dict[str, Any]:
    reply["msg_id"] = str(event_d.get("id") or "")
    reply["msg_seq"] = 1
    return reply


async def _send_reply(reply: dict[str, Any]) -> None:
    content = reply.get("content") or ""
    group = reply.get("group_openid")
    user = reply.get("user_openid")
    mentions = [item for item in (reply.get("mention_openids") or []) if item]
    chunks = split_for_qq(content)
    if not chunks:
        return
    base_seq = int(reply.get("msg_seq", 1) or 1)
    try:
        if group:
            try:
                for index, chunk in enumerate(chunks):
                    await asyncio.to_thread(
                        client.send_group_message,
                        group,
                        chunk,
                        msg_id=reply.get("msg_id"),
                        msg_seq=base_seq + index,
                        mention_openids=mentions if index == 0 else [],
                    )
            except client.QQBotError:
                if not mentions:
                    raise
                # QQ 不支持 @ 时降级为纯名单，不把主动消息错误当成功
                logger.warning("qq mention failed, fallback to plain list")
                for index, chunk in enumerate(chunks):
                    await asyncio.to_thread(
                        client.send_group_message,
                        group,
                        chunk + ("\n（@ 失败，已发名单）" if index == len(chunks) - 1 else ""),
                        msg_id=reply.get("msg_id"),
                        msg_seq=base_seq + index,
                        mention_openids=[],
                    )
        elif user:
            for index, chunk in enumerate(chunks):
                await asyncio.to_thread(
                    client.send_c2c_message,
                    user,
                    chunk,
                    msg_id=reply.get("msg_id"),
                    msg_seq=base_seq + index,
                )
    except client.QQBotError as exc:
        logger.warning("qq reply failed: {}", exc.safe_message)
