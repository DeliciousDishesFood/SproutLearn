"""QQ 绑定表模型（qq_binding）：两个生成列实现条件唯一。

MySQL 8.0 限制：STORED 生成列不能引用被外键约束的列（ERROR 1215），
因此运行时模型使用 VIRTUAL；唯一索引与 status=0 时 NULL 的语义不变。
"""

from sqlalchemy import (
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)

from app.models.base import Base, TimestampMixin, bigint_unsigned, pk_bigint, tinyint


class QqBinding(Base, TimestampMixin):
    __tablename__ = "qq_binding"
    __table_args__ = (
        UniqueConstraint("active_student_id", name="uk_binding_student_active"),
        UniqueConstraint("active_qq_openid", name="uk_binding_openid_active"),
        Index("idx_binding_status", "status"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    student_id = Column(
        bigint_unsigned(), ForeignKey("student.id", ondelete="CASCADE"), nullable=False
    )
    qq_openid = Column(String(64), nullable=False)
    # status=0 时生成列自动为 NULL，不占用唯一索引位；历史行可保留
    active_student_id = Column(
        bigint_unsigned(),
        Computed("CASE WHEN status = 1 THEN student_id ELSE NULL END", persisted=False),
        nullable=True,
    )
    active_qq_openid = Column(
        String(64),
        Computed("CASE WHEN status = 1 THEN qq_openid ELSE NULL END", persisted=False),
        nullable=True,
    )
    status = Column(tinyint(), nullable=False, default=1, server_default="1")
    bound_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
