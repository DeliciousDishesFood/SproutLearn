"""M3.1 题库分类：CRUD、导入归属、按库组卷、试卷 banks。"""

from __future__ import annotations

import json

from tests.conftest import auth, create_class, register_teacher


def _bank(client, token, class_id, name, description=None):
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    return client.post(
        f"/api/v1/classes/{class_id}/banks",
        headers=auth(token),
        json=payload,
    )


def _questions(count, prefix):
    return [
        {
            "type": "judge",
            "stem": f"{prefix} 题 {i}",
            "answer": True,
            "knowledge_tag": "网络",
            "difficulty": "medium",
        }
        for i in range(1, count + 1)
    ]


def _preview(client, token, class_id, questions, *, bank_id=None, name="q.json"):
    data = {"bank_id": str(bank_id)} if bank_id is not None else None
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        data=data,
        files={
            "file": (
                name,
                json.dumps(questions, ensure_ascii=False).encode(),
                "application/json",
            )
        },
    )


def _commit(client, token, class_id, token_value, *, bank_id=None):
    payload = {"token": token_value}
    if bank_id is not None:
        payload["bank_id"] = bank_id
    return client.post(
        f"/api/v1/classes/{class_id}/questions/import/commit",
        headers=auth(token),
        json=payload,
    )


def _import_to_bank(client, token, class_id, bank_id, count, prefix="归库"):
    preview = _preview(
        client,
        token,
        class_id,
        _questions(count, prefix),
        bank_id=bank_id,
    )
    assert preview.status_code == 200, preview.text
    commit = _commit(
        client,
        token,
        class_id,
        preview.json()["data"]["token"],
        bank_id=bank_id,
    )
    assert commit.status_code == 200, commit.text
    return commit.json()["data"]["question_ids"]


def test_bank_crud_uniqueness_nonempty_and_cross_class(client, teacher_token, klass):
    created = _bank(client, teacher_token, klass["id"], "第5章 网络基础", "章节库")
    assert created.status_code == 200, created.text
    bank = created.json()["data"]
    assert bank["question_count"] == 0

    duplicate = _bank(client, teacher_token, klass["id"], "第5章 网络基础")
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40913

    renamed = client.patch(
        f"/api/v1/banks/{bank['id']}",
        headers=auth(teacher_token),
        json={"name": "第5章 网络", "description": "改名"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["data"]["name"] == "第5章 网络"
    assert renamed.json()["data"]["description"] == "改名"

    empty = _bank(client, teacher_token, klass["id"], "空库")
    empty_id = empty.json()["data"]["id"]
    deleted = client.delete(f"/api/v1/banks/{empty_id}", headers=auth(teacher_token))
    assert deleted.status_code == 200
    listed = client.get(f"/api/v1/classes/{klass['id']}/banks", headers=auth(teacher_token))
    assert all(item["id"] != empty_id for item in listed.json()["data"])

    _import_to_bank(client, teacher_token, klass["id"], bank["id"], 1, "删除保护")
    protected = client.delete(f"/api/v1/banks/{bank['id']}", headers=auth(teacher_token))
    assert protected.status_code == 409
    assert protected.json()["code"] == 40912

    teacher_b = register_teacher(client, "m31-b@school.edu.cn")
    class_b = create_class(client, teacher_b["token"], "M3.1 B 班")
    assert client.get(
        f"/api/v1/classes/{klass['id']}/banks", headers=auth(teacher_b["token"])
    ).json()["code"] == 40302
    assert client.patch(
        f"/api/v1/banks/{bank['id']}",
        headers=auth(teacher_b["token"]),
        json={"name": "越权"},
    ).json()["code"] == 40302
    assert client.delete(
        f"/api/v1/banks/{bank['id']}", headers=auth(teacher_b["token"])
    ).json()["code"] == 40302
    assert class_b["id"] != klass["id"]


def test_import_to_bank_and_auto_bank(client, teacher_token, klass):
    bank = _bank(client, teacher_token, klass["id"], "指定导入库").json()["data"]
    preview = _preview(
        client,
        teacher_token,
        klass["id"],
        _questions(20, "指定库"),
        bank_id=bank["id"],
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()["data"]
    assert body["bank_id"] == bank["id"]
    assert body["bank_name"] == "指定导入库"
    assert body["valid_count"] == 20
    commit = _commit(
        client, teacher_token, klass["id"], body["token"], bank_id=bank["id"]
    )
    assert commit.status_code == 200, commit.text
    banks = client.get(
        f"/api/v1/classes/{klass['id']}/banks", headers=auth(teacher_token)
    ).json()["data"]
    target = next(item for item in banks if item["id"] == bank["id"])
    assert target["question_count"] == 20

    filtered = client.get(
        f"/api/v1/classes/{klass['id']}/questions?bank_id={bank['id']}",
        headers=auth(teacher_token),
    )
    assert filtered.status_code == 200
    assert filtered.json()["data"]["total"] == 20
    assert all(item["bank_id"] == bank["id"] for item in filtered.json()["data"]["list"])
    assert filtered.json()["data"]["list"][0]["bank_name"] == "指定导入库"

    auto_preview = _preview(
        client, teacher_token, klass["id"], _questions(3, "自动库"), name="自动导入.json"
    )
    assert auto_preview.json()["data"]["bank_id"] is None
    assert auto_preview.json()["data"]["suggested_bank_name"] == "自动导入"
    auto_commit = _commit(
        client, teacher_token, klass["id"], auto_preview.json()["data"]["token"]
    )
    assert auto_commit.status_code == 200, auto_commit.text
    banks = client.get(
        f"/api/v1/classes/{klass['id']}/banks", headers=auth(teacher_token)
    ).json()["data"]
    assert any(item["name"].startswith("导入题库-") for item in banks)


def test_fixed_paper_from_single_bank_and_legacy_question_ids(client, teacher_token, klass):
    bank = _bank(client, teacher_token, klass["id"], "固定库").json()["data"]
    ids = _import_to_bank(client, teacher_token, klass["id"], bank["id"], 4, "固定")
    fixed = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "整库固定卷", "mode": "fixed", "bank_ids": [bank["id"]]},
    )
    assert fixed.status_code == 200, fixed.text
    data = fixed.json()["data"]
    assert data["question_count"] == 4
    assert data["total_score"] == 4.0
    assert [question["seq"] for question in data["questions"]] == [1, 2, 3, 4]
    assert data["banks"] == [{"id": bank["id"], "name": "固定库"}]

    legacy = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "旧勾选卷", "mode": "fixed", "question_ids": ids[:3]},
    )
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["data"]["question_count"] == 3


