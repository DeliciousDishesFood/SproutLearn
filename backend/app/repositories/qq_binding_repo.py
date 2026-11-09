"""QQ 绑定数据访问：只读写 status=1 的有效行，历史行保留。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.qq_binding import QqBinding
from app.repositories.base import ScopedRepository


class QqBindingRepository(ScopedRepository[QqBinding]):
    model = QqBinding

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_active_by_student(self, student_id: int) -> QqBinding | None:
        return (
            self.db.query(QqBinding)
            .filter(QqBinding.student_id == student_id, QqBinding.status == 1)
            .order_by(QqBinding.id.desc())
            .first()
        )

    def get_active_by_openid(self, qq_openid: str) -> QqBinding | None:
        return (
            self.db.query(QqBinding)
            .filter(QqBinding.qq_openid == qq_openid, QqBinding.status == 1)
            .one_or_none()
        )

    def deactivate_by_student(self, student_id: int) -> int:
        return (
            self.db.query(QqBinding)
            .filter(QqBinding.student_id == student_id, QqBinding.status == 1)
            .update({QqBinding.status: 0}, synchronize_session=False)
        )
