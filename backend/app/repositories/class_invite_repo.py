"""邀请码数据访问：当前有效码与批量作废。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.class_invite import ClassInvite
from app.repositories.base import ScopedRepository


class ClassInviteRepository(ScopedRepository[ClassInvite]):
    model = ClassInvite

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_active(self, class_id: int) -> ClassInvite | None:
        return (
            self.db.query(ClassInvite)
            .filter(ClassInvite.class_id == class_id, ClassInvite.status == 1)
            .order_by(ClassInvite.id.desc())
            .first()
        )

    def get_by_code(self, code: str) -> ClassInvite | None:
        """加入班级使用：只认 status=1 的码，过期在服务层判断。"""
        return (
            self.db.query(ClassInvite)
            .filter(ClassInvite.code == code, ClassInvite.status == 1)
            .one_or_none()
        )

    def deactivate_all(self, class_id: int) -> int:
        return (
            self.db.query(ClassInvite)
            .filter(ClassInvite.class_id == class_id, ClassInvite.status == 1)
            .update({ClassInvite.status: 0}, synchronize_session=False)
        )
