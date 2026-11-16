"""M2B 作答/复核请求模型。"""

from __future__ import annotations

from typing import Any, Literal

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


class AskHistoryItem(BaseModel):
    """练习页问答历史单条；role 仅限 user/assistant。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def _content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("对话内容不能为空")
        return value


class AskSproutRequest(BaseModel):
    """POST /attempts/{id}/ask 请求体（问问小芽）。"""

    question_id: int = Field(ge=1)
    selected_text: str = Field(default="", max_length=500)
    message: str = Field(default="", max_length=500)
    history: list[AskHistoryItem] = Field(default_factory=list)

    @field_validator("selected_text", "message")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()


class AskSproutSource(BaseModel):
    """引用来源：仅回 doc_id 与 doc_name，不暴露切片正文。"""

    doc_id: int
    doc_name: str


class AskSproutResponse(BaseModel):
    answer: str
    sources: list[AskSproutSource]
