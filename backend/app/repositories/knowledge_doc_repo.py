"""课程文档数据访问：同班 hash 去重、分页列表、删除。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge_doc import KnowledgeDoc
from app.repositories.base import ScopedRepository


class KnowledgeDocRepository(ScopedRepository[KnowledgeDoc]):
    model = KnowledgeDoc

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def exists_hash(self, class_id: int, file_hash: str) -> bool:
        return (
            self.scoped(class_id)
            .filter(KnowledgeDoc.file_hash == file_hash)
            .count()
            > 0
        )

    def get_by_id(self, doc_id: int) -> KnowledgeDoc | None:
        """仅用于 404 存在性判定；业务读取必须走 get_scoped。"""
        return self.db.get(KnowledgeDoc, doc_id)

    def get_scoped(self, doc_id: int, class_id: int) -> KnowledgeDoc | None:
        return self.scoped(class_id).filter(KnowledgeDoc.id == doc_id).one_or_none()

    def list_by_class(
        self,
        class_id: int,
        *,
        status: int | None,
        offset: int,
        limit: int,
    ) -> list[KnowledgeDoc]:
        query = self.scoped(class_id)
        if status is not None:
            query = query.filter(KnowledgeDoc.status == status)
        return query.order_by(KnowledgeDoc.id.desc()).offset(offset).limit(limit).all()

    def count_by_class(self, class_id: int, *, status: int | None = None) -> int:
        query = self.scoped(class_id)
        if status is not None:
            query = query.filter(KnowledgeDoc.status == status)
        return query.count()

    def count_chunks(self, class_id: int) -> int:
        """教师工作台统计用（文档切片总数）。"""
        from sqlalchemy import func


        return (
            self.db.query(func.coalesce(func.sum(KnowledgeDoc.chunk_count), 0))
            .filter(KnowledgeDoc.class_id == class_id)
            .scalar()
            or 0
        )
