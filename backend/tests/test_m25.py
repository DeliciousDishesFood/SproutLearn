"""M2.5 后端：SSE 讲评、四格式导入、动态表头、类型推断、rows 覆盖。"""

from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from app.services import question_service
from tests.conftest import auth

FIXTURES = Path(__file__).parent / "fixtures"


def _upload(client, token, class_id, name, content, mime):
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={"file": (name, content, mime)},
    )


def _json_10():
    return [
        {
            "题目": f"JSON 题目 {i}",
            "正确答案": "对" if i % 2 else "2",
            "考点": "历史",
            "难度": "easy",
        }
        for i in range(1, 11)
    ]


def _xlsx(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _preview_ok(client, teacher_token, class_id, name, content, mime):
    response = _upload(client, teacher_token, class_id, name, content, mime)
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["valid_count"] == 10, body
    assert body["error_count"] == 0, body["errors"]
    return body


def _create_question(client, teacher_token, class_id):
    response = _upload(
        client,
        teacher_token,
        class_id,
        "q.json",
        json.dumps(
            [{"type": "blank", "stem": "光合作用的产物？", "answer": ["氧气", "有机物"], "analysis": "绿色植物利用光能合成有机物。"}],
            ensure_ascii=False,
        ).encode(),
        "application/json",
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["token"]
    commit = client.post(
        f"/api/v1/classes/{class_id}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": token},
    )
    assert commit.status_code == 200, commit.text
    return commit.json()["data"]["question_ids"][0]


def _events(response):
    events = []
    event = None
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            events.append((event, json.loads(line[6:])))
    return events


def test_stream_template_first_and_sync_explain_compatible(client, teacher_token, klass, monkeypatch):
    monkeypatch.setattr(question_service, "build_chain", lambda settings: [])
    monkeypatch.setattr(question_service, "_cache_get", lambda question: None)
    question_id = _create_question(client, teacher_token, klass["id"])
    started = time.perf_counter()
    with client.stream(
        "POST",
        f"/api/v1/questions/{question_id}/explain/stream",
        headers=auth(teacher_token),
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers.get("x-accel-buffering") == "no"
        first_event_at = None
        events = []
        event = None
        for line in response.iter_lines():
            if isinstance(line, bytes):
                line = line.decode()
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                events.append((event, json.loads(line[6:])))
                if event == "delta" and first_event_at is None:
                    first_event_at = time.perf_counter() - started

    assert first_event_at is not None and first_event_at < 1.0
    assert events[0][0] == "meta"
    assert events[1][0] == "delta" and events[1][1]["content"]
    assert events[-1][0] == "done"
    assert events[-1][1]["engine"] == "template"
    assert events[-1][1]["degraded"] is True

    sync = client.post(f"/api/v1/questions/{question_id}/explain", headers=auth(teacher_token))
    assert sync.status_code == 200
    assert set(sync.json()["data"]) == {"explanation", "engine", "degraded"}


def test_stream_ai_delta_when_router_returns(client, teacher_token, klass, monkeypatch):
    question_id = _create_question(client, teacher_token, klass["id"])
    monkeypatch.setattr(
        question_service,
        "_ai_explain_iter",
        lambda question: iter(["AI 补充：先看题干，", "再核对标准答案。"]),
    )
    with client.stream(
        "POST",
        f"/api/v1/questions/{question_id}/explain/stream",
        headers=auth(teacher_token),
    ) as response:
        events = _events(response)
    assert events[0][0] == "meta"
    assert events[-1][0] == "done"
    assert events[-1][1]["engine"] == "llm"
    assert any(step == "delta" and "AI 补充" in data["content"] for step, data in events)


def test_import_four_formats_ten_each(client, teacher_token, klass):
    json_body = _preview_ok(
        client,
        teacher_token,
        klass["id"],
        "questions.json",
        json.dumps(_json_10(), ensure_ascii=False).encode(),
        "application/json",
    )
    assert json_body["mapping"]["题目"] == "stem"
    assert json_body["mapping"]["正确答案"] == "answer"

    headers = ["题目", "正确答案", "考点", "难度"]
    rows = [["XLSX 题目", "对", "历史", "easy"] for _ in range(10)]
    _preview_ok(
        client,
        teacher_token,
        klass["id"],
        "questions.xlsx",
        _xlsx(headers, rows),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    _preview_ok(
        client,
        teacher_token,
        klass["id"],
        "questions.xls",
        (FIXTURES / "m25_10.xls").read_bytes(),
        "application/vnd.ms-excel",
    )
    csv_text = "题目,正确答案,考点,难度\n" + "\n".join(
        f"CSV 题目 {i},对,历史,easy" for i in range(10)
    )
    _preview_ok(
        client,
        teacher_token,
        klass["id"],
        "questions.csv",
        csv_text.encode("utf-8-sig"),
        "text/csv",
    )
    _preview_ok(
        client,
        teacher_token,
        klass["id"],
        "questions-gb.csv",
        csv_text.encode("gb18030"),
        "text/csv",
    )


def test_chinese_synonyms_twenty(client, teacher_token, klass):
    rows = [[f"同步题目 {i}", "对", "考点", "medium"] for i in range(20)]
    response = _upload(
        client,
        teacher_token,
        klass["id"],
        "synonyms.xlsx",
        _xlsx(["题目", "正确答案", "考点", "难度"], rows),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["valid_count"] == 20
    assert body["mapping"] == {"题目": "stem", "正确答案": "answer", "考点": "knowledge_tag", "难度": "difficulty"}


def test_type_inference_four_types(client, teacher_token, klass):
    rows = [
        ["单选", "A", "甲", "乙", "", "A", "知识点"],
        ["多选", "A", "甲", "乙", "丙", "A,C", "知识点"],
        ["判断题", "", "", "", "", "对", "知识点"],
        ["填空题", "", "", "", "", "2", "知识点"],
    ]
    response = _upload(
        client,
        teacher_token,
        klass["id"],
        "infer.xlsx",
        _xlsx(["题目", "选项A", "选项B", "选项C", "选项D", "正确答案", "考点"], rows),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["valid_count"] == 4, body["errors"]
    types = [row["normalized"]["type"] for row in body["rows"]]
    assert types == ["single", "multiple", "judge", "blank"]


def test_unmapped_columns_kept(client, teacher_token, klass):
    response = _upload(
        client,
        teacher_token,
        klass["id"],
        "unknown.csv",
        "题目,正确答案,备注\n未知列题,对,这一列不丢\n".encode("utf-8"),
        "text/csv",
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["unmapped_columns"] == ["备注"]
    assert body["valid_count"] == 1


def test_commit_rows_edit_and_delete(client, teacher_token, klass):
    rows = [[f"编辑题 {i}", "对", "历史", "easy"] for i in range(20)]
    preview = _upload(
        client,
        teacher_token,
        klass["id"],
        "edit.xlsx",
        _xlsx(["题目", "正确答案", "考点", "难度"], rows),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    body = preview.json()["data"]
    assert body["valid_count"] == 20
    edited = body["rows"][:18]
    edited[0]["normalized"]["stem"] = "已改写的题干"
    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": body["token"], "rows": edited},
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["data"]["inserted"] == 18
    listed = client.get(
        f"/api/v1/classes/{klass['id']}/questions?page_size=50",
        headers=auth(teacher_token),
    )
    assert listed.status_code == 200
    items = listed.json()["data"]["list"]
    assert listed.json()["data"]["total"] == 18
    assert any(item["stem"] == "已改写的题干" for item in items)


def test_commit_rows_revalidates_invalid_edit(client, teacher_token, klass):
    preview = _upload(
        client,
        teacher_token,
        klass["id"],
        "invalid.json",
        json.dumps([{"题目": "原题", "正确答案": "对"}], ensure_ascii=False).encode(),
        "application/json",
    )
    body = preview.json()["data"]
    rows = body["rows"]
    rows[0]["normalized"]["answer"] = None
    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": body["token"], "rows": rows},
    )
    assert commit.status_code == 422
    assert commit.json()["code"] == 42203
    listed = client.get(
        f"/api/v1/classes/{klass['id']}/questions?page_size=50",
        headers=auth(teacher_token),
    )
    assert listed.json()["data"]["total"] == 0
