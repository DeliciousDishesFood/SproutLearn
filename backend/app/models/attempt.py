"""M2B 学生作答模型（attempt）。"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, text

from app.models.base import Base, bigint_unsigned, pk_bigint


class Attempt(Base):
    __tablename__ = "attempt"
    __table_args__ = (
        UniqueConstraint("paper_id", "student_id", name="uk_attempt_paper_student"),
        Index("idx_attempt_class_student", "class_id", "student_id"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    paper_id = Column(
        bigint_unsigned(), ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
    )
    class_id = Column(bigint_unsigned(), nullable=False)
    student_id = Column(bigint_unsigned(), nullable=False)
    started_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    deadline_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False, default="doing", server_default="doing")
    total_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    full_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
