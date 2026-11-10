"""M2A 判分结果表模型（只新增表，不改 M1 表）。"""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    Numeric,
    String,
    text,
)

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class GradingResult(Base):
    __tablename__ = "grading_result"
    __table_args__ = (
        Index("idx_grading_result_class_student", "class_id", "student_id"),
        Index("idx_grading_result_class_created", "class_id", "created_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(bigint_unsigned(), nullable=False)
    student_id = Column(bigint_unsigned(), nullable=False)
    question_ref = Column(String(128), nullable=False)
    engine = Column(String(16), nullable=False)
    score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    full_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    correct = Column(tinyint(), nullable=False, default=0, server_default="0")
    confidence = Column(Numeric(4, 3), nullable=False, default=0, server_default="0")
    needs_review = Column(tinyint(), nullable=False, default=0, server_default="0")
    detail_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
