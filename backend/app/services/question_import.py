"""M2.5 题库导入：JSON/XLSX/XLS/CSV、动态表头、行级错误与预览 token。"""

from __future__ import annotations

import csv
import json
import re
import secrets
import unicodedata
from difflib import SequenceMatcher
from io import BytesIO, StringIO
from typing import Any

import openpyxl
import xlrd
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppException, ErrorCode
from app.models.question import Question
from app.redis_client import get_redis_client
from app.utils.cache_keys import question_import_key

DIFFICULTIES = {"easy", "medium", "hard"}
TYPES = {"single", "multiple", "judge", "blank"}
OPTION_LETTERS = "ABCDEF"
STANDARD_FIELDS = {
    "type",
    "stem",
    "options",
    "answer",
    "analysis",
    "knowledge_tag",
    "difficulty",
    *[f"option{letter}" for letter in OPTION_LETTERS],
}

_TYPE_ALIASES = {
    "single": "single",
    "single_choice": "single",
    "单选": "single",
    "单选题": "single",
    "choice": "single",
    "multiple": "multiple",
    "multiple_choice": "multiple",
    "多选": "multiple",
    "多选题": "multiple",
    "judge": "judge",
    "true_false": "judge",
    "判断": "judge",
    "判断题": "judge",
    "blank": "blank",
    "fill_blank": "blank",
    "填空": "blank",
    "填空题": "blank",
}

_SYNONYMS: dict[str, str] = {
    "题干": "stem",
    "题目": "stem",
    "问题": "stem",
    "试题": "stem",
    "content": "stem",
    "question": "stem",
    "stem": "stem",
    "类型": "type",
    "题型": "type",
    "type": "type",
    "选项": "options",
    "options": "options",
    "答案": "answer",
    "正确答案": "answer",
    "参考答案": "answer",
    "answer": "answer",
    "解析": "analysis",
    "答案解析": "analysis",
    "讲解": "analysis",
    "analysis": "analysis",
    "知识点": "knowledge_tag",
    "考点": "knowledge_tag",
    "标签": "knowledge_tag",
    "分类": "knowledge_tag",
    "tag": "knowledge_tag",
    "knowledge": "knowledge_tag",
    "knowledge_tag": "knowledge_tag",
    "难度": "difficulty",
    "difficulty": "difficulty",
    "level": "difficulty",
}
for _index, _letter in enumerate(OPTION_LETTERS, start=1):
    _SYNONYMS[f"选项{_letter}"] = f"option{_letter}"
    _SYNONYMS[_letter] = f"option{_letter}"
    _SYNONYMS[f"option{_letter}"] = f"option{_letter}"
    _SYNONYMS[f"选项{_index}"] = f"option{_letter}"


