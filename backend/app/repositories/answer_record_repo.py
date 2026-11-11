"""逐题作答数据访问：upsert 的查询入口。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.answer_record import AnswerRecord
from app.repositories.base import BaseRepository


class AnswerRecordRepository(BaseRepository[AnswerRecord]):
    model = AnswerRecord

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def needs_review_counts(self, attempt_ids: list[int]) -> dict[int, int]:
        if not attempt_ids:
            return {}
        rows = (
            self.db.query(AnswerRecord.attempt_id, func.count(AnswerRecord.id))
            .filter(
                AnswerRecord.attempt_id.in_(attempt_ids),
                AnswerRecord.needs_review == 1,
            )
            .group_by(AnswerRecord.attempt_id)
            .all()
        )
        return {int(attempt_id): int(count) for attempt_id, count in rows}

    def get_by_attempt_question(self, attempt_id: int, question_id: int) -> AnswerRecord | None:
        return (
            self.db.query(AnswerRecord)
            .filter(
                AnswerRecord.attempt_id == attempt_id,
                AnswerRecord.question_id == question_id,
            )
            .one_or_none()
        )

    def list_by_attempt(self, attempt_id: int) -> list[AnswerRecord]:
        return (
            self.db.query(AnswerRecord)
            .filter(AnswerRecord.attempt_id == attempt_id)
            .order_by(AnswerRecord.question_id.asc())
            .all()
        )
