"""M3.2 工作台、成长与金句：登录/提交/练习/连击/封顶/等级。"""

from __future__ import annotations

import json
from datetime import date

from app.models.difficulty_factor import DifficultyFactor
from app.models.level_def import LevelDef
from app.models.login_streak_rule import LoginStreakRule
from app.models.student import Student
from app.models.student_daily_xp import StudentDailyXp
from app.models.xp_config import XpConfig
from app.models.xp_limit_config import XpLimitConfig
from app.services import growth_service, quote_service
from tests.conftest import PASSWORD, auth, create_class, register_teacher


def _seed_growth(client):
    with client.testing_session() as db:  # type: ignore[attr-defined]
        db.add_all(
            [
                XpConfig(code="daily_login", name="每日首次登录", base_xp=10, enabled=1),
                XpConfig(code="homework", name="完成作业", base_xp=20, enabled=1),
                XpConfig(code="exam", name="参加考试", base_xp=50, enabled=1),
                XpConfig(code="practice", name="刷题", base_xp=1, enabled=1),
                XpConfig(code="streak", name="连击", base_xp=5, enabled=1),
                DifficultyFactor(code="easy", name="简单", factor=1),
                DifficultyFactor(code="medium", name="中等", factor=2),
                DifficultyFactor(code="hard", name="困难", factor=3),
                DifficultyFactor(code="unknown", name="未分类", factor=2),
                LoginStreakRule(streak_day=1, xp=10),
                LoginStreakRule(streak_day=2, xp=15),
                LoginStreakRule(streak_day=3, xp=20),
                LoginStreakRule(streak_day=4, xp=25),
                LoginStreakRule(streak_day=5, xp=30),
                XpLimitConfig(code="practice_daily_cap", value=200, unit="xp/day"),
                XpLimitConfig(code="streak_daily_cap", value=30, unit="xp/day"),
                LevelDef(level=1, title="见习学者", min_xp=0),
                LevelDef(level=2, title="求知者", min_xp=100),
                LevelDef(level=3, title="探索者", min_xp=250),
                LevelDef(level=4, title="精进者", min_xp=450),
            ]
        )
        db.commit()


