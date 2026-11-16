"""M3.7 题库 AI 导入：非结构化文件文本抽取（只读内存，不落盘）。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from pathlib import Path

MAX_TEXT_CHARS = 120_000
MAX_PDF_PAGES = 50
MAX_DOCX_TABLES = 30
MAX_SHEETS = 20
MAX_ROWS = 5000
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
SUPPORTED_EXTS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".csv",
    ".json",
    ".txt",
    ".md",
    ".markdown",
}


@dataclass
class ExtractResult:
    text: str
    source_name: str
    warnings: list[str] = field(default_factory=list)
    chars: int = 0
    pages_or_sheets: int = 0


def _clean(text: str) -> str:
    text = (text or "").replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    out: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank and out:
                out.append("")
            blank = True
            continue
        blank = False
        out.append(line)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out).strip()


def _decode(content: bytes) -> tuple[str | None, str | None]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def _finish(text: str, source_name: str, warnings: list[str], pages: int) -> ExtractResult:
    cleaned = _clean(text)
    if len(cleaned) > MAX_TEXT_CHARS:
        cleaned = cleaned[:MAX_TEXT_CHARS].rstrip()
        warnings.append(f"文本超过 {MAX_TEXT_CHARS} 字符，已截断")
    if not cleaned:
        warnings.append("未提取到有效文本")
    return ExtractResult(
        text=cleaned,
        source_name=source_name,
        warnings=warnings,
        chars=len(cleaned),
        pages_or_sheets=pages,
    )


def _extract_pdf(content: bytes) -> tuple[str, list[str], int]:
    warnings: list[str] = []
    parts: list[str] = []
    pages = 0
    try:
        import pdfplumber

        with pdfplumber.open(BytesIO(content)) as pdf:
            pages = len(pdf.pages)
            for index, page in enumerate(pdf.pages[:MAX_PDF_PAGES]):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        parts.append(text)
                except Exception:  # noqa: BLE001 - 单页失败不阻断
                    warnings.append(f"PDF 第 {index + 1} 页解析失败，已跳过")
    except Exception:  # noqa: BLE001
        warnings.append("PDF 主解析器失败，尝试备用解析器")
    if not "".join(parts).strip():
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            pages = len(reader.pages)
            fallback: list[str] = []
            for index, page in enumerate(reader.pages[:MAX_PDF_PAGES]):
                try:
                    fallback.append(page.extract_text() or "")
                except Exception:  # noqa: BLE001
                    warnings.append(f"PDF 备用解析第 {index + 1} 页失败，已跳过")
            parts = fallback
        except Exception:  # noqa: BLE001
            warnings.append("PDF 备用解析器失败")
    if len(parts) > MAX_PDF_PAGES or pages > MAX_PDF_PAGES:
        warnings.append(f"PDF 超过 {MAX_PDF_PAGES} 页，已截断")
    text = "\n\n".join(parts)
    if not text.strip():
        warnings.append("PDF 无文字层，可能是扫描件")
    return text, warnings, pages


def _extract_docx(content: bytes) -> tuple[str, list[str], int]:
    warnings: list[str] = []
    from docx import Document

    document = Document(BytesIO(content))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    tables = document.tables
    if len(tables) > MAX_DOCX_TABLES:
        warnings.append(f"Word 表格超过 {MAX_DOCX_TABLES} 张，已截断")
    for table in tables[:MAX_DOCX_TABLES]:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts), warnings, len(tables)


def _extract_pptx(content: bytes) -> tuple[str, list[str], int]:
    from pptx import Presentation

    presentation = Presentation(BytesIO(content))
    parts: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text.strip():
                parts.append(shape.text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
        if not parts:
            parts.append("")
        parts.append(f"--- 第 {index} 页 ---")
    return "\n".join(parts), [], len(presentation.slides)


def _extract_xlsx(content: bytes) -> tuple[str, list[str], int]:
    import openpyxl

    warnings: list[str] = []
    workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    sheets = workbook.worksheets
    if len(sheets) > MAX_SHEETS:
        warnings.append(f"Excel sheet 超过 {MAX_SHEETS} 个，已截断")
    parts: list[str] = []
    rows = 0
    for sheet in sheets[:MAX_SHEETS]:
        parts.append(f"## {sheet.title}")
        for row_no, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            if rows >= MAX_ROWS:
                warnings.append(f"Excel 行数超过 {MAX_ROWS}，已截断")
                break
            cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if cells:
                parts.append(f"{sheet.title}!{row_no} | " + " | ".join(cells))
                rows += 1
        if rows >= MAX_ROWS:
            break
    workbook.close()
    return "\n".join(parts), warnings, len(sheets)


def _extract_xls(content: bytes) -> tuple[str, list[str], int]:
    import xlrd

    warnings: list[str] = []
    workbook = xlrd.open_workbook(file_contents=content)
    sheets = workbook.sheets()
    if len(sheets) > MAX_SHEETS:
        warnings.append(f"Excel sheet 超过 {MAX_SHEETS} 个，已截断")
    parts: list[str] = []
    rows = 0
    for sheet in sheets[:MAX_SHEETS]:
        parts.append(f"## {sheet.name}")
        for row_index in range(sheet.nrows):
            if rows >= MAX_ROWS:
                warnings.append(f"Excel 行数超过 {MAX_ROWS}，已截断")
                break
            values = [str(cell).strip() for cell in sheet.row_values(row_index) if str(cell).strip()]
            if values:
                parts.append(f"{sheet.name}!{row_index + 1} | " + " | ".join(values))
                rows += 1
        if rows >= MAX_ROWS:
            break
    return "\n".join(parts), warnings, len(sheets)


def _extract_csv(content: bytes) -> tuple[str, list[str], int]:
    text, _encoding = _decode(content)
    if text is None:
        return "", ["CSV 编码无法识别（支持 UTF-8 / GB18030）"], 0
    rows = list(csv.reader(StringIO(text)))
    parts = []
    for index, row in enumerate(rows, start=1):
        cells = [cell.strip() for cell in row if cell and cell.strip()]
        if cells:
            parts.append(f"CSV!{index} | " + " | ".join(cells))
    return "\n".join(parts), [], len(rows)


def _extract_json(content: bytes) -> tuple[str, list[str], int]:
    text, _encoding = _decode(content)
    if text is None:
        return "", ["JSON 编码无法识别"], 0
    try:
        data = json.loads(text)
    except ValueError:
        return text, ["JSON 解析失败，已按纯文本处理"], 0
    if isinstance(data, list):
        return json.dumps(data, ensure_ascii=False), [], 0
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        return json.dumps(data["questions"], ensure_ascii=False), [], 0
    return text, ["JSON 不是题目数组，已按纯文本处理"], 0


def extract_text(filename: str, content: bytes) -> ExtractResult:
    """按扩展名抽取文本；不支持/图片返回空文本 + warning，由上层转 42203。"""
    source_name = Path(filename or "upload").name
    ext = Path(source_name).suffix.lower()
    if ext in IMAGE_EXTS:
        return _finish(
            "",
            source_name,
            ["图片识别暂未开放，请上传可复制文字的 PDF / Word / Excel / TXT 文件。"],
            0,
        )
    if ext not in SUPPORTED_EXTS:
        return _finish("", source_name, [f"不支持的文件格式：{ext or '未知'}"], 0)
    try:
        if ext == ".pdf":
            text, warnings, pages = _extract_pdf(content)
        elif ext == ".docx":
            text, warnings, pages = _extract_docx(content)
        elif ext == ".pptx":
            text, warnings, pages = _extract_pptx(content)
        elif ext == ".xlsx":
            text, warnings, pages = _extract_xlsx(content)
        elif ext == ".xls":
            text, warnings, pages = _extract_xls(content)
        elif ext == ".csv":
            text, warnings, pages = _extract_csv(content)
        elif ext == ".json":
            text, warnings, pages = _extract_json(content)
        else:
            decoded, encoding = _decode(content)
            if decoded is None:
                text, warnings, pages = "", ["文本编码无法识别（支持 UTF-8 / GB18030）"], 0
            else:
                text, warnings, pages = decoded, [], 0
    except Exception as exc:  # noqa: BLE001 - 解析异常转可读 warning
        return _finish("", source_name, [f"文件解析失败：{type(exc).__name__}"], 0)
    return _finish(text, source_name, warnings, pages)
