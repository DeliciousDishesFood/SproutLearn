"""PPT 解析器：python-pptx 只取文本框文字，幻灯片序号记为 page_no。"""

from __future__ import annotations

from loguru import logger

from app.strategies.parser.base import BaseParser, ParseResult, ParserError
from app.strategies.parser.registry import register


@register("pptx", "ppt")
class PptxParser(BaseParser):
    def extract(self, file_path: str) -> ParseResult:
        try:
            from pptx import Presentation

            presentation = Presentation(file_path)
        except Exception as exc:  # noqa: BLE001 - 损坏或旧版 ppt
            logger.warning("pptx 打开失败: {}", exc)
            raise ParserError("PPT 文件无法读取；旧版 .ppt 请另存为 .pptx 后重试") from exc

        chunks = []
        title: str | None = None
        slides = list(presentation.slides)
        for index, slide in enumerate(slides, start=1):
            texts: list[str] = []
            slide_title: str | None = None
            try:
                if slide.shapes.title is not None and slide.shapes.title.text:
                    slide_title = slide.shapes.title.text.strip()[:200]
            except Exception:  # noqa: BLE001 - 无标题占位符
                slide_title = None
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    text = (paragraph.text or "").strip()
                    if text:
                        texts.append(text)
            if not texts:
                continue
            if title is None:
                title = slide_title or texts[0][:200]
            chunks.extend(
                self.make_chunks("\n".join(texts), base_chapter=slide_title, page_no=index)
            )
        if not chunks:
            raise ParserError("PPT 文档没有可提取的文字内容")
        return ParseResult(title=title, page_count=len(slides), chunks=chunks)
