"""编码生成服务：班级编号、邀请码、绑定码；字符集排除易混 O/0/I/1。"""

from __future__ import annotations

import secrets

from app.config import get_settings

# 32 个字符，满足 32^n 的组合量；排除 O/0/I/1 降低手输错误
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_DIGITS = "0123456789"


def _random_code(length: int, alphabet: str) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(max(1, length)))


def generate_class_code() -> str:
    """班级编号：长度 CLASS_CODE_LENGTH（默认 6），大写字母+数字。"""
    return _random_code(get_settings().class_code_length, _CODE_ALPHABET)


def generate_invite_code() -> str:
    """邀请码：长度 INVITE_CODE_LENGTH（默认 6），大写字母+数字。"""
    return _random_code(get_settings().invite_code_length, _CODE_ALPHABET)


def generate_bind_code() -> str:
    """绑定码：8 位数字，首位非 0。"""
    length = max(2, get_settings().bind_code_length)
    return secrets.choice("123456789") + _random_code(length - 1, _DIGITS)
