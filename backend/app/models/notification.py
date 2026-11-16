"""通知中心（notification）。"""

from sqlalchemy import JSON, Column, DateTime, Index, String, text

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index(
            "idx_notification_recipient",
            "recipient_role",
            "recipient_id",
            "is_read",
            "created_at",
        ),
        Index("idx_notification_class_type", "class_id", "type", "created_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    recipient_role = Column(String(8), nullable=False)
    recipient_id = Column(bigint_unsigned(), nullable=False)
    class_id = Column(bigint_unsigned(), nullable=False)
    type = Column(String(32), nullable=False)
    title = Column(String(120), nullable=False)
    body = Column(String(500), nullable=False)
    target_path = Column(String(255), nullable=True)
    payload_json = Column(JSON, nullable=True)
    is_read = Column(tinyint(), nullable=False, default=0, server_default="0")
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
