"""班级冒烟测试：AC-03/04/05/06/07/09，越权 40302，角色 40301。"""

from __future__ import annotations

import jwt

from app.config import get_settings
from tests.conftest import (
    PASSWORD,
    auth,
    create_class,
    join_student,
    register_teacher,
)


def test_create_class_and_code(client, teacher_token):
    first = create_class(client, teacher_token, "2026级计算机1班")
    second = create_class(client, teacher_token, "2026级计算机2班")

    assert len(first["class_code"]) == 6
    assert len(first["invite_code"]) == 6
    assert first["class_code"] != second["class_code"]
    assert first["invite_code"] != second["invite_code"]

    detail = client.get(f"/api/v1/classes/{first['id']}", headers=auth(teacher_token))
    assert detail.status_code == 200
    assert detail.json()["data"]["class_code"] == first["class_code"]

    listing = client.get("/api/v1/classes?page=1&page_size=10", headers=auth(teacher_token))
    assert listing.status_code == 200
    body = listing.json()["data"]
    assert body["total"] == 2
    assert {item["class_code"] for item in body["list"]} == {
        first["class_code"],
        second["class_code"],
    }


def test_join_class_and_dup_student_no(client, klass):
    joined = join_student(client, klass["invite_code"])
    assert joined["user"]["class_id"] == klass["id"]
    assert joined["user"]["class_code"] == klass["class_code"]

    duplicate = client.post(
        "/api/v1/classes/join",
        json={
            "invite_code": klass["invite_code"],
            "student_no": "20260101",
            "name": "重复同学",
            "password": PASSWORD,
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40901

    login = client.post(
        "/api/v1/auth/login",
        json={
            "role": "student",
            "class_code": klass["class_code"],
            "student_no": "20260101",
            "password": PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["token"]
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    assert payload["role"] == "student"
    assert payload["class_id"] == klass["id"]

    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["data"]["class_code"] == klass["class_code"]

    forbidden = client.get("/api/v1/classes", headers=auth(token))
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40301


def test_invite_reset_invalidates_old(client, klass, teacher_token):
    old_code = klass["invite_code"]
    reset = client.post(
        f"/api/v1/classes/{klass['id']}/invite-code/reset", headers=auth(teacher_token)
    )
    assert reset.status_code == 200, reset.text
    new_code = reset.json()["data"]["invite_code"]
    assert new_code != old_code

    stale = client.post(
        "/api/v1/classes/join",
        json={
            "invite_code": old_code,
            "student_no": "20260102",
            "name": "旧码同学",
            "password": PASSWORD,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == 40902

    fresh = join_student(client, new_code, student_no="20260103", name="新码同学")
    assert fresh["user"]["class_id"] == klass["id"]

    current = client.get(
        f"/api/v1/classes/{klass['id']}/invite-code", headers=auth(teacher_token)
    )
    assert current.status_code == 200
    assert current.json()["data"]["invite_code"] == new_code


def test_cross_class_forbidden(client, klass, teacher_token, student):
    other = register_teacher(client, account="teacher02@school.edu.cn")
    other_token = other["token"]

    for path in (
        f"/api/v1/classes/{klass['id']}",
        f"/api/v1/classes/{klass['id']}/students",
        f"/api/v1/classes/{klass['id']}/invite-code",
        f"/api/v1/knowledge/documents?class_id={klass['id']}",
    ):
        response = client.get(path, headers=auth(other_token))
        assert response.status_code == 403, (path, response.text)
        assert response.json()["code"] == 40302

    upload = client.post(
        "/api/v1/knowledge/documents",
        headers=auth(other_token),
        data={"class_id": str(klass["id"])},
        files=[("files", ("a.txt", b"hello", "text/plain"))],
    )
    assert upload.status_code == 403
    assert upload.json()["code"] == 40302

    student_token = student["token"]
    student_forbidden = client.get(
        f"/api/v1/classes/{klass['id']}/students", headers=auth(student_token)
    )
    assert student_forbidden.status_code == 403
    assert student_forbidden.json()["code"] == 40301
