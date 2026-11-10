"""P4 判分结果落库：字段、作用域、raw 脱敏。"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.services.grading.grader import Grader
from app.services.grading.result_service import (
    get_grading_result,
    list_student_results,
    save_grading_result,
)


def _db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def test_grading_result_persists_and_sanitizes_raw():
    db = _db()
    result = Grader().grade(
        question_type="single_choice",
        standard="A",
        student="A",
        full_score=2,
        knowledge_tags=["tcp"],
    )
    result["raw"]["api_key"] = "should-not-be-stored"
    result["raw"]["safe_note"] = "ok"
    entity = save_grading_result(
        db,
        class_id=1,
        student_id=10,
        question_ref="m2a-test-q1",
        result=result,
    )
    assert entity.id
    assert entity.engine == "deterministic"
    assert float(entity.score) == 2.0
    assert float(entity.full_score) == 2.0
    assert entity.correct == 1
    assert entity.needs_review == 0
    assert "api_key" not in entity.detail_json["raw"]
    assert entity.detail_json["raw"]["safe_note"] == "ok"

    loaded = get_grading_result(db, entity.id, 1)
    assert loaded is not None and loaded.id == entity.id
    assert get_grading_result(db, entity.id, 2) is None
    assert len(list_student_results(db, 1, 10)) == 1
    db.close()
