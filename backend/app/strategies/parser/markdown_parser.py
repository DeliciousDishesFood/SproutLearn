"""Markdown 解析器：按 # 层级分章，正文保留。"""

from __future__ import annotations

import re

from app.strategies.parser.base import BaseParser, ParseResult, ParserError
from app.strategies.parser.registry import register

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def decode_text(content: bytes) -> str:
    """UTF-8 优先，失败换 GB18030；严格解码，避免静默乱码。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ParserError("文本编码无法识别，请使用 UTF-8 或 GB18030 编码")


@register("md")
class MarkdownParser(BaseParser):
    def extract(self, file_path: str) -> ParseResult:
        try:
            with open(file_path, "rb") as handle:
                text = decode_text(handle.read())
        except OSError as exc:
            raise ParserError("Markdown 文件无法读取") from exc

        sections: list[tuple[str, str | None]] = []
        current_title: str | None = None
        buffer: list[str] = []
        title: str | None = None

        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            match = _HEADING_RE.match(line.strip())
            if match:
                if buffer:
                    sections.append(("\n".join(buffer).strip(), current_title))
                    buffer = []
                current_title = match.group(2).strip()[:200]
                if title is None:
                    title = current_title
            else:
                buffer.append(line)
        if buffer:
            sections.append(("\n".join(buffer).strip(), current_title))

        chunks = []
        for section_text, chapter in sections:
            chunks.extend(self.make_chunks(section_text, base_chapter=chapter))
        if not chunks:
            raise ParserError("Markdown 文档没有可提取的文字内容")
        return ParseResult(title=title, page_count=None, chunks=chunks)