def test_fixed_paper_rejects_both_question_ids_and_bank_ids(client, teacher_token, klass):
    bank = _bank(client, teacher_token, klass["id"], "二选一库").json()["data"]
    ids = _import_to_bank(client, teacher_token, klass["id"], bank["id"], 1)
    response = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={
            "title": "冲突卷",
            "mode": "fixed",
            "question_ids": ids,
            "bank_ids": [bank["id"]],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_random_paper_scoped_to_two_banks_and_insufficient_range(client, teacher_token, klass):
    bank_a = _bank(client, teacher_token, klass["id"], "随机A").json()["data"]
    bank_b = _bank(client, teacher_token, klass["id"], "随机B").json()["data"]
    _import_to_bank(client, teacher_token, klass["id"], bank_a["id"], 5, "A")
    _import_to_bank(client, teacher_token, klass["id"], bank_b["id"], 5, "B")
    random_paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={
            "title": "两库随机",
            "mode": "random",
            "bank_ids": [bank_a["id"], bank_b["id"]],
            "count": 8,
        },
    )
    assert random_paper.status_code == 200, random_paper.text
    data = random_paper.json()["data"]
    assert data["question_count"] == 8
    bank_ids = {question["id"] for question in data["questions"]}
    assert len(bank_ids) == 8
    assert {item["id"] for item in data["banks"]} == {bank_a["id"], bank_b["id"]}

    small = _bank(client, teacher_token, klass["id"], "小库").json()["data"]
    _import_to_bank(client, teacher_token, klass["id"], small["id"], 3, "小")
    insufficient = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={
            "title": "范围不足",
            "mode": "random",
            "bank_ids": [small["id"]],
            "count": 8,
        },
    )
    assert insufficient.status_code == 409
    assert insufficient.json()["code"] == 40908
    assert "当前范围 3 题" in insufficient.json()["message"]


def test_question_list_bank_filter_and_paper_detail_banks(client, teacher_token, klass):
    bank = _bank(client, teacher_token, klass["id"], "详情库").json()["data"]
    _import_to_bank(client, teacher_token, klass["id"], bank["id"], 2, "详情")
    paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "详情卷", "mode": "fixed", "bank_ids": [bank["id"]]},
    )
    assert paper.status_code == 200
    detail = client.get(
        f"/api/v1/papers/{paper.json()['data']['id']}",
        headers=auth(teacher_token),
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["banks"] == [{"id": bank["id"], "name": "详情库"}]

    listed = client.get(
        f"/api/v1/classes/{klass['id']}/questions",
        headers=auth(teacher_token),
    )
    assert all(item["bank_id"] == bank["id"] for item in listed.json()["data"]["list"])
    assert all(item["bank_name"] == "详情库" for item in listed.json()["data"]["list"])
