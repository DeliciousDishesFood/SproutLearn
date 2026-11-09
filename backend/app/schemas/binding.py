"""QQ 绑定相关请求模型。"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

_CODE_RE = re.compile(r"^[1-9]\d{7}$")


class QqBindCallbackRequest(BaseModel):
    code: str
    qq_openid: str

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        code = (value or "").strip()
        if not _CODE_RE.match(code):
            raise ValueError("绑定码必须为 8 位数字且首位非 0")
        return code

    @field_validator("qq_openid")
    @classmethod
    def _openid(cls, value: str) -> str:
        openid = (value or "").strip()
        if not (1 <= len(openid) <= 64):
            raise ValueError("qq_openid 长度必须为 1–64 个字符")
        return openid
