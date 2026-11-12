"""M3.1 题库分类数据访问。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.question import Question
from app.models.question_bank import QuestionBank
from app.repositories.base import BaseRepository


class QuestionBankRepository(BaseRepository[QuestionBank]):
    model = QuestionBank

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, bank_id: int) -> QuestionBank | None:
        return self.db.get(QuestionBank, bank_id)

    def get_scoped(
        self, bank_id: int, class_id: int, *, include_deleted: bool = False
    ) -> QuestionBank | None:
        query = self.db.query(QuestionBank).filter(
            QuestionBank.id == bank_id, QuestionBank.class_id == class_id
        )
        if not include_deleted:
            query = query.filter(QuestionBank.deleted_at.is_(None))
        return query.one_or_none()

    def list_scoped(
        self, class_id: int, *, include_deleted: bool = False
    ) -> list[QuestionBank]:
        query = self.db.query(QuestionBank).filter(QuestionBank.class_id == class_id)
        if not include_deleted:
            query = query.filter(QuestionBank.deleted_at.is_(None))
        return query.order_by(QuestionBank.id.asc()).all()

    def name_exists(
        self, class_id: int, name: str, *, exclude_id: int | None = None
    ) -> bool:
        query = self.db.query(QuestionBank.id).filter(
            QuestionBank.class_id == class_id, QuestionBank.name == name
        )
        if exclude_id is not None:
            query = query.filter(QuestionBank.id != exclude_id)
        return query.first() is not None

    def count_questions(self, bank_id: int, *, include_deleted: bool = False) -> int:
        query = self.db.query(Question).filter(Question.bank_id == bank_id)
        if not include_deleted:
            query = query.filter(Question.deleted_at.is_(None))
        return query.count()

    def question_counts(self, bank_ids: list[int]) -> dict[int, int]:
        if not bank_ids:
            return {}
        rows = (
            self.db.query(Question.bank_id, func.count(Question.id))
            .filter(
                Question.bank_id.in_(bank_ids),
                Question.deleted_at.is_(None),
            )
            .group_by(Question.bank_id)
            .all()
        )
        return {int(bank_id): int(count) for bank_id, count in rows}

    def get_many_scoped(self, class_id: int, bank_ids: list[int]) -> list[QuestionBank]:
        if not bank_ids:
            return []
        return (
            self.db.query(QuestionBank)
            .filter(
                QuestionBank.class_id == class_id,
                QuestionBank.id.in_(bank_ids),
                QuestionBank.deleted_at.is_(None),
            )
            .all()
        )
