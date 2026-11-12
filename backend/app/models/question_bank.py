"""M3.1 题库分类模型（question_bank）。"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint


class QuestionBank(Base, TimestampMixin):
    __tablename__ = "question_bank"
    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uk_bank_class_name"),
        Index("idx_bank_class_deleted", "class_id", "deleted_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(60), nullable=False)
    description = Column(String(200), nullable=True)
    created_by = Column(bigint_unsigned(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
