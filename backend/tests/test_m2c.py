"""M2C 后端：撤回、blank_mode、三类列表。"""

from __future__ import annotations


from app.services.grading.blank import grade_blank
from tests.conftest import auth, create_class, join_student, register_teacher
from tests.test_m2b import _json_file, _sample_questions


class FakeJev:
    def __init__(self, *, noul=0.9, confidence=0.9):
        self.noul = noul
        self.confidence = confidence
        self.calls = 0

    def available(self):
        return True

    def evaluate(self, *, state, questions, transport="auto"):
        self.calls += 1
        from app.services.llm.jev_client import JevAnswer, JevResult

        return JevResult(
            answers={
                "blank": JevAnswer(
                    key="blank",
                    type="noul",
                    confidence=self.confidence,
                    noul=self.noul,
                    probabilities={},
                )
            },
            usage={},
            latency_ms=1.0,
            transport="bearer",
            raw={},
        )


def _seed_paper(client, token, class_id, *, blank_mode=None):
    preview = _json_file(client, token, class_id, _sample_questions())
    assert preview.status_code == 200, preview.text
    commit = client.post(
        f"/api/v1/classes/{class_id}/questions/import/commit",
        headers=auth(token),
        json={"token": preview.json()["data"]["token"]},
    )
    assert commit.status_code == 200, commit.text
    ids = commit.json()["data"]["question_ids"]
    payload = {"title": "M2C 测试卷", "mode": "fixed", "question_ids": ids}
    if blank_mode is not None:
        payload["blank_mode"] = blank_mode
    paper = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(token),
        json=payload,
    )
    assert paper.status_code == 200, paper.text
    return ids, paper.json()["data"]


def _publish(client, token, paper_id):
    response = client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _submit_all(client, student_token, paper_id, ids):
    attempt = client.post(f"/api/v1/papers/{paper_id}/attempts", headers=auth(student_token))
    assert attempt.status_code == 200, attempt.text
    attempt_id = attempt.json()["data"]["id"]
    answers = {ids[0]: "A", ids[1]: ["A", "C"], ids[2]: True, ids[3]: ["2"]}
    for question_id, answer in answers.items():
        saved = client.put(
            f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
            headers=auth(student_token),
            json={"answer": answer},
        )
        assert saved.status_code == 200, saved.text
    submitted = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student_token))
    assert submitted.status_code == 200, submitted.text
    return attempt_id


def test_withdraw_permissions_and_state(client, teacher_token, klass, student):
    _, paper = _seed_paper(client, teacher_token, klass["id"])
    paper_id = paper["id"]
    _publish(client, teacher_token, paper_id)

    # 学生 / B 班教师均 40302
    assert client.patch(f"/api/v1/papers/{paper_id}/withdraw", headers=auth(student["token"])).json()["code"] == 40302
    teacher_b = register_teacher(client, "m2c-b@school.edu.cn")
    class_b = create_class(client, teacher_b["token"], "M2C B 班")
    assert client.patch(f"/api/v1/papers/{paper_id}/withdraw", headers=auth(teacher_b["token"])).json()["code"] == 40302

    # 创建者撤回成功
    withdrawn = client.patch(f"/api/v1/papers/{paper_id}/withdraw", headers=auth(teacher_token))
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["data"]["status"] == "closed"

    # 再撤回 40911
    again = client.patch(f"/api/v1/papers/{paper_id}/withdraw", headers=auth(teacher_token))
    assert again.status_code == 409
    assert again.json()["code"] == 40911

    # draft 撤回 40911
    _, draft = _seed_paper(client, teacher_token, klass["id"])
    draft_resp = client.patch(f"/api/v1/papers/{draft['id']}/withdraw", headers=auth(teacher_token))
    assert draft_resp.status_code == 409
    assert draft_resp.json()["code"] == 40911
    assert class_b["id"] != klass["id"]


def test_withdraw_hides_student_list_and_keeps_result(client, teacher_token, klass, student):
    ids, paper = _seed_paper(client, teacher_token, klass["id"])
    _publish(client, teacher_token, paper["id"])
    attempt_id = _submit_all(client, student["token"], paper["id"], ids)

    before = client.get(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(student["token"]),
    )
    assert before.status_code == 200
    assert before.json()["data"]["total"] == 1

    withdraw = client.patch(f"/api/v1/papers/{paper['id']}/withdraw", headers=auth(teacher_token))
    assert withdraw.status_code == 200

    after = client.get(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(student["token"]),
    )
    assert after.status_code == 200
    assert after.json()["data"]["total"] == 0

    result = client.get(f"/api/v1/attempts/{attempt_id}/result", headers=auth(student["token"]))
    assert result.status_code == 200
    assert result.json()["data"]["attempt"]["id"] == attempt_id


