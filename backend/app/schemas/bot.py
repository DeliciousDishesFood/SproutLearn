"""M3.4/M3.5 机器人配置请求模型（Secret 不在请求/响应中出现）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ChatMode = Literal["strict", "balanced", "free"]


class BotConfigUpdateRequest(BaseModel):
    app_id: str = Field(min_length=1, max_length=64)
    callback_url: str | None = Field(default=None, max_length=255)
    enabled: bool = False
    binding_enabled: bool = True
    notify_assignment: bool = True
    notify_due_soon: bool = True
    mention_missing: bool = False
    allow_query_assignments: bool = True
    allow_query_scores: bool = False
    bot_chat_mode: ChatMode = "balanced"
    bot_chat_enabled: bool = True
    bot_chat_max_chars: int = Field(default=1200, ge=100, le=2000)

    @field_validator("app_id")
    @classmethod
    def _app_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("AppID 不能为空")
        return value

    @field_validator("callback_url")
    @classmethod
    def _callback_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None
