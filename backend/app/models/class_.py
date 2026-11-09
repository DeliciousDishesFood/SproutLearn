"""班级表模型（class）。文件名 class_.py 避免 Python 关键字冲突。"""

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint, tinyint


class Class(Base, TimestampMixin):
    __tablename__ = "class"
    __table_args__ = (
        UniqueConstraint("class_code", name="uk_class_code"),
        Index("idx_class_teacher", "teacher_id"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_code = Column(String(8), nullable=False)
    teacher_id = Column(bigint_unsigned(), ForeignKey("teacher.id", ondelete="RESTRICT"), nullable=False)
    class_name = Column(String(80), nullable=False)
    course_name = Column(String(80), nullable=False)
    status = Column(tinyint(), nullable=False, default=1, server_default="1")

    teacher = relationship("Teacher", lazy="joined")
