"""M3.2 工作台请求模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class XpConfigItem(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    enabled: bool


class XpConfigUpdateRequest(BaseModel):
    items: list[XpConfigItem] = Field(default_factory=list)
    code: str | None = Field(default=None, max_length=32)
    enabled: bool | None = None

    @model_validator(mode="after")
    def _normalize(self) -> "XpConfigUpdateRequest":
        if self.code is not None and self.enabled is not None:
            self.items = [XpConfigItem(code=self.code, enabled=self.enabled)]
        if not self.items:
            raise ValueError("至少提交一个经验行为开关")
        return self
