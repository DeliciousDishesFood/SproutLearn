"""TXT 解析器：编码探测（UTF-8 → GB18030），按滑动窗口分段。"""

from __future__ import annotations

from app.strategies.parser.base import BaseParser, ParseResult, ParserError
from app.strategies.parser.markdown_parser import decode_text
from app.strategies.parser.registry import register


@register("txt")
class TxtParser(BaseParser):
    def extract(self, file_path: str) -> ParseResult:
        try:
            with open(file_path, "rb") as handle:
                text = decode_text(handle.read())
        except OSError as exc:
            raise ParserError("TXT 文件无法读取") from exc

        chunks = self.make_chunks(text)
        if not chunks:
            raise ParserError("TXT 文档没有可提取的文字内容")
        return ParseResult(title=None, page_count=None, chunks=chunks)
