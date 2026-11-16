"""M3.4 通知中心、机器人命令、到期幂等与 AI 流式缓存。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

from app.models.answer_record import AnswerRecord
from app.models.bot_notice import BotNotice
from app.models.class_bot_config import ClassBotConfig
from app.models.notification import Notification
from app.models.qq_binding import QqBinding
from app.services import question_service
from app.services import bot_chat_service
from app.services.qq_bot import client as qq_client
from app.services.qq_bot import gateway, handler, notifier, worker
from tests.conftest import auth


def _questions(count=1):
    return [
        {
            "type": "judge",
            "stem": f"M3.4 题 {i}",
            "answer": True,
            "difficulty": "medium",
        }
        for i in range(1, count + 1)
    ]


def _import(client, token, class_id, questions):
    preview = client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "q.json",
                json.dumps(questions, ensure_ascii=False).encode(),
                "application/json",
            )
        },
    )
    assert preview.status_code == 200, preview.text
    commit = client.post(
        f"/api/v1/classes/{class_id}/questions/import/commit",
        headers=auth(token),
        json={"token": preview.json()["data"]["token"]},
    )
    assert commit.status_code == 200, commit.text
    return commit.json()["data"]["question_ids"]


def _paper(client, token, class_id, ids, *, kind="homework", due_at=None):
    payload = {
        "title": "M3.4 作业",
        "mode": "fixed",
        "kind": kind,
        "question_ids": ids,
    }
    if due_at is not None:
        payload["due_at"] = due_at.isoformat()
    response = client.post(
        f"/api/v1/classes/{class_id}/papers", headers=auth(token), json=payload
    )
    assert response.status_code == 200, response.text
    paper = response.json()["data"]
    published = client.post(
        f"/api/v1/papers/{paper['id']}/publish", headers=auth(token)
    )
    assert published.status_code == 200, published.text
    return published.json()["data"]


def test_publish_writes_notification_and_read_flow(client, teacher_token, klass, student):
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(
        client,
        teacher_token,
        klass["id"],
        ids,
        due_at=datetime.now() + timedelta(hours=2),
    )
    assert paper["due_at"]
    listed = client.get("/api/v1/notifications", headers=auth(student["token"]))
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert any(item["type"] == "paper_published" and item["payload"]["paper_id"] == paper["id"] for item in items)
    unread = client.get("/api/v1/notifications/unread-count", headers=auth(student["token"]))
    assert unread.json()["data"]["count"] >= 1
    notification_id = next(item["id"] for item in items if item["type"] == "paper_published")
    for _ in range(2):
        assert client.post(
            f"/api/v1/notifications/{notification_id}/read",
            headers=auth(student["token"]),
        ).status_code == 200
    all_read = client.post("/api/v1/notifications/read-all", headers=auth(student["token"]))
    assert all_read.status_code == 200
    assert client.get(
        "/api/v1/notifications/unread-count", headers=auth(student["token"])
    ).json()["data"]["count"] == 0

    announcement = client.post(
        f"/api/v1/classes/{klass['id']}/announcements",
        headers=auth(teacher_token),
        json={"title": "通知", "body": "明天带书"},
    )
    assert announcement.status_code == 200
    assert announcement.json()["data"]["recipient_count"] >= 1


def test_review_writes_student_notification(client, teacher_token, klass, student):
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(client, teacher_token, klass["id"], ids)
    attempt = client.post(
        f"/api/v1/papers/{paper['id']}/attempts", headers=auth(student["token"])
    ).json()["data"]
    client.put(
        f"/api/v1/attempts/{attempt['id']}/answers/{ids[0]}",
        headers=auth(student["token"]),
        json={"answer": False},
    )
    submitted = client.post(
        f"/api/v1/attempts/{attempt['id']}/submit", headers=auth(student["token"])
    )
    assert submitted.status_code == 200
    with client.testing_session() as db:  # type: ignore[attr-defined]
        record = db.query(AnswerRecord).filter(AnswerRecord.attempt_id == attempt["id"]).one()
        record_id = record.id
    reviewed = client.post(
        f"/api/v1/attempts/{attempt['id']}/reviews",
        headers=auth(teacher_token),
        json={"answer_record_id": record_id, "new_score": 1, "comment": "订正"},
    )
    assert reviewed.status_code == 200, reviewed.text
    notes = client.get(
        "/api/v1/notifications?page_size=50", headers=auth(student["token"])
    ).json()["data"]["items"]
    review_note = next(item for item in notes if item["type"] == "grading_reviewed")
    assert "订正" in review_note["body"]
    assert review_note["target_path"].startswith("/student/attempts/")


def test_bot_commands_binding_group_permissions(client, teacher_token, klass, student):
    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={"app_id": "102000001", "enabled": True, "allow_query_assignments": True},
    )
    assert config.status_code == 200, config.text

    code = client.post("/api/v1/binding/qq-code", headers=auth(student["token"]))
    assert code.status_code == 200
    bind_code = code.json()["data"]["code"]
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "C2C_MESSAGE_CREATE",
                "d": {
                    "content": f"绑定 {bind_code}",
                    "author": {"user_openid": "student-openid-m34"},
                },
            },
        )
    assert reply and "已绑定" in reply["content"]

    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(client, teacher_token, klass["id"], ids)
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "C2C_MESSAGE_CREATE",
                "d": {
                    "content": "作业",
                    "author": {"user_openid": "student-openid-m34"},
                },
            },
        )
    assert reply and paper["title"] in reply["content"]

    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.allow_query_assignments = 0
        db.commit()
        reply = handler.handle_event(
            db,
            {
                "t": "C2C_MESSAGE_CREATE",
                "d": {
                    "content": "作业",
                    "author": {"user_openid": "student-openid-m34"},
                },
            },
        )
    assert reply and "未开放" in reply["content"]

    group_code = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/group-code",
        headers=auth(teacher_token),
    ).json()["data"]["code"]
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": f"绑定群 {group_code}",
                    "group_openid": "group-openid-m34",
                    "author": {"member_openid": "teacher-openid"},
                },
            },
        )
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        assert cfg.group_openid == "group-openid-m34"
    assert reply and "本群已绑定班级" in reply["content"]


def test_assignment_group_notice_failure_records_failed(client, teacher_token, klass, student, monkeypatch):
    from types import SimpleNamespace

    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={"app_id": "102000001", "enabled": True, "notify_assignment": True},
    )
    assert config.status_code == 200
    with client.testing_session() as db:  # type: ignore[attr-defined]
        row = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        row.group_openid = "group-notice-m34"
        db.commit()
    monkeypatch.setattr(notifier, "get_settings", lambda: SimpleNamespace(qq_bot_enabled=True))
    sent = []

    def fake_send(group_openid, content, **kwargs):
        sent.append((group_openid, content))
        raise qq_client.QQBotError("QQ 错误码 40034105: 主动消息失败, 无权限")

    monkeypatch.setattr(qq_client, "send_group_message", fake_send)
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(
        client,
        teacher_token,
        klass["id"],
        ids,
        due_at=datetime.now() + timedelta(hours=2),
    )
    assert sent
    content = sent[0][1]
    assert content.startswith("【新作业】")
    assert "开始：" in content and "截止：" in content and "请到青芽完成。" in content
    with client.testing_session() as db:  # type: ignore[attr-defined]
        notice = db.query(BotNotice).filter(
            BotNotice.paper_id == paper["id"], BotNotice.kind == "assignment"
        ).one()
        assert notice.status == "failed"
        assert notice.message_id is None
        # 站内通知不因主动群消息失败而丢失
        notes = db.query(Notification).filter(
            Notification.type == "paper_published",
            Notification.class_id == klass["id"],
        ).all()
        assert notes


def test_due_reminder_is_idempotent(client, teacher_token, klass, student, monkeypatch):
    monkeypatch.setattr(worker, "SessionLocal", client.testing_session)  # type: ignore[attr-defined]
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(
        client,
        teacher_token,
        klass["id"],
        ids,
        due_at=datetime.now() + timedelta(hours=1),
    )
    worker._due_reminders()
    worker._due_reminders()
    with client.testing_session() as db:  # type: ignore[attr-defined]
        notices = db.query(BotNotice).filter(BotNotice.paper_id == paper["id"]).all()
        due_notes = db.query(Notification).filter(
            Notification.type == "paper_due_soon",
            Notification.recipient_id == student["user"]["id"],
        ).all()
        assert len(notices) == 1
        assert len(due_notes) == 1


def test_explain_cache_and_llm_engine(client, teacher_token, klass, monkeypatch):
    ids = _import(client, teacher_token, klass["id"], _questions())
    question_id = ids[0]
    calls = []

    def chunks(question):
        calls.append(question.id)
        yield "AI 第一段。"
        yield "AI 第二段。"

    monkeypatch.setattr(question_service, "_ai_explain_iter", chunks)
    with client.stream(
        "POST",
        f"/api/v1/questions/{question_id}/explain/stream",
        headers=auth(teacher_token),
    ) as response:
        text = response.read().decode()
    assert "AI 第一段。" in text
    assert '"engine": "llm"' in text
    assert len(calls) == 1

    monkeypatch.setattr(
        question_service,
        "_ai_explain_iter",
        lambda question: (_ for _ in ()).throw(AssertionError("cache miss")),
    )
    with client.stream(
        "POST",
        f"/api/v1/questions/{question_id}/explain/stream",
        headers=auth(teacher_token),
    ) as response:
        cached_text = response.read().decode()
    assert "cached" in cached_text
    assert "AI 第一段。" in cached_text and "AI 第二段。" in cached_text


class _QQResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_passive_group_reply_carries_msg_id_and_seq(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _QQResponse(200, {"id": "reply-1"})

    monkeypatch.setattr(qq_client, "get_app_access_token", lambda: {"access_token": "test-token"})
    monkeypatch.setattr(qq_client.httpx, "post", fake_post)
    result = qq_client.send_group_message("group-1", "可用命令", msg_id="event-1", msg_seq=1)
    assert result["message_id"] == "reply-1"
    body = calls[0][1]["json"]
    assert body["msg_id"] == "event-1"
    assert body["msg_seq"] == 1
    assert "Authorization" in calls[0][1]["headers"]


def test_passive_c2c_reply_carries_msg_id_and_seq(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _QQResponse(200, {"id": "reply-2"})

    monkeypatch.setattr(qq_client, "get_app_access_token", lambda: {"access_token": "test-token"})
    monkeypatch.setattr(qq_client.httpx, "post", fake_post)
    result = qq_client.send_c2c_message("user-1", "可用命令", msg_id="event-2", msg_seq=1)
    assert result["message_id"] == "reply-2"
    body = calls[0][1]["json"]
    assert body["msg_id"] == "event-2"
    assert body["msg_seq"] == 1


def test_gateway_send_reply_uses_event_message_ref(monkeypatch):
    group_calls = []
    c2c_calls = []
    group_reply = gateway._attach_event_ref(
        {"content": "可用命令", "group_openid": "group-1"},
        {"id": "event-group"},
    )
    c2c_reply = gateway._attach_event_ref(
        {"content": "可用命令", "user_openid": "user-1"},
        {"id": "event-c2c"},
    )
    assert group_reply["msg_id"] == "event-group" and group_reply["msg_seq"] == 1
    assert c2c_reply["msg_id"] == "event-c2c" and c2c_reply["msg_seq"] == 1

    def fake_group(group_openid, content, **kwargs):
        group_calls.append((group_openid, content, kwargs))
        return {"message_id": "m1"}

    def fake_c2c(user_openid, content, **kwargs):
        c2c_calls.append((user_openid, content, kwargs))
        return {"message_id": "m2"}

    monkeypatch.setattr(qq_client, "send_group_message", fake_group)
    monkeypatch.setattr(qq_client, "send_c2c_message", fake_c2c)
    asyncio.run(
        gateway._send_reply(
            {
                "content": "可用命令",
                "group_openid": "group-1",
                "msg_id": "event-group",
                "msg_seq": 1,
            }
        )
    )
    asyncio.run(
        gateway._send_reply(
            {
                "content": "可用命令",
                "user_openid": "user-1",
                "msg_id": "event-c2c",
                "msg_seq": 1,
            }
        )
    )
    assert group_calls[0][2] == {
        "msg_id": "event-group",
        "msg_seq": 1,
        "mention_openids": [],
    }
    assert c2c_calls[0][2] == {"msg_id": "event-c2c", "msg_seq": 1}


def test_teacher_group_binding_and_teacher_commands(client, teacher_token, klass, student):
    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={
            "app_id": "102000001",
            "enabled": True,
            "mention_missing": True,
            "allow_query_assignments": True,
        },
    )
    assert config.status_code == 200
    code = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/group-code",
        headers=auth(teacher_token),
    ).json()["data"]["code"]
    event = {
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {
            "content": f"绑定群 {code}",
            "group_openid": "group-m35",
            "author": {"member_openid": "teacher-m35"},
        },
    }
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(db, event)
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        assert cfg.teacher_openid == "teacher-m35"
        assert cfg.teacher_bound_at is not None
    assert reply and "教师身份已绑定" in reply["content"]

    ids = _import(client, teacher_token, klass["id"], _questions())
    # 前端默认组卷用途是 practice；教师命令也必须能识别
    paper = _paper(client, teacher_token, klass["id"], ids, kind="practice")
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": "作业",
                    "group_openid": "group-m35",
                    "author": {"member_openid": "teacher-m35"},
                },
            },
        )
    assert reply and paper["title"] in reply["content"]
    assert "已交：" in reply["content"]
    assert "绑定" not in reply["content"]

    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": "作业通知",
                    "group_openid": "group-m35",
                    "author": {"member_openid": "teacher-m35"},
                },
            },
        )
    assert reply and reply["content"].startswith("【新作业】")
    assert paper["title"] in reply["content"]

    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": "解绑教师",
                    "group_openid": "group-m35",
                    "author": {"member_openid": "teacher-m35"},
                },
            },
        )
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        assert cfg.teacher_openid is None
        assert cfg.group_openid == "group-m35"
    assert reply and "群绑定保留" in reply["content"]


def test_teacher_remind_returns_mentions_and_gateway_fallback(client, teacher_token, klass, student, monkeypatch):
    from app.utils.time import now_naive

    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={"app_id": "102000001", "enabled": True, "mention_missing": True},
    )
    assert config.status_code == 200
    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.group_openid = "group-m35"
        cfg.teacher_openid = "teacher-m35"
        cfg.notify_assignment = 1
        cfg.bot_chat_enabled = 0
        db.add(
            QqBinding(
                class_id=klass["id"],
                student_id=student["user"]["id"],
                qq_openid="student-openid-m35",
                status=1,
                bound_at=now_naive(),
            )
        )
        db.commit()
    ids = _import(client, teacher_token, klass["id"], _questions())
    _paper(client, teacher_token, klass["id"], ids)
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": "催交",
                    "group_openid": "group-m35",
                    "author": {"member_openid": "teacher-m35"},
                },
            },
        )
    assert reply is not None
    assert reply["mention_openids"] == ["student-openid-m35"]
    assert "未交" in reply["content"]

    calls = []

    def fake_send(group, content, **kwargs):
        calls.append((content, kwargs))
        if len(calls) == 1:
            raise qq_client.QQBotError("QQ 错误码 40034105: 主动消息失败")
        return {"message_id": "fallback-1"}

    monkeypatch.setattr(qq_client, "send_group_message", fake_send)
    asyncio.run(gateway._send_reply(dict(reply, msg_id="e1", msg_seq=1)))
    assert len(calls) == 2
    assert calls[0][1]["mention_openids"] == ["student-openid-m35"]
    assert calls[1][1]["mention_openids"] == []
    assert "（@ 失败，已发名单）" in calls[1][0]


class _FakeChatRouter:
    def __init__(self):
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return type("Result", (), {"content": "AI 回答：TCP 属于传输层，重点看协议栈。"})()


def test_ai_chat_config_unknown_commands_and_rate_limit(client, teacher_token, klass, monkeypatch):

    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={
            "app_id": "102000001",
            "enabled": True,
            "bot_chat_mode": "balanced",
            "bot_chat_enabled": True,
            "bot_chat_max_chars": 200,
        },
    )
    assert config.status_code == 200, config.text
    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.group_openid = "group-ai"
        cfg.teacher_openid = "teacher-ai"
        db.commit()
    assert config.json()["data"]["bot_chat_mode"] == "balanced"
    assert config.json()["data"]["bot_chat_max_chars"] == 200

    router = _FakeChatRouter()
    monkeypatch.setattr(bot_chat_service, "build_router", lambda settings: router)
    monkeypatch.setattr(bot_chat_service, "retrieve_chunks", lambda *args, **kwargs: [])
    event = {
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {
            "content": "TCP 属于哪一层？",
            "group_openid": "group-ai",
            "author": {"member_openid": "teacher-ai"},
        },
    }
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(db, event)
    assert reply and "AI 回答" in reply["content"]
    assert router.calls

    with client.testing_session() as db:  # type: ignore[attr-defined]
        greeting = handler.handle_event(
            db,
            {
                "t": "GROUP_AT_MESSAGE_CREATE",
                "d": {
                    "content": "泥嚎呀",
                    "group_openid": "group-ai",
                    "author": {"member_openid": "teacher-ai"},
                },
            },
        )
    assert greeting and "小芽" in greeting["content"]
    assert len(router.calls) == 1

    with client.testing_session() as db:  # type: ignore[attr-defined]
        limited = handler.handle_event(db, event)
    assert limited and "10 秒" in limited["content"]
    assert len(router.calls) == 1

    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.bot_chat_mode = "strict"
        db.commit()
    with client.testing_session() as db:  # type: ignore[attr-defined]
        strict = handler.handle_event(db, event)
    assert strict and "未识别命令" in strict["content"]


def test_ai_chat_disabled_and_knowledge_context(monkeypatch, client, teacher_token, klass):
    from types import SimpleNamespace

    config = client.put(
        f"/api/v1/classes/{klass['id']}/bot-config",
        headers=auth(teacher_token),
        json={
            "app_id": "102000001",
            "enabled": True,
            "bot_chat_mode": "balanced",
            "bot_chat_enabled": False,
        },
    )
    assert config.status_code == 200
    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.group_openid = "group-ai-2"
        cfg.teacher_openid = "teacher-ai-2"
        db.commit()
    event = {
        "t": "GROUP_AT_MESSAGE_CREATE",
        "d": {
            "content": "学校考试规则是什么？",
            "group_openid": "group-ai-2",
            "author": {"member_openid": "teacher-ai-2"},
        },
    }
    with client.testing_session() as db:  # type: ignore[attr-defined]
        disabled = handler.handle_event(db, event)
    assert disabled and "未识别命令" in disabled["content"]

    with client.testing_session() as db:  # type: ignore[attr-defined]
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        cfg.bot_chat_enabled = 1
        db.commit()
    router = _FakeChatRouter()
    monkeypatch.setattr(
        bot_chat_service,
        "build_router",
        lambda settings: router,
    )
    monkeypatch.setattr(
        bot_chat_service,
        "retrieve_chunks",
        lambda *args, **kwargs: [
            SimpleNamespace(doc_name="课程讲义.pdf", content="TCP 位于传输层。")
        ],
    )
    with client.testing_session() as db:  # type: ignore[attr-defined]
        reply = handler.handle_event(db, event)
    assert reply and "AI 回答" in reply["content"]
    user_message = router.calls[0][0][1]["content"]
    assert "课程讲义.pdf" in user_message
    assert "TCP 位于传输层。" in user_message


def test_qq_answer_formats_markdown_and_splits_messages():
    raw = "# 同余定理\n**核心**：`a ≡ b`\n```python\nprint(1)\n```\n\\(a\\) \\pmod{m}"
    clean = bot_chat_service.format_for_qq(raw)
    assert "**" not in clean
    assert "```" not in clean
    assert "\\(" not in clean
    assert "同余定理" in clean
    assert "代码：" in clean

    long_text = "\n".join(["第一段。" * 300, "第二段。" * 300, "第三段。" * 300])
    chunks = bot_chat_service.split_for_qq(long_text)
    assert len(chunks) >= 2
    assert all(len(chunk) <= bot_chat_service._QQ_CHUNK_CHARS for chunk in chunks)
    assert chunks[0].startswith("第一段")
