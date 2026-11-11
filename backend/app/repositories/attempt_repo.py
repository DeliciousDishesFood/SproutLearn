"""作答数据访问：attempt 行锁与 paper/student 唯一约束。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.repositories.base import BaseRepository


class AttemptRepository(BaseRepository[Attempt]):
    model = Attempt

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, attempt_id: int) -> Attempt | None:
        return self.db.get(Attempt, attempt_id)

    def get_by_paper_student(self, paper_id: int, student_id: int) -> Attempt | None:
        return (
            self.db.query(Attempt)
            .filter(Attempt.paper_id == paper_id, Attempt.student_id == student_id)
            .one_or_none()
        )

    def lock_by_id(self, attempt_id: int) -> Attempt | None:
        return (
            self.db.query(Attempt)
            .filter(Attempt.id == attempt_id)
            .with_for_update()
            .one_or_none()
        )

    def list_by_class_paper(self, class_id: int, paper_id: int) -> list[Attempt]:
        return (
            self.db.query(Attempt)
            .filter(Attempt.class_id == class_id, Attempt.paper_id == paper_id)
            .order_by(Attempt.id.asc())
            .all()
        )

    def list_by_paper(
        self, class_id: int, paper_id: int, *, offset: int, limit: int
    ) -> list[Attempt]:
        return (
            self.db.query(Attempt)
            .filter(Attempt.class_id == class_id, Attempt.paper_id == paper_id)
            .order_by(Attempt.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_by_paper(self, class_id: int, paper_id: int) -> int:
        return (
            self.db.query(Attempt)
            .filter(Attempt.class_id == class_id, Attempt.paper_id == paper_id)
            .count()
        )

    def list_mine(
        self, class_id: int, student_id: int, *, offset: int, limit: int
    ) -> list[Attempt]:
        return (
            self.db.query(Attempt)
            .filter(Attempt.class_id == class_id, Attempt.student_id == student_id)
            .order_by(Attempt.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_mine(self, class_id: int, student_id: int) -> int:
        return (
            self.db.query(Attempt)
            .filter(Attempt.class_id == class_id, Attempt.student_id == student_id)
            .count()
        )

    def status_by_paper_ids(
        self, class_id: int, student_id: int, paper_ids: list[int]
    ) -> dict[int, str]:
        if not paper_ids:
            return {}
        rows = (
            self.db.query(Attempt.paper_id, Attempt.status)
            .filter(
                Attempt.class_id == class_id,
                Attempt.student_id == student_id,
                Attempt.paper_id.in_(paper_ids),
            )
            .all()
        )
        return {int(paper_id): status for paper_id, status in rows}
