"""教师复核留痕数据访问。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.review import Review
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    model = Review

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_attempt(self, attempt_id: int) -> list[Review]:
        return (
            self.db.query(Review)
            .filter(Review.attempt_id == attempt_id)
            .order_by(Review.id.asc())
            .all()
        )
