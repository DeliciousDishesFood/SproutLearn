"""B0：结果接口越权拦截。

- 学生 doing 状态调 result → 业务码 40910；
- 学生提交后调 result → 200；
- 教师看同一份 doing 作答 → 200（教师路径不受影响）。
"""

from __future__ import annotations

import json

from tests.conftest import auth


def _import_one_judge(client, token, class_id):
    questions = [
        {
            "type": "judge",
            "stem": "TCP 是可靠传输协议。",
            "answer": True,
            "difficulty": "easy",
        }
    ]
    preview = client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "q.json",
                json.dumps(questions, ensure_ascii=False).encode("utf-8"),
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


def _create_published_paper(client, token, class_id, ids, *, title="B0 拦截卷"):
    paper = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(token),
        json={"title": title, "mode": "fixed", "kind": "practice", "question_ids": ids},
    )
    assert paper.status_code == 200, paper.text
    paper_id = paper.json()["data"]["id"]
    published = client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(token))
    assert published.status_code == 200, published.text
    return paper_id


def test_result_guard_student_doing_blocked_teacher_and_submitted_ok(
    client, teacher_token, klass, student
):
    ids = _import_one_judge(client, teacher_token, klass["id"])
    paper_id = _create_published_paper(client, teacher_token, klass["id"], ids)

    attempt = client.post(
        f"/api/v1/papers/{paper_id}/attempts", headers=auth(student["token"])
    )
    assert attempt.status_code == 200, attempt.text
    attempt_id = attempt.json()["data"]["id"]

    # 情形一：学生 doing 状态查看结果 → 40910 拦截
    blocked = client.get(
        f"/api/v1/attempts/{attempt_id}/result", headers=auth(student["token"])
    )
    assert blocked.status_code == 409, blocked.text
    blocked_body = blocked.json()
    assert blocked_body["code"] == 40910
    assert blocked_body["message"] == "本次作答尚未提交，不能查看结果"

    # 情形二：教师看同一份 doing 作答 → 仍 200，教师路径不受影响
    teacher_view = client.get(
        f"/api/v1/attempts/{attempt_id}/result", headers=auth(teacher_token)
    )
    assert teacher_view.status_code == 200, teacher_view.text
    assert teacher_view.json()["data"]["attempt"]["id"] == attempt_id

    # 情形三：学生提交后查看结果 → 200
    saved = client.put(
        f"/api/v1/attempts/{attempt_id}/answers/{ids[0]}",
        headers=auth(student["token"]),
        json={"answer": True},
    )
    assert saved.status_code == 200, saved.text
    submitted = client.post(
        f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student["token"])
    )
    assert submitted.status_code == 200, submitted.text

    after_submit = client.get(
        f"/api/v1/attempts/{attempt_id}/result", headers=auth(student["token"])
    )
    assert after_submit.status_code == 200, after_submit.text
    assert after_submit.json()["data"]["attempt"]["status"] == "submitted"
