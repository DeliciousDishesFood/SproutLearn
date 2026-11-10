"""判分结果数据访问：只按 class_id 作用域读取。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.grading_result import GradingResult
from app.repositories.base import BaseRepository


class GradingResultRepository(BaseRepository[GradingResult]):
    model = GradingResult

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_scoped(self, result_id: int, class_id: int) -> GradingResult | None:
        return (
            self.db.query(GradingResult)
            .filter(GradingResult.id == result_id, GradingResult.class_id == class_id)
            .one_or_none()
        )

    def list_by_student(
        self, class_id: int, student_id: int, *, offset: int = 0, limit: int = 20
    ) -> list[GradingResult]:
        return (
            self.db.query(GradingResult)
            .filter(GradingResult.class_id == class_id, GradingResult.student_id == student_id)
            .order_by(GradingResult.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
