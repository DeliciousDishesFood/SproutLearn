"""M3.3 机器人配置请求模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class BotConfigUpdateRequest(BaseModel):
    app_id: str = Field(min_length=1, max_length=64)
    app_secret: str | None = Field(default=None, max_length=512)
    callback_url: str | None = Field(default=None, max_length=255)
    enabled: bool = False

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
