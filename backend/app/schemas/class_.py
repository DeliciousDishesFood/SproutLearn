"""班级相关请求模型。"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.config import get_settings
from app.utils.validators import validate_text_field


class ClassCreateRequest(BaseModel):
    class_name: str
    course_name: str

    @field_validator("class_name")
    @classmethod
    def _class_name(cls, value: str) -> str:
        return validate_text_field(value, "班级名称", get_settings().text_field_max_len)

    @field_validator("course_name")
    @classmethod
    def _course_name(cls, value: str) -> str:
        return validate_text_field(value, "课程名称", get_settings().text_field_max_len)
