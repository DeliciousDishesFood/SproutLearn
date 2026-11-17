"""QQ 演示启动预检（D2）：默认离线，不启动长期进程。"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import get_settings
from app.database import engine
from app.redis_client import redis_ping, set_redis_client
from app.services.qq_bot import client as qq_client
from app.services.qq_bot.gateway import fetch_gateway_url

DEMO_CLASS = "C26A79"


def _db_check(engine) -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM `class` WHERE class_code=:code"), {"code": DEMO_CLASS}
            ).first()
            if row is None:
                return False, "demo class 不存在"
            cfg = conn.execute(
                text(
                    "SELECT enabled, group_openid, binding_enabled, notify_assignment, "
                    "notify_due_soon, allow_query_assignments, allow_query_scores, "
                    "bot_chat_enabled, bot_chat_mode, bot_chat_max_chars "
                    "FROM class_bot_config WHERE class_id=:id"
                ),
                {"id": row[0]},
            ).first()
            if cfg is None:
                return False, "demo class_bot_config 不存在"
            notice = conn.execute(
                text(
                    "SELECT status, reason, error_code, attempt_count, error_message "
                    "FROM bot_notice WHERE class_id=:id ORDER BY id DESC LIMIT 1"
                ),
                {"id": row[0]},
            ).first()
            notice_text = "none"
            if notice is not None:
                notice_text = (
                    f"status={notice[0]} reason={notice[1]} code={notice[2]} "
                    f"attempts={notice[3]} message={notice[4] or '-'}"
                )
            return True, (
                f"ok class_id={row[0]} bot_enabled={cfg[0]} group_tail={(cfg[1] or '')[-4:] or '-'} "
                f"binding={cfg[2]} notify_assignment={cfg[3]} notify_due={cfg[4]} "
                f"queries={cfg[5]}/{cfg[6]} chat={cfg[7]}/{cfg[8]}/{cfg[9]} last_notice=[{notice_text}]"
            )
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def _redis_check() -> tuple[bool, str]:
    try:
        return redis_ping() == "ok", redis_ping()
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__


def _deps_check() -> tuple[bool, str]:
    modules = [
        "pdfplumber",
        "pypdf",
        "docx",
        "pptx",
        "openpyxl",
        "xlrd",
        "fakeredis",
    ]
    missing = []
    for name in modules:
        try:
            __import__(name)
        except Exception:  # noqa: BLE001
            missing.append(name)
    return not missing, "ok" if not missing else f"missing={missing}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--fake-redis", action="store_true")
    parser.add_argument("--active-send", "--send-test", dest="active_send", action="store_true", help="显式发送一条真实主动消息，默认关闭")
    args = parser.parse_args()
    settings = get_settings()
    failed = False

    app_id = (settings.qq_bot_app_id or "").strip()
    print(f"env QQ_BOT_ENABLED={bool(settings.qq_bot_enabled)}")
    print(f"env QQ_BOT_APP_ID={bool(app_id)} tail={app_id[-4:] if app_id else '-'}")
    print(f"env QQ_BOT_APP_SECRET={bool(settings.qq_bot_app_secret)}")
    print(f"env QQ_BOT_GATEWAY_URL={bool(settings.qq_bot_gateway_url)}")

    db_engine = create_engine(f"sqlite:///{args.sqlite}") if args.sqlite else engine
    if args.fake_redis:
        import fakeredis
        set_redis_client(fakeredis.FakeRedis(decode_responses=True))
    print(f"mode={'sqlite' if args.sqlite else 'configured-db'} redis={'fake' if args.fake_redis else 'configured'}")
    db_ok, db_msg = _db_check(db_engine)
    print(f"db {db_ok} {db_msg}")
    print("active_message_hint=token/gateway 正常不代表群主动消息已授权；40034105 需群主在手机 QQ 群设置开启机器人主动发言")
    failed = failed or not db_ok

    redis_ok, redis_msg = _redis_check()
    print(f"redis {redis_ok} {redis_msg}")
    failed = failed or not redis_ok

    deps_ok, deps_msg = _deps_check()
    print(f"deps {deps_ok} {deps_msg}")
    failed = failed or not deps_ok

    providers = {
        name: bool(getattr(settings, f"{name}_api_key", ""))
        for name in settings.llm_chain_list
    }
    print(f"llm_providers={providers}")
    failed = failed or not any(providers.values())

    if args.online:
        started = time.perf_counter()
        try:
            data = qq_client.get_app_access_token()
            token_ok = bool(data.get("access_token"))
            url = asyncio.run(fetch_gateway_url(data["access_token"])) if token_ok else None
            elapsed = round((time.perf_counter() - started) * 1000)
            print(f"online token_ok={token_ok} gateway={bool(url)} elapsed_ms={elapsed}")
            failed = failed or not token_ok
        except Exception as exc:  # noqa: BLE001
            print(f"online FAILED {type(exc).__name__} elapsed_ms={round((time.perf_counter()-started)*1000)}")
            failed = True

    if args.active_send:
        started = time.perf_counter()
        if not args.online:
            print("active_send FAILED: 需要同时传 --online")
            failed = True
        elif os.environ.get("QQ_ACTIVE_SEND_CONFIRM") != "YES":
            print("active_send REFUSED: 需显式设置 QQ_ACTIVE_SEND_CONFIRM=YES")
            failed = True
        else:
            try:
                with db_engine.connect() as conn:
                    row = conn.execute(
                        text(
                            "SELECT c.id, cfg.group_openid FROM `class` c "
                            "JOIN class_bot_config cfg ON cfg.class_id=c.id "
                            "WHERE c.class_code=:code"
                        ),
                        {"code": DEMO_CLASS},
                    ).first()
                if row is None or not row[1]:
                    print("active_send FAILED: demo 群未绑定")
                    failed = True
                else:
                    result = qq_client.send_group_message(
                        row[1], "【青芽】主动消息权限测试，收到请忽略。"
                    )
                    print(
                        f"active_send OK message_id={bool(result.get('message_id'))} "
                        f"elapsed_ms={round((time.perf_counter()-started)*1000)}"
                    )
            except qq_client.QQBotError as exc:
                print(
                    f"active_send FAILED code={exc.code} status={exc.status} "
                    f"elapsed_ms={round((time.perf_counter()-started)*1000)}"
                )
                failed = True
            except Exception as exc:  # noqa: BLE001
                print(f"active_send FAILED {type(exc).__name__}")
                failed = True

    if args.worker:
        print("worker command: python -m app.qq_bot_worker")
        print("worker log acceptance: qq gateway READY")
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
