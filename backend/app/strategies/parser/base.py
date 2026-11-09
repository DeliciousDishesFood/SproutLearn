"""解析器策略抽象基类：结构化抽取 + 通用滑动窗口切片。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.utils.text import normalize_text


@dataclass
class ParsedChunk:
    content: str
    chapter_title: str | None = None
    page_no: int | None = None


@dataclass
class ParseResult:
    title: str | None = None
    page_count: int | None = None
    chunks: list[ParsedChunk] = field(default_factory=list)


class ParserError(Exception):
    """解析异常基类；code 使用契约错误码字符串。"""

    code: str = "42202"

    def __init__(self, message: str, code: str | None = None) -> None:
        self.code = code or self.code
        super().__init__(message)


class UnsupportedFormat(ParserError):
    code = "41501"


class NoTextLayer(ParserError):
    code = "42201"


class BaseParser(ABC):
    """所有解析器必须实现 extract；构造函数只接收配置，不读全局变量。"""

    supported_ext: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        min_text_chars: int,
        chunk_size: int,
        chunk_overlap: int,
        timeout_seconds: int,
    ) -> None:
        self.min_text_chars = min_text_chars
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, chunk_overlap)
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def extract(self, file_path: str) -> ParseResult:
        """抽取结构化文本；失败抛 ParserError 子类，禁止返回空壳结果。"""

    def make_chunks(
        self,
        text: str,
        *,
        base_chapter: str | None = None,
        page_no: int | None = None,
    ) -> list[ParsedChunk]:
        """对单段文本切片，并给每个切片附加章节/页码元数据。"""
        normalized = normalize_text(text)
        if not normalized:
            return []
        chunks: list[ParsedChunk] = []
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = max(1, self.chunk_size // 2)
        start = 0
        total = len(normalized)
        while start < total:
            end = min(start + self.chunk_size, total)
            content = normalized[start:end].strip()
            if content:
                chunks.append(
                    ParsedChunk(
                        content=content,
                        chapter_title=(base_chapter or None),
                        page_no=page_no,
                    )
                )
            if end >= total:
                break
            start += step
        return chunks

    def split(
        self,
        text: str,
        *,
        base_chapter: str | None = None,
        page_map: dict[int, int] | None = None,
    ) -> list[ParsedChunk]:
        """契约要求的 split 入口；page_map 用于把字符偏移映射到页码。"""
        if not page_map:
            return self.make_chunks(text, base_chapter=base_chapter)
        normalized = normalize_text(text)
        if not normalized:
            return []
        chunks: list[ParsedChunk] = []
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = max(1, self.chunk_size // 2)
        start = 0
        total = len(normalized)
        keys = sorted(page_map)
        while start < total:
            end = min(start + self.chunk_size, total)
            content = normalized[start:end].strip()
            if content:
                page_no = None
                for key in keys:
                    if key <= start:
                        page_no = page_map[key]
                    else:
                        break
                chunks.append(
                    ParsedChunk(content=content, chapter_title=base_chapter, page_no=page_no)
                )
            if end >= total:
                break
            start += step
        return chunks
