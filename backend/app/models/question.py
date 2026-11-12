"""M2B 题库题目模型（question）。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint


class Question(Base, TimestampMixin):
    __tablename__ = "question"
    __table_args__ = (
        Index("idx_question_class_status_deleted", "class_id", "status", "deleted_at"),
        Index("idx_question_class_tag", "class_id", "knowledge_tag"),
        Index("idx_question_bank_status_deleted", "bank_id", "status", "deleted_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(bigint_unsigned(), nullable=False)
    bank_id = Column(
        bigint_unsigned(),
        ForeignKey("question_bank.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type = Column(String(16), nullable=False)
    stem = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=True)
    answer_json = Column(JSON, nullable=False)
    analysis = Column(Text, nullable=True)
    knowledge_tag = Column(String(50), nullable=False, default="未分类", server_default="未分类")
    difficulty = Column(String(16), nullable=False, default="medium", server_default="medium")
    status = Column(String(16), nullable=False, default="draft", server_default="draft")
    created_by = Column(bigint_unsigned(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