def _norm_header(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return "".join(
        ch for ch in text if not ch.isspace() and not unicodedata.category(ch).startswith("P")
    )


def _candidate_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for field in STANDARD_FIELDS:
        result[_norm_header(field)] = field
    for name, field in _SYNONYMS.items():
        result[_norm_header(name)] = field
    return result


_CANDIDATES = _candidate_map()


def map_headers(headers: list[Any]) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """精确→同义词→模糊；返回原表头到标准字段、匹配质量、未映射列。"""
    mapping: dict[str, str] = {}
    quality: dict[str, str] = {}
    unmapped: list[str] = []
    used: set[str] = set()
    for raw in headers:
        header = str(raw).strip() if raw is not None else ""
        if not header:
            continue
        normalized = _norm_header(header)
        target: str | None = None
        match = ""
        if normalized in STANDARD_FIELDS or normalized in {_norm_header(f) for f in STANDARD_FIELDS}:
            target = next((f for f in STANDARD_FIELDS if _norm_header(f) == normalized), normalized)
            match = "exact"
        elif normalized in _CANDIDATES:
            target = _CANDIDATES[normalized]
            match = "synonym"
        else:
            best: tuple[float, str] | None = None
            for candidate, field in _CANDIDATES.items():
                if len(candidate) < 2:
                    continue
                ratio = SequenceMatcher(None, normalized, candidate).ratio()
                if candidate in normalized or normalized in candidate:
                    ratio = max(ratio, 0.86)
                if ratio >= 0.72 and (best is None or ratio > best[0]):
                    best = (ratio, field)
            if best is not None:
                target = best[1]
                match = "fuzzy"
        if target is None or target in used:
            unmapped.append(header)
            continue
        mapping[header] = target
        quality[header] = match
        used.add(target)
    return mapping, quality, unmapped


def _error(index: int, column: str, message: str, *, row: int | None = None) -> dict[str, Any]:
    return {
        "index": index,
        "row": row if row is not None else index + 1,
        "column": column,
        "message": message,
    }


def _normalize_options(raw_options: Any) -> tuple[list[dict[str, str]] | None, str | None]:
    if raw_options in (None, "", []):
        return None, None
    if not isinstance(raw_options, list):
        return None, "options 必须是 {key,text} 数组"
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_options:
        if not isinstance(item, dict):
            return None, "options 每项必须是 {key,text}"
        key = str(item.get("key", "")).strip().upper()
        text = str(item.get("text", "")).strip()
        if not key or not text:
            return None, "options 的 key/text 不能为空"
        if len(key) != 1 or key in seen:
            return None, "options key 必须唯一且为单个字母"
        seen.add(key)
        cleaned.append({"key": key, "text": text})
    return cleaned, None


def _as_keys(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip().upper() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    for sep in (",", "，", "、", ";", "；"):
        text = text.replace(sep, ",")
    return [item.strip().upper() for item in text.split(",") if item.strip()]


def _as_truth(value: Any) -> bool | None:
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y", "对", "正确", "是"}:
        return True
    if text in {"false", "f", "0", "no", "n", "错", "错误", "否"}:
        return False
    return None


def _normalize_type(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    return _TYPE_ALIASES.get(text, "invalid")


def _infer_type(raw: dict[str, Any]) -> str:
    options, _ = _normalize_options(raw.get("options"))
    answer = raw.get("answer")
    if options:
        if isinstance(answer, (list, tuple, set)):
            return "multiple" if len(answer) > 1 else "single"
        return "multiple" if len(_as_keys(answer)) > 1 else "single"
    if _as_truth(answer) is not None:
        return "judge"
    return "blank"


def _blank_values(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    if "|" in text or "\n" in text:
        return [part.strip() for part in re.split(r"\|+|\n+", text) if part.strip()]
    return [text]


def normalize_item(raw: dict[str, Any], index: int, *, row: int | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """校验并归一化一条导入题；返回 (item, errors)。"""
    errors: list[dict[str, Any]] = []
    type_raw = _normalize_type(raw.get("type"))
    type_ = type_raw if type_raw in TYPES else ""
    if type_raw == "invalid":
        errors.append(_error(index, "type", "type 必须为 single/multiple/judge/blank", row=row))
    elif type_raw is None:
        type_ = _infer_type(raw)
    if type_ not in TYPES:
        errors.append(_error(index, "type", "type 必须为 single/multiple/judge/blank", row=row))

    stem = str(raw.get("stem", "")).strip()
    if not stem:
        errors.append(_error(index, "stem", "题干不能为空", row=row))

    options, option_error = _normalize_options(raw.get("options"))
    if option_error:
        errors.append(_error(index, "options", option_error, row=row))

    answer_raw = raw.get("answer")
    answer: Any = None
    if type_ == "single":
        value = str(answer_raw or "").strip().upper()
        if not value:
            errors.append(_error(index, "answer", "单选题答案不能为空", row=row))
        elif options and value not in {item["key"] for item in options}:
            errors.append(_error(index, "answer", "答案不在选项中", row=row))
        else:
            answer = value
    elif type_ == "multiple":
        values = _as_keys(answer_raw)
        if not values:
            errors.append(_error(index, "answer", "多选题答案不能为空", row=row))
        elif options and not set(values).issubset({item["key"] for item in options}):
            errors.append(_error(index, "answer", "答案包含不在选项中的 key", row=row))
        else:
            answer = values
    elif type_ == "judge":
        value = _as_truth(answer_raw)
        if value is None:
            errors.append(_error(index, "answer", "判断题答案必须为 true/false/对/错", row=row))
        else:
            answer = value
    elif type_ == "blank":
        values = _blank_values(answer_raw)
        if not values:
            errors.append(_error(index, "answer", "填空题答案不能为空", row=row))
        else:
            answer = values

    tag = str(raw.get("knowledge_tag") or "未分类").strip() or "未分类"
    if len(tag) > 50:
        errors.append(_error(index, "knowledge_tag", "知识点标签不能超过 50 字符", row=row))
    difficulty = str(raw.get("difficulty") or "medium").strip().lower()
    if difficulty not in DIFFICULTIES:
        errors.append(_error(index, "difficulty", "difficulty 必须为 easy/medium/hard", row=row))

    if type_ in {"single", "multiple"} and not options:
        errors.append(_error(index, "options", "选择题必须提供 options/A-F 选项", row=row))
    if type_ in {"judge", "blank"}:
        options = options or None

    analysis = raw.get("analysis")
    analysis_text = str(analysis).strip() if analysis is not None else None

    if errors:
        return None, errors
    return {
        "type": type_,
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": analysis_text,
        "knowledge_tag": tag,
        "difficulty": difficulty,
    }, []


def _options_from_cell(value: Any) -> list[dict[str, str]] | None:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    return parsed if isinstance(parsed, list) else None


def _row_from_mapping(
    raw_values: dict[str, Any],
    mapping: dict[str, str],
    *,
    index: int,
    row_no: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    raw: dict[str, Any] = {}
    option_values: list[dict[str, str]] = []
    for header, target in mapping.items():
        value = raw_values.get(header)
        if target.startswith("option") and target != "options":
            letter = target.removeprefix("option").upper()
            if value is not None and str(value).strip():
                option_values.append({"key": letter, "text": str(value).strip()})
        elif target == "options":
            parsed = _options_from_cell(value)
            raw["options"] = parsed if parsed is not None else value
        else:
            raw[target] = value
    if option_values:
        raw["options"] = option_values
    raw["type"] = raw.get("type") or _infer_type(raw)
    return normalize_item(raw, index, row=row_no)


def _preview_from_rows(
    headers: list[Any],
    rows: list[tuple[int, dict[str, Any]]],
    *,
    source: str,
    require_mapped: bool,
) -> dict[str, Any]:
    mapping, quality, unmapped = map_headers(headers)
    if require_mapped:
        missing = [field for field in ("stem", "answer") if field not in mapping.values()]
        if missing:
            raise AppException(
                ErrorCode.IMPORT_FORMAT_ERROR,
                f"{source} 缺少必填列",
                data={"column": missing[0], "missing": missing},
            )
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []
    for index, (row_no, raw_values) in enumerate(rows, start=1):
        item, row_errors = _row_from_mapping(raw_values, mapping, index=index - 1, row_no=row_no)
        if item is not None:
            items.append(item)
        errors.extend(row_errors)
        warnings = [
            {"column": header, "message": "按模糊匹配推测"}
            for header, match in quality.items()
            if match == "fuzzy"
        ]
        preview_rows.append(
            {
                "index": index,
                "normalized": item,
                "warnings": warnings,
                "errors": row_errors,
            }
        )
    return {
        "total": len(rows),
        "items": items,
        "errors": errors,
        "mapping": mapping,
        "mapping_meta": quality,
        "unmapped_columns": unmapped,
        "rows": preview_rows,
        "stats": {
            "total": len(rows),
            "valid": len(items),
            "invalid": len(rows) - len(items),
        },
    }


def _parse_json(content: bytes, max_rows: int) -> dict[str, Any]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - 统一转 42203
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "JSON 文件无法解析", data={"column": "file", "message": str(exc)[:200]}) from exc
    if not isinstance(data, list):
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "JSON 顶层必须是数组", data={"column": "file"})
    if len(data) > max_rows:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
    headers: list[str] = []
    for item in data:
        if isinstance(item, dict):
            for key in item:
                if str(key) not in headers:
                    headers.append(str(key))
    rows = [
        (index, {str(key): value for key, value in item.items()})
        for index, item in enumerate(data, start=1)
        if isinstance(item, dict)
    ]
    invalid_count = len(data) - len(rows)
    result = _preview_from_rows(headers, rows, source="JSON", require_mapped=False)
    if invalid_count:
        result["total"] += invalid_count
        result["stats"]["total"] += invalid_count
        result["stats"]["invalid"] += invalid_count
    return result


def _parse_csv(content: bytes, max_rows: int) -> dict[str, Any]:
    text = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "CSV 编码无法识别", data={"column": "file"})
    reader = list(csv.reader(StringIO(text)))
    if not reader:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "CSV 为空", data={"column": "file"})
    headers = reader[0]
    data_rows = [
        (row_no, {str(headers[i]): value for i, value in enumerate(row) if i < len(headers)})
        for row_no, row in enumerate(reader[1:], start=2)
        if any(str(value).strip() for value in row)
    ]
    if len(data_rows) > max_rows:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
    return _preview_from_rows(headers, data_rows, source="CSV", require_mapped=True)


def _parse_xlsx(content: bytes, max_rows: int) -> dict[str, Any]:
    try:
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - 统一转 42203
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLSX 文件无法解析", data={"column": "file", "message": str(exc)[:200]}) from exc
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLSX 为空", data={"column": "file"})
    headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    data_rows = [
        (row_no, {headers[i]: value for i, value in enumerate(row) if i < len(headers)})
        for row_no, row in enumerate(rows[1:], start=2)
        if any(cell is not None and str(cell).strip() for cell in row)
    ]
    if len(data_rows) > max_rows:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
    return _preview_from_rows(headers, data_rows, source="XLSX", require_mapped=True)


def _parse_xls(content: bytes, max_rows: int) -> dict[str, Any]:
    try:
        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(0)
    except Exception as exc:  # noqa: BLE001 - 统一转 42203
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLS 文件无法解析", data={"column": "file", "message": str(exc)[:200]}) from exc
    if sheet.nrows == 0:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLS 为空", data={"column": "file"})
    headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]
    data_rows = [
        (row_no + 1, {headers[col]: sheet.cell_value(row_no, col) for col in range(sheet.ncols)})
        for row_no in range(1, sheet.nrows)
        if any(str(sheet.cell_value(row_no, col)).strip() for col in range(sheet.ncols))
    ]
    if len(data_rows) > max_rows:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
    return _preview_from_rows(headers, data_rows, source="XLS", require_mapped=True)


def parse_import(content: bytes, filename: str) -> dict[str, Any]:
    """按扩展名解析；文件大小/行数上限在这里统一拦截。"""
    settings = get_settings()
    max_bytes = settings.question_import_max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"导入文件不能超过 {settings.question_import_max_mb}MB")
    name = (filename or "").lower()
    if name.endswith(".json"):
        return _parse_json(content, settings.question_import_max_rows)
    if name.endswith(".xlsx"):
        return _parse_xlsx(content, settings.question_import_max_rows)
    if name.endswith(".xls"):
        return _parse_xls(content, settings.question_import_max_rows)
    if name.endswith(".csv"):
        return _parse_csv(content, settings.question_import_max_rows)
    raise AppException(
        ErrorCode.IMPORT_FORMAT_ERROR,
        "仅支持 .json / .xlsx / .xls / .csv 导入",
        data={"column": "file"},
    )


