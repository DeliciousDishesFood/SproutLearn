"""M2B 试卷模型（paper）。"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, text

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class Paper(Base):
    __tablename__ = "paper"
    __table_args__ = (
        Index("idx_paper_class_status", "class_id", "status"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(200), nullable=False)
    mode = Column(String(16), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=0, server_default="0")
    shuffle = Column(tinyint(), nullable=False, default=0, server_default="0")
    question_count = Column(Integer, nullable=False, default=0, server_default="0")
    total_score = Column(Numeric(8, 2), nullable=False, default=0, server_default="0")
    status = Column(String(16), nullable=False, default="draft", server_default="draft")
    created_by = Column(bigint_unsigned(), nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
