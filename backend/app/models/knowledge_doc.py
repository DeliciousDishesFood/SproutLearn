"""课程文档表模型（knowledge_doc）：同班同 sha256 唯一。"""

from sqlalchemy import (
    CHAR,
    Column,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)

from app.models.base import Base, TimestampMixin, bigint_unsigned, int_unsigned, pk_bigint, tinyint


class KnowledgeDoc(Base, TimestampMixin):
    __tablename__ = "knowledge_doc"
    __table_args__ = (
        UniqueConstraint("class_id", "file_hash", name="uk_doc_class_hash"),
        Index("idx_doc_class_status", "class_id", "status"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    class_id = Column(
        bigint_unsigned(), ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    course_name = Column(String(80), nullable=False)
    title = Column(String(200), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_ext = Column(String(10), nullable=False)
    file_size = Column(bigint_unsigned(), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(CHAR(64), nullable=False)
    status = Column(tinyint(), nullable=False, default=0, server_default="0")
    error_code = Column(String(32), nullable=True)
    error_message = Column(String(500), nullable=True)
    page_count = Column(int_unsigned(), nullable=True)
    chunk_count = Column(int_unsigned(), nullable=False, default=0, server_default="0")
    created_by = Column(
        bigint_unsigned(), ForeignKey("teacher.id", ondelete="RESTRICT"), nullable=False
    )
