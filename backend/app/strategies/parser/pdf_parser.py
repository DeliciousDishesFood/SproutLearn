"""PDF 解析器：pdfplumber 优先，pypdf 兜底；无文本层抛 42201。"""

from __future__ import annotations

from loguru import logger

from app.strategies.parser.base import BaseParser, NoTextLayer, ParseResult, ParserError
from app.strategies.parser.registry import register
from app.utils.text import count_printable_chars, first_non_empty_line


@register("pdf")
class PdfParser(BaseParser):
    def extract(self, file_path: str) -> ParseResult:
        pages, page_count = self._extract_pages(file_path)
        printable = sum(count_printable_chars(text) for text in pages)
        if printable < self.min_text_chars:
            raise NoTextLayer("未检测到文本层，疑似扫描件，请上传可复制文字的 PDF")

        chunks = []
        for page_no, text in enumerate(pages, start=1):
            chapter = first_non_empty_line(text)
            chunks.extend(self.make_chunks(text, base_chapter=chapter, page_no=page_no))
        if not chunks:
            raise NoTextLayer("未检测到文本层，疑似扫描件，请上传可复制文字的 PDF")
        title = next((first_non_empty_line(text) for text in pages if first_non_empty_line(text)), None)
        return ParseResult(title=title, page_count=page_count, chunks=chunks)

    def _extract_pages(self, file_path: str) -> tuple[list[str], int]:
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                pages = [(page.extract_text() or "") for page in pdf.pages]
                return pages, len(pdf.pages)
        except Exception as exc:  # noqa: BLE001 - 换 pypdf 兜底
            logger.warning("pdfplumber 解析失败，尝试 pypdf: {}", exc)

        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            pages = [(page.extract_text() or "") for page in reader.pages]
            return pages, len(reader.pages)
        except Exception as exc:  # noqa: BLE001 - 统一转 42202
            logger.warning("pypdf 解析失败: {}", exc)
            raise ParserError("PDF 文件损坏或无法读取，请检查后重试") from exc
