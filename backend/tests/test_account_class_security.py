"""v1.4 账号与班级基础管理验收。"""

from __future__ import annotations

from app.models.account_audit_log import AccountAuditLog
from app.models.class_ import Class
from app.models.class_bot_config import ClassBotConfig
from app.models.qq_binding import QqBinding
from app.models.student import Student
from app.services import notification_service
from app.services.qq_bot import handler
from tests.conftest import PASSWORD, auth, create_class, register_teacher

NEW_PASSWORD = "Newpass123"


def _change(client, token, current, new):
    return client.post(
        "/api/v1/auth/password/change",
        headers=auth(token),
        json={"current_password": current, "new_password": new},
    )


def _login_student(client, klass, student_no, password):
    return client.post(
        "/api/v1/auth/login",
        json={
            "role": "student",
            "class_code": klass["class_code"],
            "student_no": student_no,
            "password": password,
        },
    )


def test_password_change_rules_and_old_token_invalid(client, teacher_token, student, klass):
    token = student["token"]
    wrong = _change(client, token, "Wrong1234", NEW_PASSWORD)
    assert wrong.status_code == 400 and wrong.json()["code"] == 40001
    same = _change(client, token, PASSWORD, PASSWORD)
    assert same.status_code == 400 and same.json()["code"] == 40001
    weak = _change(client, token, PASSWORD, "short")
    assert weak.status_code in (400, 422) and weak.json()["code"] == 40001

    ok = _change(client, token, PASSWORD, NEW_PASSWORD)
    assert ok.status_code == 200, ok.text
    old = client.get("/api/v1/auth/me", headers=auth(token))
    assert old.status_code == 401
    old_login = _login_student(client, klass, "20260101", PASSWORD)
    assert old_login.status_code == 401 and old_login.json()["code"] == 40103
    new_login = _login_student(client, klass, "20260101", NEW_PASSWORD)
    assert new_login.status_code == 200
    assert new_login.json()["data"]["must_change_password"] is False
    new_token = new_login.json()["data"]["token"]
    assert client.get("/api/v1/auth/me", headers=auth(new_token)).status_code == 200

    # 教师改密同样递增版本
    teacher_new = _change(client, teacher_token, PASSWORD, "Teacher123")
    assert teacher_new.status_code == 200, teacher_new.text
    assert client.get("/api/v1/auth/me", headers=auth(teacher_token)).status_code == 401


def test_password_change_failure_limit(client, student):
    token = student["token"]
    for _ in range(5):
        response = _change(client, token, "Wrong1234", NEW_PASSWORD)
        assert response.status_code == 400
    limited = _change(client, token, "Wrong1234", NEW_PASSWORD)
    assert limited.status_code == 429
    assert limited.json()["code"] == 42901


def test_teacher_reset_temp_password_and_cross_class(client, teacher_token, klass, student):
    sid = student["user"]["id"]
    reset = client.post(
        f"/api/v1/classes/{klass['id']}/students/{sid}/password-reset",
        headers=auth(teacher_token),
    )
    assert reset.status_code == 200, reset.text
    temp = reset.json()["data"]["temporary_password"]
    assert len(temp) >= 8 and any(c.isalpha() for c in temp) and any(c.isdigit() for c in temp)

    # 临时密码只存 hash；audit 不含密码
    with client.testing_session() as db:
        assert db.query(Student).filter(Student.id == sid).one().must_change_password == 1
        audits = db.query(AccountAuditLog).filter(AccountAuditLog.target_id == sid).all()
        assert audits and all(temp not in str(row.__dict__) for row in audits)

    login = _login_student(client, klass, "20260101", temp)
    assert login.status_code == 200
    assert login.json()["data"]["must_change_password"] is True
    temp_token = login.json()["data"]["token"]
    me = client.get("/api/v1/auth/me", headers=auth(temp_token))
    assert me.status_code == 200
    assert me.json()["data"]["must_change_password"] is True
    blocked = client.get("/api/v1/me/workbench", headers=auth(temp_token))
    assert blocked.status_code == 403 and blocked.json()["code"] == 40303

    # 临时密码改密后恢复
    changed = _change(client, temp_token, temp, NEW_PASSWORD)
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/auth/me", headers=auth(temp_token)).status_code == 401
    assert _login_student(client, klass, "20260101", NEW_PASSWORD).status_code == 200

    # 跨班重置不能泄露学生存在性
    other_teacher = register_teacher(client, "v14-other@school.edu.cn")
    other_class = create_class(client, other_teacher["token"], "另一个班")
    cross = client.post(
        f"/api/v1/classes/{other_class['id']}/students/{sid}/password-reset",
        headers=auth(other_teacher["token"]),
    )
    assert cross.status_code == 403 and cross.json()["code"] == 40302


