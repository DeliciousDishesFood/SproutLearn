"""教师数据访问。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.teacher import Teacher
from app.repositories.base import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    model = Teacher

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_account(self, account: str) -> Teacher | None:
        return self.db.query(Teacher).filter(Teacher.account == account.lower()).one_or_none()
