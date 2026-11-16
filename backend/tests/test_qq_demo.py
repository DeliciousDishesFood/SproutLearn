"""D3 离线 demo：直接回放 QQ handler，不调用真实 QQ。"""

from __future__ import annotations

from types import SimpleNamespace

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.deps import CurrentUser
from app.models.paper import Paper
from app.redis_client import reset_redis_client, set_redis_client
from app.services import binding_service, bot_chat_service, bot_service
from app.services.qq_bot import handler, notifier
from app.services.qq_bot import client as qq_client
from scripts.generate_qq_demo_seed import build_sqlite

TEACHER = CurrentUser(user_id=9001, role="teacher", class_id=None, jti="t", exp=0)
STUDENT = CurrentUser(user_id=9007, role="student", class_id=9001, jti="s", exp=0)


@pytest.fixture()
def demo_db(tmp_path):
    path = tmp_path / "demo.db"
    build_sqlite(path)
    engine = create_engine(f"sqlite:///{path}")
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    fake = fakeredis.FakeRedis(decode_responses=True)
    set_redis_client(fake)
    db = Session()
    try:
        yield db, fake
    finally:
        db.close()
        reset_redis_client()
        engine.dispose()


def _event(t, content, *, group=None, openid="teacher-demo"):
    d = {"content": content, "author": {"member_openid" if group else "user_openid": openid}}
    if group:
        d["group_openid"] = group
    return {"t": t, "d": d}


def test_teacher_group_binding_and_commands(demo_db):
    db, _fake = demo_db
    code = bot_service.generate_group_code(db, TEACHER, class_id=9001)["code"]
    reply = handler.handle_event(
        db,
        _event("GROUP_AT_MESSAGE_CREATE", f"绑定群 {code}", group="demo-group"),
    )
    assert reply and "教师身份已绑定" in reply["content"]
    assert reply["group_openid"] == "demo-group"
    from app.models.class_bot_config import ClassBotConfig

    cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == 9001).one()
    assert cfg.teacher_openid == "teacher-demo"

    for command, needle in (
        ("作业", "4/10"),
        ("作业情况", "未交（6）"),
        ("催交", "未交"),
        ("作业通知", "【新作业】"),
        ("帮助", "可用教师命令"),
    ):
        reply = handler.handle_event(
            db,
            _event("GROUP_AT_MESSAGE_CREATE", command, group="demo-group"),
        )
        assert reply and needle in reply["content"], (command, reply)


def test_student_binding_assignments_scores_and_unbind(demo_db):
    db, _fake = demo_db
    code = binding_service.generate_qq_code(STUDENT)["code"]
    reply = handler.handle_event(
        db, _event("C2C_MESSAGE_CREATE", f"绑定 {code}", openid="student-demo")
    )
    assert reply and "已绑定" in reply["content"]
    for command, needle in (("作业", "第一次作业"), ("成绩", "成绩")):
        reply = handler.handle_event(
            db, _event("C2C_MESSAGE_CREATE", command, openid="student-demo")
        )
        assert reply and needle in reply["content"], (command, reply)
    reply = handler.handle_event(
        db, _event("C2C_MESSAGE_CREATE", "解绑", openid="student-demo")
    )
    assert reply and "已解除绑定" in reply["content"]


def test_ai_unknown_uses_demo_chunk_and_rate_limit(demo_db, monkeypatch):
    db, _fake = demo_db
    code = bot_service.generate_group_code(db, TEACHER, class_id=9001)["code"]
    handler.handle_event(db, _event("GROUP_AT_MESSAGE_CREATE", f"绑定群 {code}", group="demo-group"))
    captured = []

    def fake_race(router, messages, **kwargs):
        captured.extend(messages)
        return SimpleNamespace(content="引导：先比较 TCP 和 UDP 的连接与可靠性。")

    monkeypatch.setattr(bot_chat_service, "build_router", lambda settings: object())
    monkeypatch.setattr(bot_chat_service, "_race_chat", fake_race)
    event = _event(
        "GROUP_AT_MESSAGE_CREATE",
        "TCP 和 UDP 有什么区别？",
        group="demo-group",
    )
    reply = handler.handle_event(db, event)
    assert reply and "引导" in reply["content"]
    prompt = "\n".join(item["content"] for item in captured)
    assert "TCP" in prompt and "三次握手" in prompt
    second = handler.handle_event(
        db,
        _event("GROUP_AT_MESSAGE_CREATE", "什么是三次握手？", group="demo-group"),
    )
    assert second and "10 秒" in second["content"]


def test_assignment_notice_idempotent(demo_db, monkeypatch):
    db, _fake = demo_db
    from app.models.class_bot_config import ClassBotConfig
    from app.models.bot_notice import BotNotice

    cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == 9001).one()
    cfg.group_openid = "demo-group"
    cfg.notify_assignment = 1
    db.commit()
    paper = db.get(Paper, 9201)
    sent = []
    monkeypatch.setattr(notifier, "get_settings", lambda: SimpleNamespace(qq_bot_enabled=True))
    monkeypatch.setattr(
        qq_client,
        "send_group_message",
        lambda group, content, **kwargs: sent.append((group, content)) or {"message_id": "m1"},
    )
    assert notifier.send_assignment_published(db, paper) == "sent"
    assert notifier.send_assignment_published(db, paper) == "skipped"
    assert len(sent) == 1
    assert db.query(BotNotice).filter(BotNotice.paper_id == 9201, BotNotice.kind == "assignment").count() == 1
