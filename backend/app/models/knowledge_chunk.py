"""文档切片表模型（knowledge_chunk）：doc_name 冗余快照，随文档标题写入。"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)

from app.models.base import Base, bigint_unsigned, int_unsigned, medium_text, pk_bigint


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_index", name="uk_chunk_doc_index"),
        Index("idx_chunk_doc", "doc_id"),
        Index("idx_chunk_class", "class_id"),
    )

    id = Column(pk_bigint(), primary_key=True, autoincrement=True)
    doc_id = Column(
        bigint_unsigned(), ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False
    )
    class_id = Column(bigint_unsigned(), nullable=False)
    doc_name = Column(String(200), nullable=False)
    chunk_index = Column(int_unsigned(), nullable=False)
    content = Column(medium_text(), nullable=False)
    char_count = Column(int_unsigned(), nullable=False, default=0, server_default="0")
    chapter_title = Column(String(200), nullable=True)
    page_no = Column(int_unsigned(), nullable=True)
    vector_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
