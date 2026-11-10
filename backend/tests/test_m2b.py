"""M2B 接口冒烟：导入、组卷、开卷、自动保存、提交、复核、讲评。"""

from __future__ import annotations

import json
from io import BytesIO

from openpyxl import Workbook

from app.services import question_service
from tests.conftest import auth


def _json_file(client, token, class_id, questions):
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "questions.json",
                json.dumps(questions, ensure_ascii=False).encode("utf-8"),
                "application/json",
            )
        },
    )


def _xlsx_file(client, token, class_id, rows, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or ["type", "stem", "optionA", "optionB", "optionC", "optionD", "optionE", "optionF", "answer", "analysis", "knowledge_tag", "difficulty"])
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "questions.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def _sample_questions():
    return [
        {
            "type": "single",
            "stem": "1+1 等于几？",
            "options": [{"key": "A", "text": "2"}, {"key": "B", "text": "3"}],
            "answer": "A",
            "knowledge_tag": "算术",
            "difficulty": "easy",
        },
        {
            "type": "multiple",
            "stem": "以下属于传输层协议的是？",
            "options": [{"key": "A", "text": "TCP"}, {"key": "B", "text": "IP"}, {"key": "C", "text": "UDP"}],
            "answer": ["A", "C"],
            "knowledge_tag": "网络",
            "difficulty": "medium",
        },
        {
            "type": "judge",
            "stem": "TCP 是可靠传输协议。",
            "answer": True,
            "knowledge_tag": "网络",
            "difficulty": "easy",
        },
        {
            "type": "blank",
            "stem": "1+1 的答案是？",
            "answer": ["2"],
            "analysis": "基础算术",
            "knowledge_tag": "算术",
            "difficulty": "easy",
        },
    ]


def test_json_xlsx_import_and_commit(client, teacher_token, klass):
    questions = _sample_questions()
    preview = _json_file(client, teacher_token, klass["id"], questions)
    assert preview.status_code == 200, preview.text
    body = preview.json()["data"]
    assert body["valid_count"] == 4 and body["error_count"] == 0
    assert body["token"]

    bad = [*questions, {**questions[0], "answer": None}]
    bad_preview = _json_file(client, teacher_token, klass["id"], bad)
    assert bad_preview.status_code == 200
    assert bad_preview.json()["data"]["valid_count"] == 4
    assert bad_preview.json()["data"]["errors"][0]["column"] == "answer"
    assert bad_preview.json()["data"]["errors"][0]["index"] == 4

    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": body["token"]},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["data"]["inserted"] == 4

    xlsx = _xlsx_file(
        client,
        teacher_token,
        klass["id"],
        [
            ["single", "2+2", "4", "5", "", "", "", "", "A", "", "算术", "easy"],
            ["judge", "UDP 可靠。", "", "", "", "", "", "", "false", "", "网络", "easy"],
        ],
    )
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.json()["data"]["valid_count"] == 2

    missing = _xlsx_file(
        client,
        teacher_token,
        klass["id"],
        [["single", "x", "a", "b", "", "", "", "", "A", "", "t", "easy"]],
        headers=["type", "stem", "optionA", "optionB", "optionC", "optionD", "optionE", "optionF", "analysis", "knowledge_tag", "difficulty"],
    )
    assert missing.status_code == 422
    assert missing.json()["code"] == 42203
    assert missing.json()["data"]["column"] == "answer"


def test_paper_attempt_submit_review_and_explain(client, teacher_token, klass, student):
    questions = _sample_questions()
    preview = _json_file(client, teacher_token, klass["id"], questions)
    token = preview.json()["data"]["token"]
    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": token},
    )
    ids = commit.json()["data"]["question_ids"]
    assert len(ids) == 4

    paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "M2B 单元卷", "mode": "fixed", "question_ids": ids},
    )
    assert paper.status_code == 200, paper.text
    paper_id = paper.json()["data"]["id"]
    assert paper.json()["data"]["question_count"] == 4
    assert paper.json()["data"]["total_score"] == 4.0

    published = client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(teacher_token))
    assert published.status_code == 200, published.text
    assert published.json()["data"]["status"] == "published"

    first = client.post(f"/api/v1/papers/{paper_id}/attempts", headers=auth(student["token"]))
    second = client.post(f"/api/v1/papers/{paper_id}/attempts", headers=auth(student["token"]))
    assert first.status_code == 200, first.text
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    attempt_id = first.json()["data"]["id"]
    assert len(first.json()["data"]["questions"]) == 4

    answers = {
        ids[0]: "A",
        ids[1]: ["A", "C"],
        ids[2]: True,
        ids[3]: ["2"],
    }
    for question_id, answer in answers.items():
        saved = client.put(
            f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
            headers=auth(student["token"]),
            json={"answer": answer},
        )
        assert saved.status_code == 200, saved.text
    # 同题重复 upsert
    saved_again = client.put(
        f"/api/v1/attempts/{attempt_id}/answers/{ids[0]}",
        headers=auth(student["token"]),
        json={"answer": "A"},
    )
    assert saved_again.status_code == 200

    submitted = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student["token"]))
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()["data"]
    assert result["attempt"]["status"] == "submitted"
    assert result["attempt"]["total_score"] == 4.0
    assert result["attempt"]["full_score"] == 4.0
    assert all(item["is_correct"] for item in result["answers"])

    repeat = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student["token"]))
    assert repeat.status_code == 200
    assert repeat.json()["data"]["attempt"]["total_score"] == 4.0

    result_view = client.get(f"/api/v1/attempts/{attempt_id}/result", headers=auth(student["token"]))
    assert result_view.status_code == 200
    assert result_view.json()["data"]["attempt"]["id"] == attempt_id

    answer_record_id = result["answers"][0]["answer_record_id"]
    review = client.post(
        f"/api/v1/attempts/{attempt_id}/reviews",
        headers=auth(teacher_token),
        json={"answer_record_id": answer_record_id, "new_score": 0, "comment": "复核降分"},
    )
    assert review.status_code == 200, review.text
    reviewed = review.json()["data"]
    assert reviewed["attempt"]["status"] == "graded"
    assert reviewed["attempt"]["total_score"] == 3.0
    assert reviewed["reviews"][0]["new_score"] == 0.0

    explain = client.post(f"/api/v1/questions/{ids[0]}/explain", headers=auth(teacher_token))
    assert explain.status_code == 200
    assert explain.json()["data"]["explanation"]
    assert explain.json()["data"]["engine"] in ("llm", "template")


def test_explain_falls_back_to_template_when_router_fails(
    client, teacher_token, klass, monkeypatch
):
    questions = _sample_questions()[:1]
    preview = _json_file(client, teacher_token, klass["id"], questions)
    committed = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": preview.json()["data"]["token"]},
    )
    question_id = committed.json()["data"]["question_ids"][0]

    def _boom(settings=None):
        raise RuntimeError("all providers down")

    monkeypatch.setattr(question_service, "build_router", _boom)
    explain = client.post(f"/api/v1/questions/{question_id}/explain", headers=auth(teacher_token))
    assert explain.status_code == 200
    body = explain.json()["data"]
    assert body["engine"] == "template"
    assert body["degraded"] is True
    assert body["explanation"]
