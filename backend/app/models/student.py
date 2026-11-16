"""学生表模型（student）：班内学号唯一，跨班可重复。"""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin, bigint_unsigned, int_unsigned, pk_bigint, smallint_unsigned, tinyint, tinyint_unsigned


class Student(Base, TimestampMixin):
    __tablename__ = "student"
    __table_args__ = (
        UniqueConstraint("class_id", "student_no", name="uk_class_student_no"),
        Index("idx_student_class", "class_id"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    student_no = Column(String(32), nullable=False)
    name = Column(String(50), nullable=False)
    password_hash = Column(String(100), nullable=False)
    xp_total = Column(int_unsigned(), nullable=False, default=0, server_default="0")
    level = Column(tinyint_unsigned(), nullable=False, default=1, server_default="1")
    status = Column(tinyint(), nullable=False, default=1, server_default="1")
    auth_version = Column(Integer, nullable=False, default=1, server_default="1")
    must_change_password = Column(tinyint(), nullable=False, default=0, server_default="0")
    last_login_at = Column(DateTime, nullable=True)
    streak_days = Column(smallint_unsigned(), nullable=False, default=0, server_default="0")
    last_login_date = Column(Date, nullable=True)
