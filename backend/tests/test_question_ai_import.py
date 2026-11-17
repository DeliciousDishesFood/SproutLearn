"""M3.7 题库 AI 智能识别导入验收。"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

from app.models.question import Question
from app.services import question_ai_import
from app.services.llm.base import AllProvidersFailed
from tests.conftest import auth, create_class, register_teacher

TEXT = """
1. TCP 属于传输层。
答案：对
解析：TCP 是传输层协议。

2. UDP 是可靠传输。
答案：错
解析：UDP 不保证可靠。
"""

VALID_JSON = json.dumps(
    {
        "questions": [
            {
                "type": "judge",
                "stem": "TCP 属于传输层。",
                "answer": True,
                "analysis": "TCP 是传输层协议。",
                "knowledge_tag": "传输层",
                "difficulty": "easy",
                "confidence": 0.95,
            },
            {
                "type": "judge",
                "stem": "UDP 是可靠传输。",
                "answer": False,
                "analysis": "UDP 不保证可靠。",
                "knowledge_tag": "传输层",
                "difficulty": "easy",
                "confidence": 0.9,
            },
        ],
        "warnings": ["模型提示：这是两题"],
    },
    ensure_ascii=False,
)


class _FakeRouter:
    def __init__(self, content: str):
        self.content = content
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return SimpleNamespace(content=self.content, model="fake-model", degraded=False)


def _fake_llm(monkeypatch, content):
    router = _FakeRouter(content)
    monkeypatch.setattr(question_ai_import, "build_router", lambda settings: router)
    return router


def _upload(client, token, class_id, *, name="sql题库.txt", content=TEXT, max_questions=50):
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/ai-preview",
        headers=auth(token),
        data={"max_questions": str(max_questions)},
        files={"file": (name, content.encode("utf-8"), "text/plain")},
    )


def test_ai_preview_success_and_commit(client, teacher_token, klass, monkeypatch):
    router = _fake_llm(monkeypatch, VALID_JSON)
    response = _upload(client, teacher_token, klass["id"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["mode"] == "ai"
    assert data["engine"] == "llm"
    assert data["model"] == "fake-model"
    assert data["valid_count"] == 2
    assert data["total"] == 2
    assert len(data["rows"]) == 2
    assert data["token"]
    assert data["source_name"] == "sql题库.txt"
    assert "模型提示：这是两题" in data["warnings"]
    assert router.calls == 1

    with client.testing_session() as db:  # type: ignore[attr-defined]
        assert db.query(Question).count() == 0

    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": data["token"]},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["data"]["inserted"] == 2
    with client.testing_session() as db:  # type: ignore[attr-defined]
        assert db.query(Question).count() == 2


def test_ai_preview_image_and_empty_text(client, teacher_token, klass):
    image = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/ai-preview",
        headers=auth(teacher_token),
        files={"file": ("题目.png", b"\x89PNG", "image/png")},
    )
    assert image.status_code == 422
    assert image.json()["code"] == 42203
    assert "图片识别暂未开放" in image.json()["message"]

    empty = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/ai-preview",
        headers=auth(teacher_token),
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 422
    assert empty.json()["code"] == 42203


def test_ai_preview_llm_unavailable_and_bad_json(client, teacher_token, klass, monkeypatch):
    def unavailable(settings):
        raise AllProvidersFailed([])

    monkeypatch.setattr(question_ai_import, "build_router", unavailable)
    failed = _upload(client, teacher_token, klass["id"])
    assert failed.status_code == 503
    assert failed.json()["code"] == 50301

    _fake_llm(monkeypatch, "不是 JSON")
    bad = _upload(client, teacher_token, klass["id"])
    assert bad.status_code == 422
    assert bad.json()["code"] == 42203


def test_ai_preview_partial_invalid_and_dedup(client, teacher_token, klass, monkeypatch):
    payload = {
        "questions": [
            {
                "type": "judge",
                "stem": "有答案题。",
                "answer": True,
                "difficulty": "easy",
            },
            {
                "type": "judge",
                "stem": "缺答案题。",
                "difficulty": "easy",
            },
        ]
    }
    _fake_llm(monkeypatch, json.dumps(payload, ensure_ascii=False))
    response = _upload(client, teacher_token, klass["id"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["valid_count"] == 1
    assert data["error_count"] == 1
    assert any("原文未识别到答案" in item["message"] for item in data["errors"])

    dup = {
        "questions": [
            {"type": "judge", "stem": "重复题。", "answer": True, "difficulty": "easy"},
            {"type": "judge", "stem": "重复题。", "answer": False, "difficulty": "easy"},
        ]
    }
    _fake_llm(monkeypatch, json.dumps(dup, ensure_ascii=False))
    duplicate = _upload(client, teacher_token, klass["id"])
    assert duplicate.status_code == 200, duplicate.text
    body = duplicate.json()["data"]
    assert body["valid_count"] == 1
    assert any("题干重复" in warning for warning in body["warnings"])


def test_ai_preview_permissions_and_max_questions(client, teacher_token, klass, student, monkeypatch):
    _fake_llm(monkeypatch, VALID_JSON)
    student_call = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/ai-preview",
        headers=auth(student["token"]),
        files={"file": ("q.txt", TEXT.encode(), "text/plain")},
    )
    assert student_call.status_code == 403
    assert student_call.json()["code"] == 40301

    teacher_b = register_teacher(client, "m37-b@school.edu.cn")
    create_class(client, teacher_b["token"], "M37 B 班")
    cross = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/ai-preview",
        headers=auth(teacher_b["token"]),
        files={"file": ("q.txt", TEXT.encode(), "text/plain")},
    )
    assert cross.status_code == 403
    assert cross.json()["code"] == 40302

    for value in (0, 101):
        invalid = _upload(client, teacher_token, klass["id"], max_questions=value)
        assert invalid.status_code in (400, 422)
        assert invalid.json()["code"] == 40001


def test_ai_preview_rate_limit(client, teacher_token, klass, monkeypatch):
    _fake_llm(monkeypatch, VALID_JSON)
    monkeypatch.setattr(question_ai_import, "now_naive", lambda: datetime(2026, 1, 1, 12, 0, 0))
    for _ in range(3):
        response = _upload(client, teacher_token, klass["id"])
        assert response.status_code == 200, response.text
    limited = _upload(client, teacher_token, klass["id"])
    assert limited.status_code == 429
    assert limited.json()["code"] == 42901
