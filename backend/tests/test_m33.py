"""M3.4 机器人配置（Secret 由环境变量托管）与文档中心。"""

from __future__ import annotations

import httpx

from app.models.class_bot_config import ClassBotConfig
from app.services import bot_service
from app.services.qq_bot import client as qq_client
from tests.conftest import auth, create_class, register_teacher


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _put(client, token, class_id, **overrides):
    body = {
        "app_id": "102000001",
        "callback_url": "https://bot.example.com/callback",
        "enabled": True,
        "binding_enabled": True,
        "notify_assignment": True,
        "notify_due_soon": True,
        "mention_missing": False,
        "allow_query_assignments": True,
        "allow_query_scores": False,
    }
    body.update(overrides)
    return client.put(
        f"/api/v1/classes/{class_id}/bot-config",
        headers=auth(token),
        json=body,
    )


def test_bot_config_env_managed_and_permissions(client, teacher_token, klass):
    empty = client.get(
        f"/api/v1/classes/{klass['id']}/bot-config", headers=auth(teacher_token)
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["secret_managed_by_env"] is True
    assert "has_secret" not in empty.json()["data"]

    saved = _put(client, teacher_token, klass["id"], allow_query_scores=True)
    assert saved.status_code == 200, saved.text
    data = saved.json()["data"]
    assert data["app_id"] == "102000001"
    assert data["allow_query_scores"] is True
    assert "app_secret" not in data and "secret_tail" not in data
    assert "app_secret" not in saved.text

    with client.testing_session() as db:  # type: ignore[attr-defined]
        row = db.query(ClassBotConfig).filter(ClassBotConfig.class_id == klass["id"]).one()
        assert not hasattr(row, "app_secret_cipher")
        assert row.group_openid is None


def test_bot_test_success_failure_timeout_and_missing_env(client, teacher_token, klass, monkeypatch):
    assert _put(client, teacher_token, klass["id"]).status_code == 200
    qq_client._token = None
    calls = []

    def fake_ok(url, **kwargs):
        calls.append((url, kwargs))
        return _Resp(200, {"access_token": "token-not-returned", "expires_in": 7200})

    monkeypatch.setattr(qq_client.httpx, "post", fake_ok)
    ok = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["ok"] is True
    assert ok.json()["data"]["expires_in"] == 7200
    assert calls and calls[0][1]["timeout"] == 8.0
    assert "access_token" not in ok.text

    qq_client._token = None

    def fake_fail(url, **kwargs):
        return _Resp(200, {"code": 100016, "message": "invalid appid"})

    monkeypatch.setattr(qq_client.httpx, "post", fake_fail)
    failed = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert failed.json()["data"]["ok"] is False
    assert "100016" in failed.json()["data"]["message"]

    qq_client._token = None

    def fake_timeout(url, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(qq_client.httpx, "post", fake_timeout)
    timeout = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert timeout.json()["data"]["ok"] is False
    assert "超时" in timeout.json()["data"]["message"]

    monkeypatch.setattr(bot_service._settings, "qq_bot_app_id", "")
    missing = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert missing.status_code == 500
    assert missing.json()["code"] == 50001


def test_bot_group_code_and_no_config_test(client, teacher_token, klass):
    no_config = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/test",
        headers=auth(teacher_token),
    )
    assert no_config.status_code == 422
    assert no_config.json()["code"] == 40001

    code = client.post(
        f"/api/v1/classes/{klass['id']}/bot-config/group-code",
        headers=auth(teacher_token),
    )
    assert code.status_code == 200, code.text
    assert len(code.json()["data"]["code"]) == 8
    assert code.json()["data"]["expires_in"] == 600


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


def test_docs_list_detail_and_404(client, teacher_token):
    listed = client.get("/api/v1/docs", headers=auth(teacher_token))
    assert listed.status_code == 200
    docs = listed.json()["data"]
    assert len(docs) >= 3
    assert {item["slug"] for item in docs} >= {"qq-bot-setup", "question-import", "grading-review"}

    detail = client.get("/api/v1/docs/qq-bot-setup", headers=auth(teacher_token))
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["title"] == "QQ 机器人配置"
    assert "QQ 开放平台" in data["content"]
    assert "<script" not in data["content"].lower()

    missing = client.get("/api/v1/docs/no-such-doc", headers=auth(teacher_token))
    assert missing.status_code == 404
    assert missing.json()["code"] == 40401
