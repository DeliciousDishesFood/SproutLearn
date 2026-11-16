"""QQ 演示启动预检（D2）：默认离线，不启动长期进程。"""

from __future__ import annotations

import argparse
import asyncio
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
                text("SELECT enabled, group_openid FROM class_bot_config WHERE class_id=:id"),
                {"id": row[0]},
            ).first()
            if cfg is None:
                return False, "demo class_bot_config 不存在"
            return True, f"ok class_id={row[0]} bot_enabled={cfg[0]} group={bool(cfg[1])}"
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

    if args.worker:
        print("worker command: python -m app.qq_bot_worker")
        print("worker log acceptance: qq gateway READY")
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
