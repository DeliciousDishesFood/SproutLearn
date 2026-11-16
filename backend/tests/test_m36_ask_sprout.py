"""M3.6 练习页“问问小芽”接口验收。"""

from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

from app.models.question import Question
from app.services import student_chat_service
from app.utils import cache_keys
from tests.conftest import auth, join_student


def _import_question(client, token, class_id, *, answer=True, analysis="解析"):
    body = [
        {
            "type": "judge",
            "stem": "TCP 属于传输层吗？",
            "answer": answer,
            "analysis": analysis,
            "knowledge_tag": "传输层",
        }
    ]
    preview = client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "q.json",
                json.dumps(body, ensure_ascii=False).encode(),
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
    return commit.json()["data"]["question_ids"][0]


def _paper(client, token, class_id, question_id, *, kind="practice"):
    response = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(token),
        json={
            "title": f"M3.6 {kind}",
            "mode": "fixed",
            "kind": kind,
            "question_ids": [question_id],
        },
    )
    assert response.status_code == 200, response.text
    paper = response.json()["data"]
    published = client.post(
        f"/api/v1/papers/{paper['id']}/publish", headers=auth(token)
    )
    assert published.status_code == 200, published.text
    return paper


def _attempt(client, token, paper_id):
    response = client.post(
        f"/api/v1/papers/{paper_id}/attempts", headers=auth(token)
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


class _FakeRouter:
    pass


def _fake_llm(monkeypatch, captured):
    def fake_race(router, messages, **kwargs):
        captured.extend(messages)
        return SimpleNamespace(content="先别急着选答案，看看 TCP 在协议栈的哪一层。")

    monkeypatch.setattr(student_chat_service, "build_router", lambda settings: _FakeRouter())
    monkeypatch.setattr(
        student_chat_service.bot_chat_service, "_race_chat", fake_race
    )


def test_practice_ask_returns_answer_and_sources_without_leak(
    client, teacher_token, klass, student, monkeypatch
):
    qid = _import_question(
        client, teacher_token, klass["id"], answer=True, analysis="LEAK_ANALYSIS"
    )
    paper = _paper(client, teacher_token, klass["id"], qid, kind="practice")
    attempt = _attempt(client, student["token"], paper["id"])
    with client.testing_session() as db:  # type: ignore[attr-defined]
        q = db.get(Question, qid)
        q.answer_json = {"value": "LEAK_ANSWER_987"}
        q.analysis = "LEAK_ANALYSIS"
        db.commit()

    captured: list[dict] = []
    _fake_llm(monkeypatch, captured)
    monkeypatch.setattr(
        student_chat_service.bot_chat_service,
        "retrieve_chunks",
        lambda *args, **kwargs: [
            SimpleNamespace(doc_id=7, doc_name="课程讲义.pdf", content="TCP 在传输层。")
        ],
    )
    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={
            "question_id": qid,
            "selected_text": "TCP",
            "message": "为什么不是网络层？",
            "history": [{"role": "user", "content": "上一轮问题"}],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["answer"]
    assert data["sources"] == [{"doc_id": 7, "doc_name": "课程讲义.pdf"}]
    prompt = "\n".join(message["content"] for message in captured)
    assert "LEAK_ANSWER_987" not in prompt
    assert "LEAK_ANALYSIS" not in prompt
    assert "TCP" in prompt and "为什么不是网络层？" in prompt
    assert "课程讲义.pdf" in prompt


def test_exam_and_homework_are_forbidden(client, teacher_token, klass, student):
    qid = _import_question(client, teacher_token, klass["id"])
    for kind in ("exam", "homework"):
        paper = _paper(client, teacher_token, klass["id"], qid, kind=kind)
        attempt = _attempt(client, student["token"], paper["id"])
        response = client.post(
            f"/api/v1/attempts/{attempt['id']}/ask",
            headers=auth(student["token"]),
            json={
                "question_id": qid,
                "selected_text": "TCP",
                "message": "给点提示",
            },
        )
        assert response.status_code == 403
        assert response.json()["code"] == 40301
        assert "当前不是练习模式" in response.json()["message"]


def test_attempt_not_found_other_student_and_question_not_in_paper(
    client, teacher_token, klass, student
):
    qid = _import_question(client, teacher_token, klass["id"])
    paper = _paper(client, teacher_token, klass["id"], qid)
    attempt = _attempt(client, student["token"], paper["id"])

    missing = client.post(
        "/api/v1/attempts/999999/ask",
        headers=auth(student["token"]),
        json={"question_id": qid, "selected_text": "TCP", "message": "提示"},
    )
    assert missing.status_code == 404

    other = join_student(client, klass["invite_code"], "20269999", "其他同学")
    other_response = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(other["token"]),
        json={"question_id": qid, "selected_text": "TCP", "message": "提示"},
    )
    assert other_response.status_code == 403

    wrong_question = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={"question_id": 999999, "selected_text": "TCP", "message": "提示"},
    )
    assert wrong_question.status_code == 404


