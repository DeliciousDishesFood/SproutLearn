"""班级数据访问：列表/详情/行锁全部以 class_id 或 teacher_id 为入口。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository[Class]):
    model = Class

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, class_id: int) -> Class | None:
        return self.db.get(Class, class_id)

    def get_by_code(self, class_code: str) -> Class | None:
        return self.db.query(Class).filter(Class.class_code == class_code).one_or_none()

    def lock_by_id(self, class_id: int) -> Class | None:
        """邀请码重置互斥：SELECT ... FOR UPDATE（SQLite 下自动忽略）。"""
        return (
            self.db.query(Class)
            .filter(Class.id == class_id)
            .with_for_update()
            .one_or_none()
        )

    def list_by_teacher(
        self, teacher_id: int, *, status: int | None, offset: int, limit: int
    ) -> list[Class]:
        query = self.db.query(Class).filter(Class.teacher_id == teacher_id)
        if status is not None:
            query = query.filter(Class.status == status)
        return query.order_by(Class.id.desc()).offset(offset).limit(limit).all()

    def count_by_teacher(self, teacher_id: int, *, status: int | None = None) -> int:
        query = self.db.query(Class).filter(Class.teacher_id == teacher_id)
        if status is not None:
            query = query.filter(Class.status == status)
        return query.count()
