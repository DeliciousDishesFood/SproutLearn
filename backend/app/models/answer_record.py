"""M2B 逐题作答与判分结果模型（answer_record）。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint, text

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class AnswerRecord(Base):
    __tablename__ = "answer_record"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uk_answer_attempt_question"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    attempt_id = Column(
        bigint_unsigned(), ForeignKey("attempt.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(bigint_unsigned(), nullable=False)
    raw_answer_json = Column(JSON, nullable=True)
    score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    is_correct = Column(tinyint(), nullable=False, default=0, server_default="0")
    engine = Column(String(16), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False, default=0, server_default="0")
    needs_review = Column(tinyint(), nullable=False, default=0, server_default="0")
    detail_json = Column(JSON, nullable=False, default=dict)
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
