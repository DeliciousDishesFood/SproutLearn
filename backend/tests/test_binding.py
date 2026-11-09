"""QQ 绑定冒烟测试：AC-16/17/18，一次性码、错 secret、冲突、解绑、改绑。"""

from __future__ import annotations

import re

from app.config import get_settings
from tests.conftest import auth, join_student
from app.utils import cache_keys

CODE_RE = re.compile(r"^[1-9]\d{7}$")


def _generate(client, token: str):
    response = client.post("/api/v1/binding/qq-code", headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _bind(client, code: str, openid: str, secret: str | None = None):
    headers = {"X-Bot-Secret": secret or get_settings().bot_shared_secret}
    return client.post(
        "/api/v1/binding/qq",
        headers=headers,
        json={"code": code, "qq_openid": openid},
    )


def test_qq_bind_code_one_time(client, klass, student):
    settings = get_settings()
    token = student["token"]
    other = join_student(client, klass["invite_code"], student_no="20260102", name="王同学")

    first = _generate(client, token)
    assert CODE_RE.match(first["code"])
    assert first["expires_in"] == settings.bind_code_ttl_seconds
    ttl = client.fake_redis.ttl(cache_keys.qq_bind_code_key(first["code"]))  # type: ignore[attr-defined]
    assert 0 < ttl <= settings.bind_code_ttl_seconds

    second = _generate(client, token)
    assert second["code"] != first["code"]
    stale = _bind(client, first["code"], "OPENID-A")
    assert stale.status_code == 409
    assert stale.json()["code"] == 40905

    bad_secret = _bind(client, second["code"], "OPENID-A", secret="wrong-secret")
    assert bad_secret.status_code == 401
    assert bad_secret.json()["code"] == 40101

    bound = _bind(client, second["code"], "OPENID-A")
    assert bound.status_code == 200, bound.text
    assert bound.json()["data"]["student_id"] == student["user"]["id"]
    assert bound.json()["data"]["class_id"] == klass["id"]

    replay = _bind(client, second["code"], "OPENID-A")
    assert replay.status_code == 409
    assert replay.json()["code"] == 40905

    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.json()["data"]["qq_bound"] is True

    third = _generate(client, other["token"])
    conflict = _bind(client, third["code"], "OPENID-A")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == 40903

    unbind = client.delete("/api/v1/binding/qq", headers=auth(token))
    assert unbind.status_code == 200
    me_after = client.get("/api/v1/auth/me", headers=auth(token))
    assert me_after.json()["data"]["qq_bound"] is False

    # 解绑后该 QQ 可被他人绑定
    fourth = _generate(client, other["token"])
    rebound = _bind(client, fourth["code"], "OPENID-A")
    assert rebound.status_code == 200, rebound.text
    assert rebound.json()["data"]["student_id"] == other["user"]["id"]

    # 同一学生改绑到新 QQ：旧有效行置 0 后插入新行
    fifth = _generate(client, token)
    changed = _bind(client, fifth["code"], "OPENID-B")
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["student_id"] == student["user"]["id"]
