"""M3.3 机器人配置与文档中心。"""

from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.models.class_bot_config import ClassBotConfig
from app.services import bot_service
from tests.conftest import auth, create_class, register_teacher

SECRET = "qq-secret-keep-private-1234"


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _put(client, token, class_id, **overrides):
    body = {
        "app_id": "102000001",
        "app_secret": SECRET,
        "callback_url": "https://bot.example.com/callback",
        "enabled": True,
    }
    body.update(overrides)
    return client.put(
        f"/api/v1/classes/{class_id}/bot-config",
        headers=auth(token),
        json=body,
    )


def test_bot_config_secret_never_echoed_and_cipher_persisted(client, teacher_token, klass):
    empty = client.get(
        f"/api/v1/classes/{klass['id']}/bot-config", headers=auth(teacher_token)
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["has_secret"] is False
    assert empty.json()["data"]["last_check_status"] == "never"

    saved = _put(client, teacher_token, klass["id"])
    assert saved.status_code == 200, saved.text
    data = saved.json()["data"]
    assert data["app_id"] == "102000001"
    assert data["has_secret"] is True
    assert data["secret_tail"] == SECRET[-4:]
    assert "app_secret" not in data and "app_secret_cipher" not in data
    assert SECRET not in saved.text

    fetched = client.get(
        f"/api/v1/classes/{klass['id']}/bot-config", headers=auth(teacher_token)
    )
    assert fetched.status_code == 200
    assert SECRET not in fetched.text
    assert fetched.json()["data"]["secret_tail"] == SECRET[-4:]

    with client.testing_session() as db:  # type: ignore[attr-defined]
        row = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        assert bytes(row.app_secret_cipher) != SECRET.encode()
        assert SECRET.encode() not in bytes(row.app_secret_cipher)

    # Secret 留空表示不修改
    updated = _put(
        client,
        teacher_token,
        klass["id"],
        app_id="102000002",
        app_secret="",
        callback_url=None,
        enabled=False,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["app_id"] == "102000002"
    assert updated.json()["data"]["secret_tail"] == SECRET[-4:]
    assert updated.json()["data"]["callback_url"] is None


def test_bot_config_first_save_requires_secret_and_missing_key(client, teacher_token, klass):
    missing = _put(client, teacher_token, klass["id"], app_secret="")
    assert missing.status_code == 422
    assert missing.json()["code"] == 40001

    import app.utils.bot_crypto as crypto

    original = crypto.get_settings
    crypto.get_settings = lambda: SimpleNamespace(bot_secret_key="")
    try:
        failed = _put(client, teacher_token, klass["id"])
    finally:
        crypto.get_settings = original
    assert failed.status_code == 500
    assert failed.json()["code"] == 50001
    assert "BOT_SECRET_KEY" in failed.json()["message"]


def test_bot_test_ok_and_failure_codes(client, teacher_token, klass, monkeypatch):
    assert _put(client, teacher_token, klass["id"]).status_code == 200

    calls = []

    def fake_ok(url, **kwargs):
        calls.append((url, kwargs))
        return _Resp(200, {"access_token": "token-not-returned", "expires_in": 7200})

    monkeypatch.setattr(bot_service.httpx, "post", fake_ok)
    ok = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["ok"] is True
    assert ok.json()["data"]["expires_in"] == 7200
    assert ok.json()["data"]["last_check_status"] == "ok"
    assert calls and calls[0][1]["timeout"] == 8.0
    assert "access_token" not in ok.text
    assert SECRET not in ok.text

    def fake_fail(url, **kwargs):
        return _Resp(200, {"code": 100016, "message": "invalid appid"})

    monkeypatch.setattr(bot_service.httpx, "post", fake_fail)
    failed = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert failed.status_code == 200
    assert failed.json()["data"]["ok"] is False
    assert "100016" in failed.json()["data"]["message"]
    assert failed.json()["data"]["last_check_status"] == "failed"
    assert SECRET not in failed.text


def test_bot_test_timeout_and_no_config(client, teacher_token, klass, monkeypatch):
    no_config = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert no_config.status_code == 422
    assert no_config.json()["code"] == 40001

    assert _put(client, teacher_token, klass["id"]).status_code == 200

    def fake_timeout(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(bot_service.httpx, "post", fake_timeout)
    result = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert result.status_code == 200
    assert result.json()["data"]["ok"] is False
    assert "8s" in result.json()["data"]["message"]
    assert result.json()["data"]["last_check_status"] == "failed"


def test_bot_permissions(client, teacher_token, klass, student):
    student_get = client.get(
        f"/api/v1/classes/{klass['id']}/bot-config", headers=auth(student["token"])
    )
    assert student_get.status_code == 403
    assert student_get.json()["code"] == 40301

    teacher_b = register_teacher(client, "m33-b@school.edu.cn")
    create_class(client, teacher_b["token"], "M3.3 B 班")
    cross = client.get(
        f"/api/v1/classes/{klass['id']}/bot-config", headers=auth(teacher_b["token"])
    )
    assert cross.status_code == 403
    assert cross.json()["code"] == 40302


def test_docs_list_detail_and_404(client, student):
    listed = client.get("/api/v1/docs", headers=auth(student["token"]))
    assert listed.status_code == 200, listed.text
    docs = listed.json()["data"]
    assert len(docs) >= 3
    assert {item["slug"] for item in docs} >= {"qq-bot-setup", "question-import", "grading-review"}
    assert all("title" in item and "summary" in item and "updated_at" in item for item in docs)

    detail = client.get("/api/v1/docs/qq-bot-setup", headers=auth(student["token"]))
    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert data["title"] == "QQ 机器人配置"
    assert "QQ 开放平台" in data["content"]
    assert "<script" not in data["content"].lower()

    missing = client.get("/api/v1/docs/no-such-doc", headers=auth(student["token"]))
    assert missing.status_code == 404
    assert missing.json()["code"] == 40401

    traversal = client.get("/api/v1/docs/../manifest", headers=auth(student["token"]))
    assert traversal.status_code == 404
    assert traversal.json()["code"] == 40401