def normalize_edited_rows(rows: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """commit rows 覆盖：重新校验前端编辑后的 normalized 行。"""
    settings = get_settings()
    if len(rows) > settings.question_import_max_rows:
        raise AppException(
            ErrorCode.IMPORT_TOO_LARGE,
            f"单次最多导入 {settings.question_import_max_rows} 题",
        )
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        raw = row.get("normalized") if isinstance(row, dict) and "normalized" in row else row
        if not isinstance(raw, dict):
            errors.append(_error(index - 1, "row", "行必须是对象"))
            continue
        raw = dict(raw)
        raw["type"] = raw.get("type") or _infer_type(raw)
        item, row_errors = normalize_item(raw, index - 1, row=index)
        if item is not None:
            items.append(item)
        errors.extend(row_errors)
    return items, errors


def store_preview(*, class_id: int, teacher_id: int, parsed: dict[str, Any]) -> str:
    """把预览结果（含逐行错误）写入 Redis，返回一次性 token。"""
    settings = get_settings()
    token = secrets.token_urlsafe(24)
    payload = json.dumps(
        {
            "class_id": class_id,
            "teacher_id": teacher_id,
            "items": parsed["items"],
            "errors": parsed["errors"],
            "total": parsed["total"],
            "mapping": parsed.get("mapping", {}),
            "unmapped_columns": parsed.get("unmapped_columns", []),
        },
        ensure_ascii=False,
    )
    try:
        get_redis_client().setex(
            question_import_key(token),
            settings.question_import_token_ttl_seconds,
            payload,
        )
    except Exception as exc:  # noqa: BLE001 - Redis 不可用统一 50301
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
    return token


def load_preview(token: str, *, class_id: int, teacher_id: int) -> dict[str, Any]:
    try:
        raw = get_redis_client().get(question_import_key(token))
    except Exception as exc:  # noqa: BLE001
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
    if not raw:
        raise AppException(ErrorCode.NOT_FOUND, "导入预览已过期，请重新上传")
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "导入预览数据损坏") from exc
    if payload.get("class_id") != class_id or payload.get("teacher_id") != teacher_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权使用该导入预览")
    return payload


def clear_preview(token: str) -> None:
    try:
        get_redis_client().delete(question_import_key(token))
    except Exception:  # noqa: BLE001 - 清理失败不阻塞提交
        pass


def commit_questions(
    db: Session,
    *,
    class_id: int,
    teacher_id: int,
    items: list[dict[str, Any]],
) -> list[int]:
    """把预览中的有效题写入 question 表（draft）。"""
    if not items:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "没有可导入的题目")
    created: list[Question] = []
    for item in items:
        question = Question(
            class_id=class_id,
            type=item["type"],
            stem=item["stem"],
            options_json=item.get("options"),
            answer_json=item["answer"],
            analysis=item.get("analysis"),
            knowledge_tag=item.get("knowledge_tag") or "未分类",
            difficulty=item.get("difficulty") or "medium",
            status="draft",
            created_by=teacher_id,
        )
        db.add(question)
        created.append(question)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    for question in created:
        db.refresh(question)
    return [question.id for question in created]
