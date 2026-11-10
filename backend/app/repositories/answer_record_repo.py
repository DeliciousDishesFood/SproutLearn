"""逐题作答数据访问：upsert 的查询入口。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.answer_record import AnswerRecord
from app.repositories.base import BaseRepository


class AnswerRecordRepository(BaseRepository[AnswerRecord]):
    model = AnswerRecord

    def __init__(self, db: Session) -> None:
        super().__init__(db)

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