def test_empty_selected_history_truncation_and_rate_limit(
    client, teacher_token, klass, student, monkeypatch
):
    qid = _import_question(client, teacher_token, klass["id"])
    paper = _paper(client, teacher_token, klass["id"], qid)
    attempt = _attempt(client, student["token"], paper["id"])
    captured: list[dict] = []
    _fake_llm(monkeypatch, captured)
    monkeypatch.setattr(
        student_chat_service.bot_chat_service,
        "retrieve_chunks",
        lambda *args, **kwargs: [],
    )
    empty = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={"question_id": qid, "selected_text": "   ", "message": "提示"},
    )
    assert empty.status_code == 400
    assert empty.json()["code"] == 40001

    history = [
        {"role": "user", "content": f"旧问题{i}"} for i in range(8)
    ]
    response = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={
            "question_id": qid,
            "selected_text": "TCP",
            "message": "现在问题",
            "history": history,
        },
    )
    assert response.status_code == 200, response.text
    prompt = "\n".join(message["content"] for message in captured)
    assert "旧问题0" not in prompt and "旧问题1" not in prompt
    assert "旧问题7" in prompt

    limited = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={"question_id": qid, "selected_text": "TCP", "message": "再问"},
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == 42901


def test_resume_paper_has_kind(client, teacher_token, klass, student):
    qid = _import_question(client, teacher_token, klass["id"])
    paper = _paper(client, teacher_token, klass["id"], qid, kind="practice")
    attempt = _attempt(client, student["token"], paper["id"])
    resume = client.get(
        f"/api/v1/attempts/{attempt['id']}", headers=auth(student["token"])
    )
    assert resume.status_code == 200
    assert resume.json()["data"]["paper"]["kind"] == "practice"


def test_empty_message_400(client, teacher_token, klass, student, monkeypatch):
    qid = _import_question(client, teacher_token, klass["id"])
    paper = _paper(client, teacher_token, klass["id"], qid)
    attempt = _attempt(client, student["token"], paper["id"])
    captured: list[dict] = []
    _fake_llm(monkeypatch, captured)
    monkeypatch.setattr(
        student_chat_service.bot_chat_service, "retrieve_chunks", lambda *a, **k: []
    )
    resp = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={"question_id": qid, "selected_text": "TCP", "message": "   "},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == 40001
    assert captured == []


def test_daily_limit_429(client, teacher_token, klass, student, monkeypatch):
    qid = _import_question(client, teacher_token, klass["id"])
    paper = _paper(client, teacher_token, klass["id"], qid)
    attempt = _attempt(client, student["token"], paper["id"])
    captured: list[dict] = []
    _fake_llm(monkeypatch, captured)
    monkeypatch.setattr(
        student_chat_service.bot_chat_service, "retrieve_chunks", lambda *a, **k: []
    )

    daily_key = cache_keys.ask_sprout_daily_key(
        student["user"]["id"], date.today().isoformat()
    )
    client.fake_redis.set(daily_key, 40, ex=86400)  # type: ignore[attr-defined]

    resp = client.post(
        f"/api/v1/attempts/{attempt['id']}/ask",
        headers=auth(student["token"]),
        json={"question_id": qid, "selected_text": "TCP", "message": "提示"},
    )
    assert resp.status_code == 429, resp.text
    assert resp.json()["code"] == 42901
