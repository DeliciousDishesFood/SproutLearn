"""M2B JSON/XLSX 题库导入：解析、逐行错误、Redis 预览 token、落库。"""

from __future__ import annotations

import json
import secrets
from io import BytesIO
from typing import Any

import openpyxl
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppException, ErrorCode
from app.models.question import Question
from app.redis_client import get_redis_client
from app.utils.cache_keys import question_import_key

DIFFICULTIES = {"easy", "medium", "hard"}
TYPES = {"single", "multiple", "judge", "blank"}
REQUIRED_XLSX_HEADERS = {
    "type",
    "stem",
    "optiona",
    "optionb",
    "optionc",
    "optiond",
    "optione",
    "optionf",
    "answer",
    "analysis",
    "knowledge_tag",
    "difficulty",
}


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


def normalize_item(raw: dict[str, Any], index: int, *, row: int | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """校验并归一化一条导入题；返回 (item, errors)。"""
    errors: list[dict[str, Any]] = []
    type_ = str(raw.get("type", "")).strip().lower()
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
        if isinstance(answer_raw, (list, tuple)):
            values = [str(item).strip() for item in answer_raw if str(item).strip()]
        else:
            text = str(answer_raw or "").strip()
            values = [text] if text else []
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


def _parse_json(content: bytes, max_rows: int) -> dict[str, Any]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - 统一转 42203
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "JSON 文件无法解析", data={"column": "file", "message": str(exc)[:200]}) from exc
    if not isinstance(data, list):
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "JSON 顶层必须是数组", data={"column": "file"})
    if len(data) > max_rows:
        raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            errors.append(_error(index - 1, "file", "每条题目必须是对象"))
            continue
        item, item_errors = normalize_item(raw, index - 1)
        if item:
            items.append(item)
        errors.extend(item_errors)
    return {"total": len(data), "items": items, "errors": errors}


def _parse_xlsx(content: bytes, max_rows: int) -> dict[str, Any]:
    try:
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - 统一转 42203
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLSX 文件无法解析", data={"column": "file", "message": str(exc)[:200]}) from exc
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "XLSX 为空", data={"column": "file"})
    headers = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]
    missing = sorted(REQUIRED_XLSX_HEADERS - set(headers))
    if missing:
        raise AppException(
            ErrorCode.IMPORT_FORMAT_ERROR,
            "XLSX 缺少固定列",
            data={"column": missing[0], "missing": missing},
        )
    header_index = {name: idx for idx, name in enumerate(headers)}
    total = 0
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for row_no, row in enumerate(rows[1:], start=2):
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        total += 1
        if total > max_rows:
            raise AppException(ErrorCode.IMPORT_TOO_LARGE, f"单次最多导入 {max_rows} 题")
        raw: dict[str, Any] = {}
        for name in ("type", "stem", "answer", "analysis", "knowledge_tag", "difficulty"):
            idx = header_index[name]
            raw[name] = row[idx] if idx < len(row) else None
        options = []
        for letter in "ABCDEF":
            idx = header_index[f"option{letter.lower()}"]
            text = row[idx] if idx < len(row) else None
            if text is not None and str(text).strip():
                options.append({"key": letter, "text": str(text).strip()})
        raw["options"] = options or None
        # XLSX 多空/多选答案用逗号/竖线分隔
        answer_value = raw.get("answer")
        if isinstance(answer_value, str):
            if raw.get("type") == "multiple":
                raw["answer"] = _as_keys(answer_value)
            elif raw.get("type") == "blank":
                raw["answer"] = [part.strip() for part in answer_value.replace("||", "|").split("|") if part.strip()]
        item, item_errors = normalize_item(raw, total - 1, row=row_no)
        if item:
            items.append(item)
        errors.extend(item_errors)
    return {"total": total, "items": items, "errors": errors}


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
    raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "仅支持 .json / .xlsx 导入", data={"column": "file"})


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
