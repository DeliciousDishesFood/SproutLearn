"""QQ 主动通知细分状态、重试与 AI 输出预算。"""

from __future__ import annotations

from types import SimpleNamespace

from app.models.bot_notice import BotNotice
from app.models.class_bot_config import ClassBotConfig
from app.services import bot_chat_service, bot_service
from app.services.llm.base import AllProvidersFailed
from app.services.qq_bot import client as qq_client
from app.services.qq_bot import notifier
from tests.conftest import auth
from tests.test_m34 import _import, _paper, _questions


def _config(client, token, class_id, **overrides):
    payload = {
        "app_id": "102000001",
        "enabled": True,
        "notify_assignment": True,
        "bot_chat_mode": "balanced",
        "bot_chat_enabled": True,
        "bot_chat_max_chars": 200,
    }
    payload.update(overrides)
    response = client.put(
        f"/api/v1/classes/{class_id}/bot-config", headers=auth(token), json=payload
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _set_group(client, class_id, value="v15"):
    with client.testing_session() as db:
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one()
        cfg.group_openid = value
        db.commit()


def test_assignment_notice_detail_and_retry(client, teacher_token, klass, monkeypatch):
    _config(client, teacher_token, klass["id"])
    _set_group(client, klass["id"])
    monkeypatch.setattr(notifier, "get_settings", lambda: SimpleNamespace(qq_bot_enabled=True))
    calls = []

    def permission_denied(group, content, **kwargs):
        calls.append("failed")
        raise qq_client.QQBotError(
            "QQ 错误码 40034105: 主动消息失败, 无权限", code="40034105", status=403
        )

    monkeypatch.setattr(qq_client, "send_group_message", permission_denied)
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(client, teacher_token, klass["id"], ids)
    assert paper["group_notice"] == "failed"
    detail = paper["group_notice_detail"]
    assert detail["reason"] == "qq_permission_denied"
    assert detail["error_code"] == "40034105"
    assert "群主" in detail["message"]
    assert detail["attempt_count"] == 1
    assert detail["sent_at"] is None

    with client.testing_session() as db:
        notice = db.query(BotNotice).filter(BotNotice.paper_id == paper["id"]).one()
        assert notice.status == "failed"
        assert notice.reason == "qq_permission_denied"
        assert notice.error_code == "40034105"
        assert notice.attempt_count == 1
        assert notice.message_id is None

    def success(group, content, **kwargs):
        calls.append("sent")
        return {"message_id": "m-v15"}

    monkeypatch.setattr(qq_client, "send_group_message", success)
    retry = client.post(
        f"/api/v1/papers/{paper['id']}/group-notice/retry",
        headers=auth(teacher_token),
    )
    assert retry.status_code == 200, retry.text
    body = retry.json()["data"]
    assert body["group_notice"] == "sent"
    assert body["group_notice_detail"]["reason"] == "sent"
    assert body["group_notice_detail"]["attempt_count"] == 2
    assert body["group_notice_detail"]["sent_at"]
    with client.testing_session() as db:
        notice = db.query(BotNotice).filter(BotNotice.paper_id == paper["id"]).one()
        assert notice.status == "sent"
        assert notice.message_id == "m-v15"
        assert notice.attempt_count == 2
        assert db.query(BotNotice).count() == 1
    assert calls == ["failed", "sent"]


def test_notice_skip_reason_and_diagnostics(client, teacher_token, klass, monkeypatch):
    _config(client, teacher_token, klass["id"], notify_assignment=False)
    _set_group(client, klass["id"])
    monkeypatch.setattr(notifier, "get_settings", lambda: SimpleNamespace(qq_bot_enabled=True))
    ids = _import(client, teacher_token, klass["id"], _questions())
    paper = _paper(client, teacher_token, klass["id"], ids)
    assert paper["group_notice"] == "skipped"
    assert paper["group_notice_detail"]["reason"] == "notify_assignment_disabled"

    # 诊断接口只报告 token/gateway 与最近通知，不声称主动消息已授权
    _config(client, teacher_token, klass["id"], notify_assignment=True)
    monkeypatch.setattr(
        bot_service.qq_client,
        "get_app_access_token",
        lambda: {"access_token": "not-printed", "expires_in": 7200},
    )
    test = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert test.status_code == 200, test.text
    data = test.json()["data"]
    assert data["group_bound"] is True
    assert data["group_openid_tail"] == "v15"
    assert data["active_message_hint"]
    assert data["last_notice"] is None or "reason" in data["last_notice"]


def _chat_router(monkeypatch, content=None, raises=None):
    class Router:
        def __init__(self):
            self.providers = []

        def chat(self, messages, **kwargs):
            if raises is not None:
                raise raises
            Router.last = (messages, kwargs)
            return SimpleNamespace(content=content or "回答")

    router = Router()

    def factory(settings):
        router.settings = settings
        return router

    monkeypatch.setattr(bot_chat_service, "build_router", factory)
    monkeypatch.setattr(bot_chat_service, "retrieve_chunks", lambda *a, **k: [])
    return router


def test_ai_budget_is_clamped_to_300_and_free_mode(client, teacher_token, klass, monkeypatch):
    _config(
        client,
        teacher_token,
        klass["id"],
        bot_chat_mode="free",
        bot_chat_max_chars=600,
    )
    with client.testing_session() as db:
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        router = _chat_router(monkeypatch, content="长" * 1000)
        out = bot_chat_service.answer(
            db,
            config=cfg,
            class_id=klass["id"],
            openid="v15-ai",
            question="TCP 和 UDP 有什么区别？",
        )
        assert len(out) <= 300
        messages, kwargs = router.last
        assert "300 字" in messages[0]["content"]
        assert kwargs["max_tokens"] <= 700
        assert router.settings.llm_timeout_seconds == 6


def test_ai_timeout_message(client, teacher_token, klass, monkeypatch):
    _config(client, teacher_token, klass["id"], bot_chat_mode="balanced")
    with client.testing_session() as db:
        cfg = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        _chat_router(monkeypatch, raises=AllProvidersFailed([{"error": "race_timeout"}]))
        out = bot_chat_service.answer(
            db,
            config=cfg,
            class_id=klass["id"],
            openid="v15-timeout",
            question="什么是三次握手？",
        )
        assert "缩短" in out
