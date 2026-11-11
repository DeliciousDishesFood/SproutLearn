"""M2B/M2C 组卷请求模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Mode = Literal["fixed", "random"]
Difficulty = Literal["easy", "medium", "hard"]
BlankMode = Literal["smart", "strict"]


class PaperCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    mode: Mode
    question_ids: list[int] | None = None
    knowledge_tag: str | None = None
    difficulty: Difficulty | None = None
    count: int | None = Field(default=None, ge=1, le=500)
    duration_minutes: int = Field(default=0, ge=0)
    shuffle: bool = False
    blank_mode: BlankMode = "smart"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("试卷标题不能为空")
        return value

    @model_validator(mode="after")
    def _check_mode(self) -> "PaperCreateRequest":
        if self.mode == "fixed":
            if not self.question_ids:
                raise ValueError("固定组卷必须提供 question_ids")
            if len(set(self.question_ids)) != len(self.question_ids):
                raise ValueError("question_ids 不能重复")
        else:
            if not self.count:
                raise ValueError("随机组卷必须提供 count")
        return self


class PaperUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, ge=0)
    blank_mode: BlankMode | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("试卷标题不能为空")
        return value

    @model_validator(mode="after")
    def _at_least_one(self) -> "PaperUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("至少提交一个可修改字段")
        return self