def _import_questions(client, token, class_id, questions):
    preview = client.post(
        f"/api/v1/classes/{class_id}/questions/import/preview",
        headers=auth(token),
        files={
            "file": (
                "q.json",
                json.dumps(questions, ensure_ascii=False).encode(),
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


def _judge_questions(count, *, difficulty="medium"):
    return [
        {
            "type": "judge",
            "stem": f"M3.2 题 {i}",
            "answer": True,
            "difficulty": difficulty,
        }
        for i in range(1, count + 1)
    ]


def _paper(client, token, class_id, ids, *, kind="practice", title="M3.2 卷"):
    response = client.post(
        f"/api/v1/classes/{class_id}/papers",
        headers=auth(token),
        json={
            "title": title,
            "mode": "fixed",
            "kind": kind,
            "question_ids": ids,
        },
    )
    assert response.status_code == 200, response.text
    paper = response.json()["data"]
    published = client.post(
        f"/api/v1/papers/{paper['id']}/publish", headers=auth(token)
    )
    assert published.status_code == 200, published.text
    return paper


def _submit(client, student_token, ids, answers):
    paper_id = answers.pop("__paper_id", None)
    attempt = client.post(
        f"/api/v1/papers/{paper_id}/attempts", headers=auth(student_token)
    )
    assert attempt.status_code == 200, attempt.text
    attempt_id = attempt.json()["data"]["id"]
    for question_id, answer in answers.items():
        saved = client.put(
            f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
            headers=auth(student_token),
            json={"answer": answer},
        )
        assert saved.status_code == 200, saved.text
    submitted = client.post(
        f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student_token)
    )
    assert submitted.status_code == 200, submitted.text
    return attempt_id, submitted.json()["data"]


def _xp(client, student_token):
    growth = client.get("/api/v1/me/growth", headers=auth(student_token))
    assert growth.status_code == 200, growth.text
    return growth.json()["data"]["xp_total"]


def test_login_award_and_same_day_idempotent(client, teacher_token, klass, student):
    _seed_growth(client)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "role": "student",
            "class_code": klass["class_code"],
            "student_no": student["user"]["student_no"],
            "password": PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["token"]
    assert _xp(client, token) == 10

    again = client.post(
        "/api/v1/auth/login",
        json={
            "role": "student",
            "class_code": klass["class_code"],
            "student_no": student["user"]["student_no"],
            "password": PASSWORD,
        },
    )
    assert again.status_code == 200
    assert _xp(client, token) == 10


def test_login_streak_rule_next_day_and_reset(client, teacher_token, klass, student):
    _seed_growth(client)
    student_id = student["user"]["id"]
    with client.testing_session() as db:  # type: ignore[attr-defined]
        row = db.get(Student, student_id)
        row.last_login_date = date(2026, 1, 1)
        row.streak_days = 1
        db.commit()

    # 直接 patch 今天的日期，覆盖“次日/断签”分支。
    original = growth_service.today_date
    try:
        growth_service.today_date = lambda: date(2026, 1, 2)
        with client.testing_session() as db:
            awarded = growth_service.apply_login(db, student_id)
            db.commit()
        assert awarded == 15
        with client.testing_session() as db:
            row = db.get(Student, student_id)
            assert row.streak_days == 2
            daily = db.query(StudentDailyXp).filter(StudentDailyXp.stat_date == date(2026, 1, 2)).one()
            assert daily.login_xp == 15

        growth_service.today_date = lambda: date(2026, 1, 2)
        with client.testing_session() as db:
            assert growth_service.apply_login(db, student_id) == 0

        growth_service.today_date = lambda: date(2026, 1, 8)
        with client.testing_session() as db:
            assert growth_service.apply_login(db, student_id) == 10
            db.commit()
        with client.testing_session() as db:
            row = db.get(Student, student_id)
            assert row.streak_days == 1
    finally:
        growth_service.today_date = original


def test_exam_and_homework_submission_xp_idempotent(client, teacher_token, klass, student):
    _seed_growth(client)
    ids = _import_questions(client, teacher_token, klass["id"], _judge_questions(1))
    exam = _paper(client, teacher_token, klass["id"], ids, kind="exam", title="考试")
    attempt_id, _ = _submit(
        client,
        student["token"],
        ids,
        {"__paper_id": exam["id"], ids[0]: True},
    )
    assert _xp(client, student["token"]) == 50
    repeat = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=auth(student["token"]))
    assert repeat.status_code == 200
    assert _xp(client, student["token"]) == 50

    homework = _paper(client, teacher_token, klass["id"], ids, kind="homework", title="作业")
    _submit(
        client,
        student["token"],
        ids,
        {"__paper_id": homework["id"], ids[0]: True},
    )
    assert _xp(client, student["token"]) == 70


def test_practice_difficulty_cap_and_ledger(client, teacher_token, klass, student):
    _seed_growth(client)
    ids = _import_questions(client, teacher_token, klass["id"], _judge_questions(10))
    paper = _paper(client, teacher_token, klass["id"], ids, kind="practice", title="练习")
    answers = {"__paper_id": paper["id"]}
    for index, question_id in enumerate(ids):
        answers[question_id] = index < 8
    _submit(client, student["token"], ids, answers)
    with client.testing_session() as db:  # type: ignore[attr-defined]
        student_id = student["user"]["id"]
        daily = db.query(StudentDailyXp).filter(StudentDailyXp.student_id == student_id).one()
        assert daily.practice_xp == 16
        assert daily.streak_xp == 5
        assert daily.total_xp == 21

    # 日封顶：已有 195 练习经验，再答对 5 道 medium 只再加 5
    with client.testing_session() as db:
        daily = db.query(StudentDailyXp).filter(StudentDailyXp.student_id == student["user"]["id"]).one()
        daily.practice_xp = 195
        daily.total_xp = max(daily.total_xp, 195)
        db.commit()
    paper2 = _paper(client, teacher_token, klass["id"], ids[:5], kind="practice", title="封顶")
    answers2 = {"__paper_id": paper2["id"]}
    for question_id in ids[:5]:
        answers2[question_id] = True
    _submit(client, student["token"], ids[:5], answers2)
    with client.testing_session() as db:  # type: ignore[attr-defined]
        daily = db.query(StudentDailyXp).filter(StudentDailyXp.student_id == student["user"]["id"]).one()
        assert daily.practice_xp == 200
        assert daily.streak_xp <= 30


def test_streak_ten_and_level_thresholds(client, teacher_token, klass, student):
    _seed_growth(client)
    ids = _import_questions(client, teacher_token, klass["id"], _judge_questions(10))
    paper = _paper(client, teacher_token, klass["id"], ids, kind="practice", title="连击")
    answers = {"__paper_id": paper["id"]}
    for question_id in ids:
        answers[question_id] = True
    _submit(client, student["token"], ids, answers)
    with client.testing_session() as db:  # type: ignore[attr-defined]
        daily = db.query(StudentDailyXp).filter(StudentDailyXp.student_id == student["user"]["id"]).one()
        assert daily.practice_xp == 20
        assert daily.streak_xp == 10

    with client.testing_session() as db:  # type: ignore[attr-defined]
        assert growth_service.level_info(db, 100)["title"] == "求知者"
        assert growth_service.level_info(db, 249)["level"] == 2
        assert growth_service.level_info(db, 250)["level"] == 3
        assert growth_service.level_info(db, 299)["level"] == 3


def test_student_and_teacher_workbench_and_cross_class(client, teacher_token, klass, student):
    _seed_growth(client)
    ids = _import_questions(client, teacher_token, klass["id"], _judge_questions(1))
    paper = _paper(client, teacher_token, klass["id"], ids, kind="practice", title="工作台卷")
    pending = client.get("/api/v1/me/workbench", headers=auth(student["token"]))
    assert pending.status_code == 200, pending.text
    assert any(item["id"] == paper["id"] for item in pending.json()["data"]["pending"])

    _submit(client, student["token"], ids, {"__paper_id": paper["id"], ids[0]: True})
    me = client.get("/api/v1/me/workbench", headers=auth(student["token"]))
    assert me.status_code == 200
    assert me.json()["data"]["today_xp"] >= 2
    assert any(item["paper_id"] == paper["id"] for item in me.json()["data"]["recent"])

    teacher = client.get(f"/api/v1/classes/{klass['id']}/workbench", headers=auth(teacher_token))
    assert teacher.status_code == 200, teacher.text
    assert teacher.json()["data"]["today_submissions"] >= 1
    assert "top_students" in teacher.json()["data"]

    teacher_b = register_teacher(client, "m32-b@school.edu.cn")
    create_class(client, teacher_b["token"], "M3.2 B 班")
    cross = client.get(f"/api/v1/classes/{klass['id']}/workbench", headers=auth(teacher_b["token"]))
    assert cross.status_code == 403 and cross.json()["code"] == 40302


def test_activity_growth_and_xp_config(client, teacher_token, klass, student):
    _seed_growth(client)
    ids = _import_questions(client, teacher_token, klass["id"], _judge_questions(1))
    paper = _paper(client, teacher_token, klass["id"], ids, kind="practice", title="活动卷")
    _submit(client, student["token"], ids, {"__paper_id": paper["id"], ids[0]: True})

    activity = client.get("/api/v1/me/activity?weeks=12", headers=auth(student["token"]))
    assert activity.status_code == 200
    assert len(activity.json()["data"]["items"]) == 84
    class_activity = client.get(
        f"/api/v1/classes/{klass['id']}/activity?weeks=4",
        headers=auth(teacher_token),
    )
    assert class_activity.status_code == 200
    assert len(class_activity.json()["data"]["items"]) == 28

    config = client.get(
        f"/api/v1/classes/{klass['id']}/xp-config", headers=auth(teacher_token)
    )
    assert config.status_code == 200
    assert any(item["code"] == "practice" for item in config.json()["data"]["items"])
    patched = client.patch(
        f"/api/v1/classes/{klass['id']}/xp-config",
        headers=auth(teacher_token),
        json={"items": [{"code": "practice", "enabled": False}]},
    )
    assert patched.status_code == 200, patched.text
    practice = next(item for item in patched.json()["data"]["items"] if item["code"] == "practice")
    assert practice["enabled"] is False


def test_paper_kind_create_patch_detail(client, teacher_token, klass):
    ids = _import_questions(
        client, teacher_token, klass["id"], _judge_questions(1)
    )
    paper = client.post(
        f"/api/v1/classes/{klass['id']}/papers",
        headers=auth(teacher_token),
        json={"title": "用途卷", "mode": "fixed", "kind": "exam", "question_ids": ids},
    )
    assert paper.status_code == 200, paper.text
    assert paper.json()["data"]["kind"] == "exam"
    paper_id = paper.json()["data"]["id"]
    detail = client.get(f"/api/v1/papers/{paper_id}", headers=auth(teacher_token))
    assert detail.json()["data"]["kind"] == "exam"
    patched = client.patch(
        f"/api/v1/papers/{paper_id}",
        headers=auth(teacher_token),
        json={"kind": "homework"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["kind"] == "homework"
    assert client.post(f"/api/v1/papers/{paper_id}/publish", headers=auth(teacher_token)).status_code == 200
    rejected = client.patch(
        f"/api/v1/papers/{paper_id}",
        headers=auth(teacher_token),
        json={"kind": "exam"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == 40909


def test_quote_three_level_fallback(monkeypatch, client):
    monkeypatch.setattr(quote_service, "_from_shiora", lambda quote_type: None)
    monkeypatch.setattr(quote_service, "_from_hitokoto", lambda quote_type: None)
    response = client.get("/api/v1/quotes/random")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["text"] and data["from"] and data["source"] == "local"


def test_quote_primary_source(monkeypatch, client):
    monkeypatch.setattr(
        quote_service,
        "_from_shiora",
        lambda quote_type: {"text": "主源句子", "from": "shiora", "source": "shiora"},
    )
    monkeypatch.setattr(quote_service, "_from_hitokoto", lambda quote_type: None)
    response = client.get("/api/v1/quotes/random?type=test-primary")
    assert response.status_code == 200
    assert response.json()["data"]["source"] == "shiora"


def test_quote_secondary_source(monkeypatch, client):
    monkeypatch.setattr(quote_service, "_from_shiora", lambda quote_type: None)
    monkeypatch.setattr(
        quote_service,
        "_from_hitokoto",
        lambda quote_type: {"text": "次源句子", "from": "hitokoto", "source": "hitokoto"},
    )
    response = client.get("/api/v1/quotes/random?type=test-secondary")
    assert response.status_code == 200
    assert response.json()["data"]["source"] == "hitokoto"
