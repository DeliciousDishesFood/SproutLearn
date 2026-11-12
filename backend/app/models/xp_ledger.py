"""M3.2 经验流水（xp_ledger）。"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text

from app.models.base import Base, bigint_unsigned, pk_bigint


class XpLedger(Base):
    __tablename__ = "xp_ledger"
    __table_args__ = (
        UniqueConstraint("student_id", "source", "ref_id", name="uk_ledger_student_source_ref"),
        Index("idx_ledger_student_created", "student_id", "created_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    student_id = Column(
        bigint_unsigned(), ForeignKey("student.id", ondelete="CASCADE"), nullable=False
    )
    source = Column(String(16), nullable=False)
    ref_type = Column(String(16), nullable=False)
    ref_id = Column(bigint_unsigned(), nullable=False)
    xp = Column(Integer, nullable=False, default=0, server_default="0")
    note = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
