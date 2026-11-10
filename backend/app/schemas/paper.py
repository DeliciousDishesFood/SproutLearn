"""M2B 组卷请求模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Mode = Literal["fixed", "random"]
Difficulty = Literal["easy", "medium", "hard"]


class PaperCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    mode: Mode
    question_ids: list[int] | None = None
    knowledge_tag: str | None = None
    difficulty: Difficulty | None = None
    count: int | None = Field(default=None, ge=1, le=500)
    duration_minutes: int = Field(default=0, ge=0)
    shuffle: bool = False

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
