"""M2B/M2C 组卷请求模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Mode = Literal["fixed", "random"]
Difficulty = Literal["easy", "medium", "hard"]
BlankMode = Literal["smart", "strict"]
PaperKind = Literal["practice", "homework", "exam"]


class PaperCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    mode: Mode
    kind: PaperKind = "practice"
    question_ids: list[int] | None = None
    bank_ids: list[int] | None = None
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
            if bool(self.question_ids) and bool(self.bank_ids):
                raise ValueError("fixed 模式 question_ids 与 bank_ids 只能二选一")
            if not self.question_ids and not self.bank_ids:
                raise ValueError("固定组卷必须提供 question_ids 或 bank_ids")
            if self.question_ids and len(set(self.question_ids)) != len(self.question_ids):
                raise ValueError("question_ids 不能重复")
            if self.bank_ids and len(set(self.bank_ids)) != len(self.bank_ids):
                raise ValueError("bank_ids 不能重复")
        else:
            if not self.count:
                raise ValueError("随机组卷必须提供 count")
        return self


class PaperUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, ge=0)
    blank_mode: BlankMode | None = None
    kind: PaperKind | None = None

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
