"""教师表模型（teacher）。"""

from sqlalchemy import Column, DateTime, Index, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin, pk_bigint, tinyint


class Teacher(Base, TimestampMixin):
    __tablename__ = "teacher"
    __table_args__ = (
        UniqueConstraint("account", name="uk_teacher_account"),
        Index("idx_teacher_email", "email"),
        Index("idx_teacher_phone", "phone"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    account = Column(String(64), nullable=False)
    password_hash = Column(String(100), nullable=False)
    name = Column(String(50), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(20), nullable=True)
    status = Column(tinyint(), nullable=False, default=1, server_default="1")
    auth_version = Column(Integer, nullable=False, default=1, server_default="1")
    must_change_password = Column(tinyint(), nullable=False, default=0, server_default="0")
    last_login_at = Column(DateTime, nullable=True)