def test_reset_rate_limit_and_no_password_in_response_logs(client, teacher_token, klass, student):
    sid = student["user"]["id"]
    for _ in range(5):
        response = client.post(
            f"/api/v1/classes/{klass['id']}/students/{sid}/password-reset",
            headers=auth(teacher_token),
        )
        assert response.status_code == 200
        assert "password_hash" not in response.text
    limited = client.post(
        f"/api/v1/classes/{klass['id']}/students/{sid}/password-reset",
        headers=auth(teacher_token),
    )
    assert limited.status_code == 429 and limited.json()["code"] == 42901


def test_student_disable_restore_and_qq_notification(client, teacher, teacher_token, klass, student):
    sid = student["user"]["id"]
    token = student["token"]
    disabled = client.put(
        f"/api/v1/classes/{klass['id']}/students/{sid}/status",
        headers=auth(teacher_token),
        json={"status": 0},
    )
    assert disabled.status_code == 200 and disabled.json()["data"]["status"] == 0
    assert client.get("/api/v1/auth/me", headers=auth(token)).json()["code"] == 40304
    assert _login_student(client, klass, "20260101", PASSWORD).json()["code"] == 40304
    with client.testing_session() as db:
        assert notification_service.add_for_class(
            db, class_id=klass["id"], type="test", title="停用", body="不应发给停用学生"
        ) == 0

    # 同一状态幂等，不再递增版本
    with client.testing_session() as db:
        row = db.get(Student, sid)
        version = row.auth_version
        assert row.xp_total == student["user"].get("xp_total", row.xp_total)
        cfg = ClassBotConfig(class_id=klass["id"], app_id="env", enabled=1, binding_enabled=1, created_by=teacher["user"]["id"])
        db.add(cfg)
        db.add(QqBinding(class_id=klass["id"], student_id=sid, qq_openid="v14-student", status=1))
        db.commit()
    again = client.put(
        f"/api/v1/classes/{klass['id']}/students/{sid}/status",
        headers=auth(teacher_token),
        json={"status": 0},
    )
    assert again.status_code == 200 and again.json()["data"]["changed"] is False
    with client.testing_session() as db:
        assert db.get(Student, sid).auth_version == version
        reply = handler.handle_event(
            db,
            {
                "t": "C2C_MESSAGE_CREATE",
                "d": {"content": "作业", "author": {"user_openid": "v14-student"}},
            },
        )
    assert reply and "停用" in reply["content"]

    restored = client.put(
        f"/api/v1/classes/{klass['id']}/students/{sid}/status",
        headers=auth(teacher_token),
        json={"status": 1},
    )
    assert restored.status_code == 200
    assert _login_student(client, klass, "20260101", PASSWORD).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_class_archive_restore_and_active_limit(client, teacher_token, klass, student):
    other_teacher = register_teacher(client, "v14-archive-other@school.edu.cn")
    with client.testing_session() as db:
        db.add(ClassBotConfig(class_id=klass["id"], app_id="env", enabled=1, binding_enabled=1, group_openid="v14-group", teacher_openid="v14-teacher", created_by=teacher_token and db.query(Class).filter(Class.id == klass["id"]).one().teacher_id))
        db.commit()
    cross = client.post(f"/api/v1/classes/{klass['id']}/archive", headers=auth(other_teacher["token"]))
    assert cross.status_code == 403 and cross.json()["code"] == 40302
    archived = client.post(f"/api/v1/classes/{klass['id']}/archive", headers=auth(teacher_token))
    assert archived.status_code == 200 and archived.json()["data"]["status"] == 0
    again = client.post(f"/api/v1/classes/{klass['id']}/archive", headers=auth(teacher_token))
    assert again.status_code == 200

    listing = client.get("/api/v1/classes", headers=auth(teacher_token))
    assert all(item["id"] != klass["id"] for item in listing.json()["data"]["list"])
    archived_list = client.get("/api/v1/classes?include_archived=true", headers=auth(teacher_token))
    assert any(item["id"] == klass["id"] for item in archived_list.json()["data"]["list"])

    assert _login_student(client, klass, "20260101", PASSWORD).json()["code"] == 40305
    assert client.get("/api/v1/auth/me", headers=auth(student["token"])).status_code == 401
    with client.testing_session() as db:
        qq_reply = handler.handle_event(
            db,
            {"t": "GROUP_AT_MESSAGE_CREATE", "d": {"content": "作业", "author": {"member_openid": "v14-teacher"}, "group_openid": "v14-group"}},
        )
    assert qq_reply and "归档" in qq_reply["content"]
    announcement = client.post(
        f"/api/v1/classes/{klass['id']}/announcements",
        headers=auth(teacher_token),
        json={"title": "归档测试", "body": "不应发送"},
    )
    assert announcement.status_code == 403 and announcement.json()["code"] == 40305
    paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "归档卷", "mode": "random", "count": 1},
    )
    assert paper.status_code == 403 and paper.json()["code"] == 40305

    restored = client.post(f"/api/v1/classes/{klass['id']}/restore", headers=auth(teacher_token))
    assert restored.status_code == 200 and restored.json()["data"]["status"] == 1
    assert _login_student(client, klass, "20260101", PASSWORD).status_code == 200

    # 活跃班上限不计归档：先建到 10 个，再归档一个后仍可新建
    for i in range(9):
        create_class(client, teacher_token, f"上限班{i}")
    at_limit = client.post(
        "/api/v1/classes",
        headers=auth(teacher_token),
        json={"class_name": "超限", "course_name": "网络"},
    )
    assert at_limit.status_code == 409 and at_limit.json()["code"] == 40907
    client.post(f"/api/v1/classes/{klass['id']}/archive", headers=auth(teacher_token))
    after_archive = client.post(
        "/api/v1/classes",
        headers=auth(teacher_token),
        json={"class_name": "归档后新班", "course_name": "网络"},
    )
    assert after_archive.status_code == 200, after_archive.text


def test_docs_role_filter(client, teacher_token, student):
    teacher_docs = client.get("/api/v1/docs", headers=auth(teacher_token))
    assert teacher_docs.status_code == 200
    assert any(item["slug"] == "qq-bot-setup" for item in teacher_docs.json()["data"])
    assert client.get("/api/v1/docs/qq-bot-setup", headers=auth(teacher_token)).status_code == 200

    student_docs = client.get("/api/v1/docs", headers=auth(student["token"]))
    assert student_docs.status_code == 200
    assert student_docs.json()["data"] == []
    forbidden = client.get("/api/v1/docs/qq-bot-setup", headers=auth(student["token"]))
    assert forbidden.status_code == 404 and forbidden.json()["code"] == 40401


def test_existing_rows_default_auth_fields(client, teacher, student):
    with client.testing_session() as db:
        row = db.get(Student, student["user"]["id"])
        assert row is not None
        assert row.auth_version == 1
        assert row.must_change_password == 0
        assert db.query(Class).first() is not None
