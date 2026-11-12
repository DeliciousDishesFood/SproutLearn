"""M3.3 班级 QQ 机器人配置（class_bot_config）。"""

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, text
from sqlalchemy.dialects import mysql

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint, tinyint


class ClassBotConfig(Base, TimestampMixin):
    __tablename__ = "class_bot_config"
    __table_args__ = ()

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(),
        ForeignKey("class.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    app_id = Column(String(64), nullable=False)
    app_secret_cipher = Column(
        LargeBinary(512).with_variant(mysql.VARBINARY(512), "mysql"),
        nullable=False,
    )
    callback_url = Column(String(255), nullable=True)
    enabled = Column(tinyint(), nullable=False, default=0, server_default="0")
    last_check_at = Column(DateTime, nullable=True)
    last_check_status = Column(
        String(16), nullable=False, default="never", server_default="never"
    )
    created_by = Column(bigint_unsigned(), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
