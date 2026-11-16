"""班级 QQ 机器人配置（M3.3/M3.4：密钥移入环境变量，新增群与权限开关）。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text

from app.models.base import Base, bigint_unsigned, pk_bigint, tinyint


class ClassBotConfig(Base):
    __tablename__ = "class_bot_config"

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(),
        ForeignKey("class.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    app_id = Column(String(64), nullable=False)
    callback_url = Column(String(255), nullable=True)
    enabled = Column(tinyint(), nullable=False, default=0, server_default="0")
    group_openid = Column(String(64), nullable=True)
    teacher_openid = Column(String(64), nullable=True)
    teacher_bound_at = Column(DateTime, nullable=True)
    binding_enabled = Column(tinyint(), nullable=False, default=1, server_default="1")
    notify_assignment = Column(tinyint(), nullable=False, default=1, server_default="1")
    notify_due_soon = Column(tinyint(), nullable=False, default=1, server_default="1")
    mention_missing = Column(tinyint(), nullable=False, default=0, server_default="0")
    allow_query_assignments = Column(
        tinyint(), nullable=False, default=1, server_default="1"
    )
    allow_query_scores = Column(tinyint(), nullable=False, default=0, server_default="0")
    bot_chat_mode = Column(
        String(16), nullable=False, default="balanced", server_default="balanced"
    )
    bot_chat_enabled = Column(tinyint(), nullable=False, default=1, server_default="1")
    bot_chat_max_chars = Column(Integer, nullable=False, default=600, server_default="600")
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
