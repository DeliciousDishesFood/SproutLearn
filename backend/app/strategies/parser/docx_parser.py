"""Word 解析器：python-docx 按段落与标题样式分级。"""

from __future__ import annotations

from loguru import logger

from app.strategies.parser.base import BaseParser, ParseResult, ParserError
from app.strategies.parser.registry import register
from app.utils.text import first_non_empty_line


@register("docx", "doc")
class DocxParser(BaseParser):
    def extract(self, file_path: str) -> ParseResult:
        try:
            from docx import Document

            document = Document(file_path)
        except Exception as exc:  # noqa: BLE001 - 损坏或旧版 doc
            logger.warning("docx 打开失败: {}", exc)
            raise ParserError("Word 文件无法读取；旧版 .doc 请另存为 .docx 后重试") from exc

        segments: list[tuple[str, str | None]] = []
        current_chapter: str | None = None
        buffer: list[str] = []
        title: str | None = None

        for paragraph in document.paragraphs:
            text = (paragraph.text or "").strip()
            if not text:
                continue
            if title is None:
                title = text[:200]
            style = (paragraph.style.name or "") if paragraph.style is not None else ""
            is_heading = style.startswith("Heading") or style.startswith("标题") or style.startswith("Title")
            if is_heading:
                if buffer:
                    segments.append(("\n".join(buffer), current_chapter))
                    buffer = []
                current_chapter = text[:200]
            else:
                buffer.append(text)
        if buffer:
            segments.append(("\n".join(buffer), current_chapter))

        chunks = []
        for text, chapter in segments:
            chunks.extend(self.make_chunks(text, base_chapter=chapter))
        if not chunks:
            raise ParserError("Word 文档没有可提取的文字内容")
        return ParseResult(title=title or first_non_empty_line(chunks[0].content), page_count=None, chunks=chunks)
