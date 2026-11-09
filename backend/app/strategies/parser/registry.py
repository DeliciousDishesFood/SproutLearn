"""解析器注册表：新增格式只加实现类 + @register，不改调用方。"""

from __future__ import annotations

from loguru import logger

from app.strategies.parser.base import BaseParser, UnsupportedFormat

_PARSERS: dict[str, type[BaseParser]] = {}


def register(*exts: str):
    """扩展名 → Parser 类注册装饰器。"""

    def deco(cls: type[BaseParser]) -> type[BaseParser]:
        cls.supported_ext = tuple(ext.lower().lstrip(".") for ext in exts)
        for ext in cls.supported_ext:
            _PARSERS[ext] = cls
        return cls

    return deco


def get_parser(ext: str, settings) -> BaseParser:
    """按扩展名实例化解析器；未注册扩展名抛 41501。"""
    cls = _PARSERS.get((ext or "").lower().lstrip("."))
    if not cls:
        raise UnsupportedFormat(f"不支持的文件类型: {ext}")
    logger.debug("选择解析器 {} → {}", ext, cls.__name__)
    return cls(
        min_text_chars=settings.pdf_min_text_chars,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        timeout_seconds=settings.parser_timeout_seconds,
    )


def registered_exts() -> list[str]:
    return sorted(_PARSERS.keys())


# 导入即注册；放在函数定义之后避免循环导入
from app.strategies.parser import (  # noqa: E402,F401
    docx_parser,
    markdown_parser,
    pdf_parser,
    pptx_parser,
    txt_parser,
)
