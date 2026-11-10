"""M2B 题库请求模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

QuestionType = Literal["single", "multiple", "judge", "blank"]
Difficulty = Literal["easy", "medium", "hard"]


class QuestionUpdateRequest(BaseModel):
    type: QuestionType | None = None
    stem: str | None = None
    options: Any | None = None
    answer: Any | None = None
    analysis: str | None = None
    knowledge_tag: str | None = None
    difficulty: Difficulty | None = None

    @field_validator("stem")
    @classmethod
    def _stem(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("题干不能为空")
        return value.strip() if value is not None else None

    @field_validator("knowledge_tag")
    @classmethod
    def _tag(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("知识点标签不能为空")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def _at_least_one(self) -> "QuestionUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("至少提交一个可修改字段")
        return self


class QuestionQuery(BaseModel):
    type: QuestionType | None = None
    tag: str | None = None
    difficulty: Difficulty | None = None
    status: Literal["draft", "published"] | None = None
    keyword: str | None = Field(default=None, max_length=100)
