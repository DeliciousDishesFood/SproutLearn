"""最小账号/班级操作记录（不含密码、hash、token）。"""

from sqlalchemy import Column, DateTime, Index, String, text

from app.models.base import Base, bigint_unsigned, pk_bigint


class AccountAuditLog(Base):
    __tablename__ = "account_audit_log"
    __table_args__ = (
        Index("idx_audit_actor", "actor_role", "actor_id", "created_at"),
        Index("idx_audit_target", "target_role", "target_id", "created_at"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    actor_role = Column(String(8), nullable=False)
    actor_id = Column(bigint_unsigned(), nullable=False)
    target_role = Column(String(8), nullable=False)
    target_id = Column(bigint_unsigned(), nullable=False)
    class_id = Column(bigint_unsigned(), nullable=True)
    action = Column(String(32), nullable=False)
    result = Column(String(16), nullable=False)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
