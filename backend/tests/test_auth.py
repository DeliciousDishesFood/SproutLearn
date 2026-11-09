"""鉴权冒烟测试：AC-02 / 会话机制 / 登出幂等。"""

from __future__ import annotations

from tests.conftest import PASSWORD, auth, register_teacher


def test_teacher_register_login(client):
    registered = register_teacher(client)
    assert registered["token"]
    assert registered["user"]["role"] == "teacher"

    duplicate = client.post(
        "/api/v1/auth/teacher/register",
        json={
            "account": registered["user"]["account"],
            "name": "另一老师",
            "password": PASSWORD,
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40904
    assert set(duplicate.json()) == {"code", "message", "data", "request_id", "timestamp"}

    wrong = client.post(
        "/api/v1/auth/login",
        json={"role": "teacher", "account": registered["user"]["account"], "password": "Wrong123"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == 40103

    login = client.post(
        "/api/v1/auth/login",
        json={"role": "teacher", "account": registered["user"]["account"], "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["token"]

    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200
    body = me.json()["data"]
    assert body["role"] == "teacher"
    assert body["account"] == registered["user"]["account"]
    assert body["name"] == "张老师"

    logout = client.post("/api/v1/auth/logout", headers=auth(token))
    assert logout.status_code == 200
    assert logout.json()["data"] is None

    # 重复登出不报错（幂等）
    logout_again = client.post("/api/v1/auth/logout", headers=auth(token))
    assert logout_again.status_code == 200
    assert logout_again.json()["code"] == 0

    expired = client.get("/api/v1/auth/me", headers=auth(token))
    assert expired.status_code == 401
    assert expired.json()["code"] == 40102


def test_session_missing_returns_40102(client):
    teacher = register_teacher(client)
    client.fake_redis.flushall()  # type: ignore[attr-defined]
    response = client.get("/api/v1/auth/me", headers=auth(teacher["token"]))
    assert response.status_code == 401
    assert response.json()["code"] == 40102
