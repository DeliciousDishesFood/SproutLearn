"""解析器策略包：对外暴露基类、结果结构与注册表入口。"""

from app.strategies.parser.base import (
    BaseParser,
    NoTextLayer,
    ParsedChunk,
    ParseResult,
    ParserError,
    UnsupportedFormat,
)
from app.strategies.parser.registry import get_parser, register, registered_exts

__all__ = [
    "BaseParser",
    "ParsedChunk",
    "ParseResult",
    "ParserError",
    "UnsupportedFormat",
    "NoTextLayer",
    "get_parser",
    "register",
    "registered_exts",
]
