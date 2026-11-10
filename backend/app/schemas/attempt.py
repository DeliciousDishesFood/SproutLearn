"""M2B 作答/复核请求模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AnswerSaveRequest(BaseModel):
    answer: Any


class ReviewCreateRequest(BaseModel):
    answer_record_id: int = Field(ge=1)
    new_score: float = Field(ge=0)
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment")
    @classmethod
    def _comment(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None
