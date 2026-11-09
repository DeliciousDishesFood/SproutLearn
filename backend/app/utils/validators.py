"""输入校验工具：账号、密码、学号、文件名、扩展名、分页。"""

import re
from pathlib import PurePosixPath

# 邮箱使用宽松但明确的格式；手机号按中国大陆 11 位
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
_PHONE_RE = re.compile(r"^1\d{10}$")
_STUDENT_NO_RE = re.compile(r"^[A-Za-z0-9]{4,32}$")
_PASSWORD_LETTER_RE = re.compile(r"[A-Za-z]")
_PASSWORD_DIGIT_RE = re.compile(r"\d")


def validate_account(account: str) -> str:
    """教师账号：4–64 字符，必须是邮箱或 11 位手机号；统一小写。"""
    value = (account or "").strip()
    if not (4 <= len(value) <= 64):
        raise ValueError("账号长度必须为 4–64 个字符")
    if not (_EMAIL_RE.match(value) or _PHONE_RE.match(value)):
        raise ValueError("账号必须是邮箱或 11 位手机号")
    return value.lower()


def validate_phone(phone: str | None) -> str | None:
    if phone is None or not str(phone).strip():
        return None
    value = str(phone).strip()
    if not _PHONE_RE.match(value):
        raise ValueError("手机号必须是 11 位数字")
    return value


def validate_email(email: str | None) -> str | None:
    if email is None or not str(email).strip():
        return None
    value = str(email).strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("邮箱格式不正确")
    return value


def validate_password(password: str) -> str:
    """密码 8–32 位，必须同时包含字母与数字。"""
    value = password or ""
    if not (8 <= len(value) <= 32):
        raise ValueError("密码长度必须为 8–32 个字符")
    if not (_PASSWORD_LETTER_RE.search(value) and _PASSWORD_DIGIT_RE.search(value)):
        raise ValueError("密码必须同时包含字母和数字")
    return value


def validate_name(name: str, max_len: int = 50) -> str:
    value = (name or "").strip()
    if not (1 <= len(value) <= max_len):
        raise ValueError(f"姓名长度必须为 1–{max_len} 个字符")
    return value


def validate_student_no(student_no: str) -> str:
    value = (student_no or "").strip()
    if not _STUDENT_NO_RE.match(value):
        raise ValueError("学号必须为 4–32 位字母或数字")
    return value


def validate_text_field(value: str, field_name: str, max_len: int) -> str:
    text = (value or "").strip()
    if not (1 <= len(text) <= max_len):
        raise ValueError(f"{field_name}长度必须为 1–{max_len} 个字符")
    return text


def sanitize_filename(filename: str | None) -> str:
    """去掉客户端路径，只保留文件名，防目录穿越；保留中文。"""
    raw = (filename or "").replace("\\", "/")
    name = PurePosixPath(raw).name.strip()
    return name or "unnamed"


def extract_ext(filename: str) -> str:
    """提取小写扩展名（不含点）；无扩展名返回空串。"""
    name = sanitize_filename(filename)
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
