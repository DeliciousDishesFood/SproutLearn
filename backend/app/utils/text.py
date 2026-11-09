"""文本归一化与哈希工具：解析切片、去重、字符统计复用。"""

import hashlib
import re
import unicodedata


def sha256_hex(content: bytes) -> str:
    """文件内容 sha256（小写十六进制）。"""
    return hashlib.sha256(content).hexdigest()


def normalize_text(text: str) -> str:
    """统一换行、去行尾空白、压缩连续空行，保留中文正文。"""
    value = unicodedata.normalize("NFC", text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def count_printable_chars(text: str) -> int:
    """统计可打印字符数（PDF 扫描件判定用）。"""
    return sum(1 for ch in text or "" if ch.isprintable() and not ch.isspace())


def char_count(text: str) -> int:
    """切片字符数：中文按 1 字符。"""
    return len(text or "")


def first_non_empty_line(text: str, max_len: int = 200) -> str | None:
    """取第一行非空文本作为章节标题候选。"""
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line[:max_len]
    return None
