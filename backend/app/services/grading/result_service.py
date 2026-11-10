"""判分结果落库服务：结构化 JSON 可回放，落库前递归剔除敏感键。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.grading_result import GradingResult
from app.repositories.grading_result_repo import GradingResultRepository

_FORBIDDEN_KEY_PARTS = (
    "api_key",
    "apikey",
    "appkey",
    "authorization",
    "secret",
    "password",
    "access_token",
    "refresh_token",
)


def sanitize_detail(value: Any) -> Any:
    """递归剔除可能携带密钥的字段；不改变正常判分字段。"""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                continue
            cleaned[str(key)] = sanitize_detail(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_detail(item) for item in value]
    return value


def save_grading_result(
    db: Session,
    *,
    class_id: int,
    student_id: int,
    question_ref: str,
    result: dict[str, Any],
) -> GradingResult:
    """把 Grader 的统一输出写入 grading_result。"""
    entity = GradingResult(
        class_id=class_id,
        student_id=student_id,
        question_ref=question_ref,
        engine=str(result.get("engine") or "deterministic"),
        score=float(result.get("score") or 0.0),
        full_score=float(result.get("full_score") or 0.0),
        correct=1 if result.get("correct") else 0,
        confidence=float(result.get("confidence") or 0.0),
        needs_review=1 if result.get("needs_review") else 0,
        detail_json=sanitize_detail(result),
    )
    db.add(entity)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(entity)
    return entity


def get_grading_result(db: Session, result_id: int, class_id: int) -> GradingResult | None:
    return GradingResultRepository(db).get_scoped(result_id, class_id)


def list_student_results(
    db: Session, class_id: int, student_id: int, *, page: int = 1, page_size: int = 20
) -> list[GradingResult]:
    return GradingResultRepository(db).list_by_student(
        class_id, student_id, offset=(page - 1) * page_size, limit=page_size
    )
