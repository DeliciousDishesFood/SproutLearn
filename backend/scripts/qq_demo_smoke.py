"""D3 离线 QQ 全命令 smoke：临时 demo SQLite + fakeredis，不调用真实 QQ。"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.deps import CurrentUser
from app.redis_client import set_redis_client
from app.services import binding_service, bot_chat_service, bot_service
from app.services.qq_bot import handler
from scripts.generate_qq_demo_seed import build_sqlite

TEACHER = CurrentUser(user_id=9001, role="teacher", class_id=None, jti="t", exp=0)
STUDENT = CurrentUser(user_id=9007, role="student", class_id=9001, jti="s", exp=0)


def event(content, *, group=None, openid="teacher-demo"):
    d = {"content": content, "author": {"member_openid" if group else "user_openid": openid}}
    if group:
        d["group_openid"] = group
    return {"t": "GROUP_AT_MESSAGE_CREATE" if group else "C2C_MESSAGE_CREATE", "d": d}


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "demo.db"
        build_sqlite(path)
        engine = create_engine(f"sqlite:///{path}")
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        set_redis_client(fakeredis.FakeRedis(decode_responses=True))
        db = Session()
        try:
            code = bot_service.generate_group_code(db, TEACHER, class_id=9001)["code"]
            reply = handler.handle_event(db, event(f"绑定群 {code}", group="demo-group"))
            assert reply and "教师身份已绑定" in reply["content"]
            print("OK teacher 绑定群")

            for command, needle in (("作业", "4/10"), ("作业情况", "未交（6）"), ("催交", "未交"), ("作业通知", "【新作业】"), ("帮助", "可用教师命令")):
                reply = handler.handle_event(db, event(command, group="demo-group"))
                assert reply and needle in reply["content"], (command, reply)
                print(f"OK teacher {command}: {reply['content'].splitlines()[0]}")

            code = binding_service.generate_qq_code(STUDENT)["code"]
            reply = handler.handle_event(db, event(f"绑定 {code}", openid="student-demo"))
            assert reply and "已绑定" in reply["content"]
            print("OK student 绑定")
            for command, needle in (("作业", "第一次作业"), ("成绩", "成绩")):
                reply = handler.handle_event(db, event(command, openid="student-demo"))
                assert reply and needle in reply["content"], (command, reply)
                print(f"OK student {command}: {reply['content'].splitlines()[0]}")
            reply = handler.handle_event(db, event("解绑", openid="student-demo"))
            assert reply and "已解除绑定" in reply["content"]
            print("OK student 解绑")

            captured = []

            def fake_race(router, messages, **kwargs):
                captured.extend(messages)
                return SimpleNamespace(content="先比较连接方式和可靠性，再想想三次握手。")

            original_build = bot_chat_service.build_router
            original_race = bot_chat_service._race_chat
            bot_chat_service.build_router = lambda settings: object()
            bot_chat_service._race_chat = fake_race
            try:
                reply = handler.handle_event(db, event("TCP 和 UDP 有什么区别？", group="demo-group"))
                assert reply and "先比较" in reply["content"]
                prompt = "\n".join(item["content"] for item in captured)
                assert "三次握手" in prompt
                second = handler.handle_event(db, event("什么是三次握手？", group="demo-group"))
                assert second and "10 秒" in second["content"]
                print("OK AI 知识上下文 + 10 秒限流")
            finally:
                bot_chat_service.build_router = original_build
                bot_chat_service._race_chat = original_race

            print("RESULT: PASS")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"RESULT: FAIL {type(exc).__name__}: {exc}")
            return 1
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
