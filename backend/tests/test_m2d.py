"""M2D 恢复接口：已答内容、服务端时钟、跨班、已提交。"""

from __future__ import annotations

from datetime import datetime

from tests.conftest import auth, create_class, join_student, register_teacher
from tests.test_m2b import _json_file


def _seed_attempt(client, teacher_token, class_id, student_token):
    preview = _json_file(
        client,
        teacher_token,
        class_id,
        [
            {
                "type": "single",
                "stem": "1+1 等于几？",
                "options": [{"key": "A", "text": "2"}, {"key": "B", "text": "3"}],
                "answer": "A",
                "knowledge_tag": "算术",
            }
        ],
    )
    commit = client.post(
        f"/api/v1/classes/{class_id}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": preview.json()["data"]["token"]},
    )
    question_id = commit.json()["data"]["question_ids"][0]
    paper = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(teacher_token),
        json={"title": "M2D 恢复卷", "mode": "fixed", "question_ids": [question_id], "duration_minutes": 30},
    )
    assert paper.status_code == 200, paper.text
    paper_id = paper.json()["data"]["id"]
    assert client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(teacher_token)).status_code == 200
    started = client.post(f"/api/v1/papers/{paper_id}/attempts", headers=auth(student_token))
    assert started.status_code == 200, started.text
    return question_id, paper_id, started.json()["data"]


def test_resume_returns_saved_answers_and_remaining(client, teacher_token, klass, student):
    question_id, _paper_id, attempt = _seed_attempt(client, teacher_token, klass["id"], student["token"])
    assert "server_now" in attempt
    assert isinstance(attempt["remaining_seconds"], int)
    assert 0 < attempt["remaining_seconds"] <= 1800

    saved = client.put(
        f"/api/v1/attempts/{attempt['id']}/answers/{question_id}",
        headers=auth(student["token"]),
        json={"answer": "A"},
    )
    assert saved.status_code == 200, saved.text

    resumed = client.get(f"/api/v1/attempts/{attempt['id']}", headers=auth(student["token"]))
    assert resumed.status_code == 200, resumed.text
    body = resumed.json()["data"]
    assert body["attempt"]["id"] == attempt["id"]
    assert body["attempt"]["status"] == "doing"
    assert body["answers"][str(question_id)] == "A"
    assert body["paper"]["blank_mode"] == "smart"
    assert body["questions"][0]["id"] == question_id
    assert "answer" not in body["questions"][0]
    assert "standard_answer" not in body["questions"][0]
    assert "analysis" not in body["questions"][0]
    assert 0 < body["remaining_seconds"] <= 1800
    datetime.fromisoformat(body["server_now"])

    teacher_view = client.get(f"/api/v1/attempts/{attempt['id']}", headers=auth(teacher_token))
    assert teacher_view.status_code == 200
    assert teacher_view.json()["data"]["answers"][str(question_id)] == "A"


def test_resume_cross_class_forbidden(client, teacher_token, klass, student):
    _question_id, _paper_id, attempt = _seed_attempt(client, teacher_token, klass["id"], student["token"])

    teacher_b = register_teacher(client, "m2d-b@school.edu.cn")
    class_b = create_class(client, teacher_b["token"], "M2D B 班")
    student_b = join_student(client, class_b["invite_code"], student_no="M2D2026")

    teacher_resp = client.get(f"/api/v1/attempts/{attempt['id']}", headers=auth(teacher_b["token"]))
    assert teacher_resp.status_code == 403
    assert teacher_resp.json()["code"] == 40302

    student_resp = client.get(f"/api/v1/attempts/{attempt['id']}", headers=auth(student_b["token"]))
    assert student_resp.status_code == 403
    assert student_resp.json()["code"] == 40302


def test_resume_submitted_remaining_zero_and_answers_readable(client, teacher_token, klass, student):
    question_id, _paper_id, attempt = _seed_attempt(client, teacher_token, klass["id"], student["token"])
    client.put(
        f"/api/v1/attempts/{attempt['id']}/answers/{question_id}",
        headers=auth(student["token"]),
        json={"answer": "A"},
    )
    submitted = client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=auth(student["token"]))
    assert submitted.status_code == 200, submitted.text

    resumed = client.get(f"/api/v1/attempts/{attempt['id']}", headers=auth(student["token"]))
    assert resumed.status_code == 200
    body = resumed.json()["data"]
    assert body["attempt"]["status"] == "submitted"
    assert body["remaining_seconds"] == 0
    assert body["answers"][str(question_id)] == "A"
    assert "answer" not in body["questions"][0]
