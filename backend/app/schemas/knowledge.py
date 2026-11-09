"""知识库相关 Pydantic 模型（上传走 multipart，列表走 Query 参数）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentQuery(BaseModel):
    class_id: int = Field(ge=1)
    status: int | None = Field(default=None, ge=0, le=3)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)
