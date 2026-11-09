"""鉴权相关请求模型：字段校验规则严格对齐契约 §7.3。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from app.utils.validators import (
    validate_account,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
    validate_student_no,
)


class TeacherRegisterRequest(BaseModel):
    account: str
    name: str
    password: str
    email: str | None = None
    phone: str | None = None

    @field_validator("account")
    @classmethod
    def _account(cls, value: str) -> str:
        return validate_account(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return validate_email(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return validate_phone(value)


class LoginRequest(BaseModel):
    role: Literal["teacher", "student"]
    account: str | None = None
    class_code: str | None = None
    student_no: str | None = None
    password: str

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)

    @model_validator(mode="after")
    def _check_role_fields(self) -> "LoginRequest":
        if self.role == "teacher":
            if not self.account:
                raise ValueError("教师登录必须填写 account")
            self.account = validate_account(self.account)
        else:
            if not self.class_code or not self.student_no:
                raise ValueError("学生登录必须填写 class_code 与 student_no")
            self.class_code = self.class_code.strip().upper()
            if len(self.class_code) != 6 or not self.class_code.isalnum():
                raise ValueError("班级编号必须为 6 位字母或数字")
            self.student_no = validate_student_no(self.student_no)
        return self


class StudentJoinRequest(BaseModel):
    invite_code: str
    student_no: str
    name: str
    password: str

    @field_validator("invite_code")
    @classmethod
    def _invite_code(cls, value: str) -> str:
        code = (value or "").strip().upper()
        if len(code) != 6 or not code.isalnum():
            raise ValueError("邀请码必须为 6 位大写字母或数字")
        return code

    @field_validator("student_no")
    @classmethod
    def _student_no(cls, value: str) -> str:
        return validate_student_no(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)