def test_withdraw_edit_and_republish_chain(client, teacher_token, klass):
    ids, paper = _seed_paper(client, teacher_token, klass["id"])
    _publish(client, teacher_token, paper["id"])
    assert client.patch(f"/api/v1/papers/{paper['id']}/withdraw", headers=auth(teacher_token)).status_code == 200

    edited = client.patch(
        f"/api/v1/questions/{ids[0]}",
        headers=auth(teacher_token),
        json={"stem": "撤回后修改题干"},
    )
    assert edited.status_code == 200, edited.text

    republished = client.post(
        f"/api/v1/papers/{paper['id']}/publish",
        headers=auth(teacher_token),
    )
    assert republished.status_code == 200, republished.text
    assert republished.json()["data"]["status"] == "published"


def test_blank_mode_create_patch_and_openapi(client, teacher_token, klass):
    _, default_paper = _seed_paper(client, teacher_token, klass["id"])
    assert default_paper["blank_mode"] == "smart"
    _, strict_paper = _seed_paper(client, teacher_token, klass["id"], blank_mode="strict")
    assert strict_paper["blank_mode"] == "strict"

    patched = client.patch(
        f"/api/v1/papers/{default_paper['id']}",
        headers=auth(teacher_token),
        json={"blank_mode": "strict", "title": "改名卷"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["blank_mode"] == "strict"
    assert patched.json()["data"]["title"] == "改名卷"

    published = _publish(client, teacher_token, default_paper["id"])
    assert published["blank_mode"] == "strict"
    rejected = client.patch(
        f"/api/v1/papers/{default_paper['id']}",
        headers=auth(teacher_token),
        json={"blank_mode": "smart"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == 40909

    assert client.patch(f"/api/v1/papers/{default_paper['id']}/withdraw", headers=auth(teacher_token)).status_code == 200
    closed_patch = client.patch(
        f"/api/v1/papers/{default_paper['id']}",
        headers=auth(teacher_token),
        json={"blank_mode": "smart"},
    )
    assert closed_patch.status_code == 200, closed_patch.text
    assert closed_patch.json()["data"]["blank_mode"] == "smart"

    spec = client.get("/openapi.json").json()
    for schema_name in ("PaperCreateRequest", "PaperUpdateRequest"):
        prop = spec["components"]["schemas"][schema_name]["properties"]["blank_mode"]
        enum = prop.get("enum") or prop["anyOf"][0]["enum"]
        assert enum == ["smart", "strict"]


def test_blank_mode_strict_vs_smart_kernel():
    strict_jev = FakeJev()
    strict = grade_blank(
        standard="TCP",
        student="传输控制协议",
        mode="strict",
        jev_client=strict_jev,
    )
    assert strict.correct is False
    assert strict.needs_review is False
    assert strict_jev.calls == 0

    smart_jev = FakeJev()
    smart = grade_blank(
        standard="TCP",
        student="传输控制协议",
        mode="smart",
        jev_client=smart_jev,
    )
    assert smart.correct is True
    assert smart.engine == "jev"
    assert smart_jev.calls > 0


def test_blank_mode_patch_affects_new_attempt_not_old(client, teacher_token, klass, student):
    preview = _json_file(
        client,
        teacher_token,
        klass["id"],
        [{"type": "blank", "stem": "TCP 全称？", "answer": ["TCP"], "knowledge_tag": "网络"}],
    )
    commit = client.post(
        f"/api/v1/classes/{klass['id']}/questions/import/commit",
        headers=auth(teacher_token),
        json={"token": preview.json()["data"]["token"]},
    )
    qid = commit.json()["data"]["question_ids"][0]
    paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "模式切换卷", "mode": "fixed", "question_ids": [qid]},
    ).json()["data"]
    _publish(client, teacher_token, paper["id"])

    first = client.post(f"/api/v1/papers/{paper['id']}/attempts", headers=auth(student["token"])).json()["data"]
    client.put(
        f"/api/v1/attempts/{first['id']}/answers/{qid}",
        headers=auth(student["token"]),
        json={"answer": ["传输控制协议"]},
    )
    old_result = client.post(f"/api/v1/attempts/{first['id']}/submit", headers=auth(student["token"])).json()["data"]
    assert old_result["attempt"]["needs_review"] is True

    assert client.patch(f"/api/v1/papers/{paper['id']}/withdraw", headers=auth(teacher_token)).status_code == 200
    patched = client.patch(
        f"/api/v1/papers/{paper['id']}",
        headers=auth(teacher_token),
        json={"blank_mode": "strict"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["blank_mode"] == "strict"
    assert client.post(f"/api/v1/papers/{paper['id']}/publish", headers=auth(teacher_token)).status_code == 200

    student2 = join_student(client, klass["invite_code"], student_no="M2C2026", name="M2C 学生二")
    second = client.post(f"/api/v1/papers/{paper['id']}/attempts", headers=auth(student2["token"])).json()["data"]
    client.put(
        f"/api/v1/attempts/{second['id']}/answers/{qid}",
        headers=auth(student2["token"]),
        json={"answer": ["传输控制协议"]},
    )
    new_result = client.post(f"/api/v1/attempts/{second['id']}/submit", headers=auth(student2["token"])).json()["data"]
    assert new_result["answers"][0]["engine"] == "deterministic"
    assert new_result["answers"][0]["needs_review"] is False

    old_again = client.get(f"/api/v1/attempts/{first['id']}/result", headers=auth(student["token"]))
    assert old_again.status_code == 200
    assert old_again.json()["data"]["attempt"]["needs_review"] is True


def test_class_papers_list_permissions_and_pagination(client, teacher_token, klass, student):
    _, draft = _seed_paper(client, teacher_token, klass["id"])
    _, published = _seed_paper(client, teacher_token, klass["id"])
    _publish(client, teacher_token, published["id"])

    teacher_list = client.get(
        f"/api/v1/classes/{klass['id']}/papers?page=1&page_size=1",
        headers=auth(teacher_token),
    )
    assert teacher_list.status_code == 200
    assert teacher_list.json()["data"]["total"] == 2
    assert teacher_list.json()["data"]["page_size"] == 1
    assert len(teacher_list.json()["data"]["list"]) == 1
    assert "blank_mode" in teacher_list.json()["data"]["list"][0]
    assert draft["id"] != published["id"]

    student_list = client.get(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(student["token"]),
    )
    assert student_list.status_code == 200
    assert student_list.json()["data"]["total"] == 1
    assert student_list.json()["data"]["list"][0]["status"] == "published"

    teacher_b = register_teacher(client, "m2c-list-b@school.edu.cn")
    class_b = create_class(client, teacher_b["token"], "M2C 列表 B 班")
    student_b = join_student(client, class_b["invite_code"], student_no="M2CB2026")
    assert client.get(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_b["token"]),
    ).json()["code"] == 40302
    assert client.get(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(student_b["token"]),
    ).json()["code"] == 40302

    too_large = client.get(
        f"/api/v1/classes/{klass['id']}/papers?page_size=101",
        headers=auth(teacher_token),
    )
    assert too_large.status_code == 422
    assert too_large.json()["code"] == 40001


def test_paper_attempts_list_permissions(client, teacher_token, klass, student):
    ids, paper = _seed_paper(client, teacher_token, klass["id"])
    _publish(client, teacher_token, paper["id"])
    _submit_all(client, student["token"], paper["id"], ids)

    teacher_list = client.get(
        f"/api/v1/papers/{paper['id']}/attempts?page=1&page_size=20",
        headers=auth(teacher_token),
    )
    assert teacher_list.status_code == 200
    body = teacher_list.json()["data"]
    assert body["total"] == 1
    assert body["list"][0]["student_id"] == student["user"]["id"]
    assert body["list"][0]["student_no"] == student["user"]["student_no"]
    assert "needs_review_count" in body["list"][0]
    assert body["list"][0]["status"] == "submitted"

    assert client.get(
        f"/api/v1/papers/{paper['id']}/attempts",
        headers=auth(student["token"]),
    ).json()["code"] == 40301

    teacher_b = register_teacher(client, "m2c-attempt-b@school.edu.cn")
    create_class(client, teacher_b["token"], "M2C 成绩 B 班")
    assert client.get(
        f"/api/v1/papers/{paper['id']}/attempts",
        headers=auth(teacher_b["token"]),
    ).json()["code"] == 40302


def test_my_attempts_permissions_and_pagination(client, teacher_token, klass, student):
    ids, paper = _seed_paper(client, teacher_token, klass["id"])
    _publish(client, teacher_token, paper["id"])
    attempt_id = _submit_all(client, student["token"], paper["id"], ids)

    mine = client.get("/api/v1/attempts/mine?page=1&page_size=1", headers=auth(student["token"]))
    assert mine.status_code == 200
    body = mine.json()["data"]
    assert body["total"] == 1
    assert body["list"][0]["id"] == attempt_id
    assert body["list"][0]["paper_title"]
    assert body["list"][0]["status"] == "submitted"

    assert client.get("/api/v1/attempts/mine", headers=auth(teacher_token)).json()["code"] == 40301
