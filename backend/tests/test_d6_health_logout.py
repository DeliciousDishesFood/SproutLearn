"""D6 健康检查与幂等登出。"""

from __future__ import annotations

from tests.conftest import auth


def test_health_reports_backend_without_secret(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["db_backend"] in {"sqlite", "mysql"}
    assert data["db_name"]
    assert data["app_env"] == "test"
    assert data["jwt_secret_fingerprint"]
    assert "secret" not in data["jwt_secret_fingerprint"].lower()


def test_logout_without_bad_and_repeated_token_is_200(client, teacher_token):
    no_token = client.post("/api/v1/auth/logout")
    assert no_token.status_code == 200
    assert no_token.json()["code"] == 0
    assert no_token.json()["data"] is None

    bad = client.post(
        "/api/v1/auth/logout", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert bad.status_code == 200
    assert bad.json()["code"] == 0

    first = client.post("/api/v1/auth/logout", headers=auth(teacher_token))
    assert first.status_code == 200 and first.json()["code"] == 0
    again = client.post("/api/v1/auth/logout", headers=auth(teacher_token))
    assert again.status_code == 200 and again.json()["code"] == 0
    me = client.get("/api/v1/auth/me", headers=auth(teacher_token))
    assert me.status_code == 401
    assert me.json()["code"] == 40102
