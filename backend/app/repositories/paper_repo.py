"""试卷数据访问：教师/学生均按 class_id 作用域读取。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_question import PaperQuestion
from app.models.question import Question
from app.repositories.base import BaseRepository


class PaperRepository(BaseRepository[Paper]):
    model = Paper

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, paper_id: int) -> Paper | None:
        return self.db.get(Paper, paper_id)

    def get_scoped(self, paper_id: int, class_id: int) -> Paper | None:
        return (
            self.db.query(Paper)
            .filter(Paper.id == paper_id, Paper.class_id == class_id)
            .one_or_none()
        )

    def lock_by_id(self, paper_id: int) -> Paper | None:
        return (
            self.db.query(Paper)
            .filter(Paper.id == paper_id)
            .with_for_update()
            .one_or_none()
        )

    def questions(self, paper_id: int) -> list[tuple[PaperQuestion, Question]]:
        return (
            self.db.query(PaperQuestion, Question)
            .join(Question, Question.id == PaperQuestion.question_id)
            .filter(PaperQuestion.paper_id == paper_id)
            .order_by(PaperQuestion.seq.asc())
            .all()
        )

    def question_ids(self, paper_id: int) -> list[int]:
        return [
            row[0]
            for row in self.db.query(PaperQuestion.question_id)
            .filter(PaperQuestion.paper_id == paper_id)
            .order_by(PaperQuestion.seq.asc())
            .all()
        ]
