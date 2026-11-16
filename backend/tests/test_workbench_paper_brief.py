"""B1：工作台精简试卷 `_paper_brief` 补 `due_at`。

- 学生 `pending` 与教师 `recent_papers` 都带 `due_at`；
- 有截止日期返回格式化字符串，无截止日期返回 `null`。
"""

from __future__ import annotations

import json

from tests.conftest import auth

DUE_AT = "2026-12-31 23:59:59"


def _import_one_judge(client, token, class_id):
    questions = [
        {
            "type": "judge",
            "stem": "UDP 不保证可靠交付。",
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


def _create_published_paper(client, token, class_id, ids, *, title, due_at=None):
    payload = {"title": title, "mode": "fixed", "kind": "practice", "question_ids": ids}
    if due_at is not None:
        payload["due_at"] = due_at
    paper = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(token),
        json=payload,
    )
    assert paper.status_code == 200, paper.text
    paper_id = paper.json()["data"]["id"]
    published = client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(token))
    assert published.status_code == 200, published.text
    return paper_id


def test_pending_and_recent_papers_carry_due_at(client, teacher_token, klass, student):
    ids = _import_one_judge(client, teacher_token, klass["id"])
    with_due = _create_published_paper(
        client, teacher_token, klass["id"], ids, title="有截止卷", due_at=DUE_AT
    )
    without_due = _create_published_paper(
        client, teacher_token, klass["id"], ids, title="无截止卷"
    )

    # 学生待办 pending：有截止为格式化字符串，无截止为 null
    me = client.get("/api/v1/me/workbench", headers=auth(student["token"]))
    assert me.status_code == 200, me.text
    pending = {item["id"]: item for item in me.json()["data"]["pending"]}
    assert with_due in pending and without_due in pending
    assert pending[with_due]["due_at"] == DUE_AT
    assert pending[without_due]["due_at"] is None

    # 教师最近试卷 recent_papers：同一 _paper_brief 取数，两态一致
    teacher = client.get(
        f"/api/v1/classes/{klass['id']}/workbench", headers=auth(teacher_token)
    )
    assert teacher.status_code == 200, teacher.text
    recent = {
        item["id"]: item for item in teacher.json()["data"]["recent_papers"]
    }
    assert with_due in recent and without_due in recent
    assert recent[with_due]["due_at"] == DUE_AT
    assert recent[without_due]["due_at"] is None
