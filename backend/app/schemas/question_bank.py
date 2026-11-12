"""M3.1 题库分类请求模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionBankCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("题库名称不能为空")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class QuestionBankUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("题库名称不能为空")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def _at_least_one(self) -> "QuestionBankUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("至少提交一个可修改字段")
        return self
