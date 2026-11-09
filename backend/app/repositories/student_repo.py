"""学生数据访问：班内学号大小写不敏感查询、列表 qq_bound 派生。"""

from __future__ import annotations

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.qq_binding import QqBinding
from app.models.student import Student
from app.repositories.base import ScopedRepository


class StudentRepository(ScopedRepository[Student]):
    model = Student

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_class_and_no(self, class_id: int, student_no: str) -> Student | None:
        return (
            self.scoped(class_id)
            .filter(func.lower(Student.student_no) == student_no.strip().lower())
            .one_or_none()
        )

    def list_by_class(
        self, class_id: int, *, keyword: str | None, offset: int, limit: int
    ) -> list[tuple[Student, int | None]]:
        query = (
            self.db.query(Student, QqBinding.id.label("binding_id"))
            .outerjoin(
                QqBinding,
                and_(QqBinding.student_id == Student.id, QqBinding.status == 1),
            )
            .filter(Student.class_id == class_id)
        )
        if keyword:
            like = f"%{keyword.strip()}%"
            query = query.filter(or_(Student.student_no.like(like), Student.name.like(like)))
        rows = query.order_by(Student.student_no.asc()).offset(offset).limit(limit).all()
        return [(row[0], row[1]) for row in rows]

    def count_by_class(self, class_id: int, *, keyword: str | None = None) -> int:
        query = self.scoped(class_id)
        if keyword:
            like = f"%{keyword.strip()}%"
            query = query.filter(or_(Student.student_no.like(like), Student.name.like(like)))
        return query.count()

    def get_by_id_scoped(self, student_id: int, class_id: int) -> Student | None:
        return self.scoped(class_id).filter(Student.id == student_id).one_or_none()
