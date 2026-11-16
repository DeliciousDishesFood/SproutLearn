"""机器人通知幂等记录（bot_notice）。"""

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from app.models.base import Base, bigint_unsigned, pk_bigint


class BotNotice(Base):
    __tablename__ = "bot_notice"
    __table_args__ = (
        UniqueConstraint("paper_id", "kind", name="uk_bot_notice_paper_kind"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    paper_id = Column(
        bigint_unsigned(), ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
    )
    kind = Column(String(32), nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    message_id = Column(String(64), nullable=True)
