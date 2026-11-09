"""邀请码表模型（class_invite）：历史码保留，status=0 表示作废。"""

from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Index, UniqueConstraint

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint, tinyint


class ClassInvite(Base, TimestampMixin):
    __tablename__ = "class_invite"
    __table_args__ = (
        UniqueConstraint("code", name="uk_invite_code"),
        Index("idx_invite_class", "class_id"),
        Index("idx_invite_class_status", "class_id", "status"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    code = Column(CHAR(6), nullable=False)
    status = Column(tinyint(), nullable=False, default=1, server_default="1")
    expires_at = Column(DateTime, nullable=True)
    created_by = Column(
        bigint_unsigned(), ForeignKey("teacher.id", ondelete="RESTRICT"), nullable=False
    )
