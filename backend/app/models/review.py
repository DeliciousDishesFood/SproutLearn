"""M2B 教师复核留痕模型（review）。"""

from sqlalchemy import Column, DateTime, Numeric, String, text

from app.models.base import Base, bigint_unsigned, pk_bigint


class Review(Base):
    __tablename__ = "review"

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    attempt_id = Column(bigint_unsigned(), nullable=False)
    answer_record_id = Column(bigint_unsigned(), nullable=False)
    teacher_id = Column(bigint_unsigned(), nullable=False)
    old_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    new_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
