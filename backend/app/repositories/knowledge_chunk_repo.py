"""文档切片数据访问：按 doc_id + class_id 双条件读取。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.repositories.base import ScopedRepository


class KnowledgeChunkRepository(ScopedRepository[KnowledgeChunk]):
    model = KnowledgeChunk

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def bulk_create(self, chunks: list[KnowledgeChunk]) -> None:
        if chunks:
            self.db.add_all(chunks)

    def list_by_doc(
        self, doc_id: int, class_id: int, *, offset: int, limit: int
    ) -> list[KnowledgeChunk]:
        return (
            self.scoped(class_id)
            .filter(KnowledgeChunk.doc_id == doc_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_by_doc(self, doc_id: int, class_id: int) -> int:
        return (
            self.scoped(class_id)
            .filter(KnowledgeChunk.doc_id == doc_id)
            .count()
        )

    def delete_by_doc(self, doc_id: int, class_id: int) -> int:
        return (
            self.scoped(class_id)
            .filter(KnowledgeChunk.doc_id == doc_id)
            .delete(synchronize_session=False)
        )
