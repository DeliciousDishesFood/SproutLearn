"""M2B 试卷题目关联模型（paper_question）。"""

from sqlalchemy import Column, ForeignKey, Index, Integer, Numeric, UniqueConstraint

from app.models.base import Base, bigint_unsigned, pk_bigint


class PaperQuestion(Base):
    __tablename__ = "paper_question"
    __table_args__ = (
        UniqueConstraint("paper_id", "seq", name="uk_paper_question_seq"),
        UniqueConstraint("paper_id", "question_id", name="uk_paper_question_question"),
        Index("idx_paper_question_question", "question_id"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    paper_id = Column(
        bigint_unsigned(), ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(bigint_unsigned(), nullable=False)
    seq = Column(Integer, nullable=False)
    score = Column(Numeric(8, 2), nullable=False, default=1, server_default="1")
