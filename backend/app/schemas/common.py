"""通用 Pydantic 模型与分页参数。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import get_settings


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default_factory=lambda: get_settings().pagination_default_size,
        ge=1,
        le=50,
    )

    @model_validator(mode="after")
    def _check_page_size(self) -> "PageQuery":
        if self.page_size > get_settings().pagination_max_size:
            raise ValueError("page_size 超过上限")
        return self


class PageResponse(BaseModel):
    total: int
    page: int
    page_size: int
    list: list[Any]
