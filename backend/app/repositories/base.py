"""仓储基类：统一 class_id 作用域入口，禁止业务层裸查跨班数据。"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, object_id: int) -> ModelT | None:
        return self.db.get(self.model, object_id)

    def add(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        return instance

    def flush(self) -> None:
        self.db.flush()


class ScopedRepository(BaseRepository[ModelT]):
    """带 class_id 的仓储基类：scoped() 是唯一允许的列表查询入口。"""

    def scoped(self, class_id: int):
        if not hasattr(self.model, "class_id"):
            raise TypeError(f"{self.model.__name__} 不支持 class_id 作用域")
        return self.db.query(self.model).filter(self.model.class_id == class_id)
