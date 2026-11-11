"""题库数据访问：所有列表/随机抽取必须带 class_id，软删除默认排除。"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_question import PaperQuestion
from app.models.question import Question
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    model = Question

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, question_id: int) -> Question | None:
        return self.db.get(Question, question_id)

    def get_scoped(self, question_id: int, class_id: int) -> Question | None:
        return (
            self.db.query(Question)
            .filter(
                Question.id == question_id,
                Question.class_id == class_id,
                Question.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def list_scoped(
        self,
        class_id: int,
        *,
        type_: str | None,
        tag: str | None,
        difficulty: str | None,
        status: str | None,
        keyword: str | None,
        offset: int,
        limit: int,
    ) -> list[Question]:
        query = self.db.query(Question).filter(
            Question.class_id == class_id, Question.deleted_at.is_(None)
        )
        if type_:
            query = query.filter(Question.type == type_)
        if tag:
            query = query.filter(Question.knowledge_tag == tag)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        if status:
            query = query.filter(Question.status == status)
        if keyword:
            like = f"%{keyword.strip()}%"
            query = query.filter(or_(Question.stem.like(like), Question.analysis.like(like)))
        return query.order_by(Question.id.desc()).offset(offset).limit(limit).all()

    def count_scoped(
        self,
        class_id: int,
        *,
        type_: str | None,
        tag: str | None,
        difficulty: str | None,
        status: str | None,
        keyword: str | None,
    ) -> int:
        query = self.db.query(Question).filter(
            Question.class_id == class_id, Question.deleted_at.is_(None)
        )
        if type_:
            query = query.filter(Question.type == type_)
        if tag:
            query = query.filter(Question.knowledge_tag == tag)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        if status:
            query = query.filter(Question.status == status)
        if keyword:
            like = f"%{keyword.strip()}%"
            query = query.filter(or_(Question.stem.like(like), Question.analysis.like(like)))
        return query.count()

    def get_many(self, class_id: int, question_ids: list[int]) -> list[Question]:
        if not question_ids:
            return []
        return (
            self.db.query(Question)
            .filter(
                Question.class_id == class_id,
                Question.id.in_(question_ids),
                Question.deleted_at.is_(None),
            )
            .all()
        )

    def random_candidates(
        self,
        class_id: int,
        *,
        tag: str | None,
        difficulty: str | None,
    ) -> list[Question]:
        query = self.db.query(Question).filter(
            Question.class_id == class_id, Question.deleted_at.is_(None)
        )
        if tag:
            query = query.filter(Question.knowledge_tag == tag)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        return query.order_by(Question.id.asc()).all()

    def published_reference(self, question_id: int, *, include_closed: bool = True) -> bool:
        statuses = ("published", "closed") if include_closed else ("published",)
        return (
            self.db.query(PaperQuestion.id)
            .join(Paper, Paper.id == PaperQuestion.paper_id)
            .filter(
                PaperQuestion.question_id == question_id,
                Paper.status.in_(statuses),
            )
            .first()
            is not None
        )

    def any_reference(self, question_id: int) -> bool:
        return (
            self.db.query(PaperQuestion.id)
            .filter(PaperQuestion.question_id == question_id)
            .first()
            is not None
        )
