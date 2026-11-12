"""M2B 题库业务：导入预览/提交、筛选、编辑、软删除、讲评。"""

from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.question import Question
from app.repositories.question_repo import QuestionRepository
from app.repositories.question_bank_repo import QuestionBankRepository
from app.schemas.question import QuestionUpdateRequest
from app.services import question_bank_service
from app.services.class_service import require_owned_class
from app.services.question_import import (
    clear_preview,
    commit_questions,
    load_preview,
    normalize_edited_rows,
    normalize_item,
    parse_import,
    store_preview,
)
from app.services.llm.router import build_router
from app.utils.response import page_data
from app.utils.time import fmt_dt, now_naive

_settings = get_settings()


def _item(question: Question, bank_name: str | None = None) -> dict[str, Any]:
    return {
        "id": question.id,
        "class_id": question.class_id,
        "bank_id": question.bank_id,
        "bank_name": bank_name,
        "type": question.type,
        "stem": question.stem,
        "options": question.options_json,
        "answer": question.answer_json,
        "analysis": question.analysis,
        "knowledge_tag": question.knowledge_tag,
        "difficulty": question.difficulty,
        "status": question.status,
        "created_at": fmt_dt(question.created_at),
        "updated_at": fmt_dt(question.updated_at),
    }


def preview_import(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    content: bytes,
    filename: str,
    bank_id: int | None = None,
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    bank = (
        question_bank_service.resolve_bank(db, class_id=class_id, bank_id=bank_id)
        if bank_id is not None
        else None
    )
    parsed = parse_import(content, filename)
    token = store_preview(
        class_id=class_id,
        teacher_id=current.user_id,
        parsed=parsed,
        bank_id=bank.id if bank else None,
    )
    suggested = question_bank_service.suggested_bank_name(filename)
    return {
        "token": token,
        "total": parsed["total"],
        "valid_count": len(parsed["items"]),
        "error_count": len(parsed["errors"]),
        "errors": parsed["errors"],
        "preview": parsed["items"],
        "mapping": parsed.get("mapping", {}),
        "mapping_meta": parsed.get("mapping_meta", {}),
        "unmapped_columns": parsed.get("unmapped_columns", []),
        "rows": parsed.get("rows", []),
        "stats": parsed.get(
            "stats",
            {
                "total": parsed["total"],
                "valid": len(parsed["items"]),
                "invalid": len(parsed["errors"]),
            },
        ),
        "bank_id": bank.id if bank else None,
        "bank_name": bank.name if bank else None,
        "suggested_bank_name": suggested,
    }


def commit_import(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    token: str | None,
    content: bytes | None,
    filename: str | None,
    rows: list[Any] | None = None,
    bank_id: int | None = None,
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    errors: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    if token:
        payload = load_preview(token, class_id=class_id, teacher_id=current.user_id)
        if rows is not None:
            if not isinstance(rows, list):
                raise AppException(ErrorCode.VALIDATION_ERROR, "rows 必须是数组")
            items, errors = normalize_edited_rows(rows)
        else:
            items = payload.get("items") or []
            errors = payload.get("errors") or []
    else:
        if rows is not None:
            raise AppException(ErrorCode.VALIDATION_ERROR, "rows 覆盖提交必须同时提供 token")
        if content is None:
            raise AppException(ErrorCode.VALIDATION_ERROR, "必须提供 token 或导入文件")
        parsed = parse_import(content, filename or "")
        items = parsed["items"]
        errors = parsed["errors"]
    if errors:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "导入存在格式错误，请修正后重试", data={"errors": errors})
    target_bank_id = bank_id if bank_id is not None else payload.get("bank_id")
    if target_bank_id is not None:
        bank = question_bank_service.resolve_bank(
            db, class_id=class_id, bank_id=int(target_bank_id)
        )
    else:
        bank = question_bank_service.get_or_create_import_bank(
            db, class_id=class_id, teacher_id=current.user_id
        )
    ids = commit_questions(
        db,
        class_id=class_id,
        teacher_id=current.user_id,
        bank_id=bank.id,
        items=items,
    )
    if token:
        clear_preview(token)
    return {"inserted": len(ids), "question_ids": ids}


def list_questions(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    bank_id: int | None,
    type_: str | None,
    tag: str | None,
    difficulty: str | None,
    status: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    repo = QuestionRepository(db)
    if bank_id is not None:
        question_bank_service.resolve_bank(db, class_id=class_id, bank_id=bank_id)
    total = repo.count_scoped(
        class_id,
        type_=type_,
        tag=tag,
        difficulty=difficulty,
        status=status,
        keyword=keyword,
        bank_id=bank_id,
    )
    rows = repo.list_scoped(
        class_id,
        type_=type_,
        tag=tag,
        difficulty=difficulty,
        status=status,
        keyword=keyword,
        offset=(page - 1) * page_size,
        limit=page_size,
        bank_id=bank_id,
    )
    bank_ids = {row.bank_id for row in rows}
    banks = (
        {
            bank.id: bank.name
            for bank in QuestionBankRepository(db).get_many_scoped(
                class_id, list(bank_ids)
            )
        }
        if bank_ids
        else {}
    )
    return page_data(
        [_item(row, banks.get(row.bank_id)) for row in rows],
        total,
        page,
        page_size,
    )


def _merged_question(question: Question, payload: QuestionUpdateRequest) -> dict[str, Any]:
    fields = payload.model_fields_set
    return {
        "type": payload.type if "type" in fields else question.type,
        "stem": payload.stem if "stem" in fields else question.stem,
        "options": payload.options if "options" in fields else question.options_json,
        "answer": payload.answer if "answer" in fields else question.answer_json,
        "analysis": payload.analysis if "analysis" in fields else question.analysis,
        "knowledge_tag": payload.knowledge_tag if "knowledge_tag" in fields else question.knowledge_tag,
        "difficulty": payload.difficulty if "difficulty" in fields else question.difficulty,
    }


def update_question(
    db: Session,
    current: CurrentUser,
    *,
    question_id: int,
    payload: QuestionUpdateRequest,
) -> dict[str, Any]:
    repo = QuestionRepository(db)
    question = repo.get_by_id(question_id)
    if question is None or question.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不存在")
    require_owned_class(db, question.class_id, current.user_id)
    fields = payload.model_fields_set
    if repo.published_reference(question_id, include_closed=False) and not fields.issubset({"analysis"}):
        raise AppException(ErrorCode.PAPER_PUBLISHED_FORBIDDEN, "已发布试卷引用的题目只允许修改解析")

    merged = _merged_question(question, payload)
    item, errors = normalize_item(merged, 0)
    if errors:
        raise AppException(ErrorCode.VALIDATION_ERROR, "题目参数校验失败", data={"errors": errors})
    assert item is not None
    question.type = item["type"]
    question.stem = item["stem"]
    question.options_json = item.get("options")
    question.answer_json = item["answer"]
    question.analysis = item.get("analysis")
    question.knowledge_tag = item.get("knowledge_tag") or "未分类"
    question.difficulty = item.get("difficulty") or "medium"
    if "bank_id" in fields and payload.bank_id is not None:
        bank = question_bank_service.resolve_bank(
            db, class_id=question.class_id, bank_id=payload.bank_id
        )
        question.bank_id = bank.id
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    bank = QuestionBankRepository(db).get_by_id(question.bank_id)
    return _item(question, bank.name if bank else None)


def delete_question(db: Session, current: CurrentUser, *, question_id: int) -> None:
    repo = QuestionRepository(db)
    question = repo.get_by_id(question_id)
    if question is None or question.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不存在")
    require_owned_class(db, question.class_id, current.user_id)
    if repo.published_reference(question_id):
        raise AppException(ErrorCode.PAPER_PUBLISHED_FORBIDDEN, "已发布试卷引用的题目不能删除")
    question.deleted_at = now_naive()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _answer_text(answer: Any) -> str:
    if isinstance(answer, (list, tuple)):
        return "、".join(str(item) for item in answer)
    if isinstance(answer, bool):
        return "正确" if answer else "错误"
    return str(answer)


def get_explain_question(db: Session, current: CurrentUser, *, question_id: int) -> Question:
    """讲评/流式共用的题目与权限校验。"""
    question = QuestionRepository(db).get_by_id(question_id)
    if question is None or question.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不存在")
    if current.role == "teacher":
        require_owned_class(db, question.class_id, current.user_id)
    elif current.class_id != question.class_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    return question


def _explain_prompt(question: Question) -> str:
    return (
        f"题干：{question.stem}\n"
        f"标准答案：{_answer_text(question.answer_json)}\n"
        f"已有解析：{question.analysis or '无'}\n"
        "请用中文给出一段简洁、可教学的讲评，说明考点、正确答案和易错点。"
    )


def _ai_explain(question: Question, *, stream: bool = False) -> str:
    """调用通用池；stream 模式使用更短的单跳超时，总上限由 SSE 侧控制。"""
    if stream:
        explain_settings = _settings.model_copy(
            update={"llm_timeout_seconds": 10, "llm_max_retries": 0}
        )
    else:
        explain_settings = _settings.model_copy(
            update={"llm_timeout_seconds": _settings.llm_explain_timeout_seconds}
        )
    router = build_router(explain_settings)
    result = router.chat(
        [
            {"role": "system", "content": "你是青芽 SproutLearn 的讲评助手，只输出中文讲评。"},
            {"role": "user", "content": _explain_prompt(question)},
        ],
        temperature=0.3,
        max_tokens=256,
    )
    logger.info(
        "explain llm provider={} model={} content_len={}",
        result.provider,
        result.model,
        len(result.content or ""),
    )
    return (result.content or "").strip()


def explain_question(db: Session, current: CurrentUser, *, question_id: int) -> dict[str, Any]:
    """同步讲评：保留原接口/原响应结构，复用同一模板与 AI 逻辑。"""
    question = get_explain_question(db, current, question_id=question_id)
    template = _template_explain(question)
    try:
        content = _ai_explain(question)
        if content:
            return {"explanation": content, "engine": "llm", "degraded": False}
        return {"explanation": template, "engine": "template", "degraded": True}
    except Exception as exc:  # noqa: BLE001 - 讲评绝不 500
        logger.warning("explain template fallback {}: {}", type(exc).__name__, str(exc)[:200])
        return {"explanation": template, "engine": "template", "degraded": True}


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _split_ai(content: str, *, size: int = 320) -> list[str]:
    """按段落/句号切 200–400 字；无标点时按固定长度切。"""
    text = content.strip()
    if not text:
        return []
    if len(text) <= 400:
        return [text]
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if current and len(current) + len(part) > size:
            chunks.append(current.strip())
            current = part
        else:
            current += part
    if current.strip():
        chunks.append(current.strip())
    if not chunks:
        chunks = [text[i : i + size] for i in range(0, len(text), size)]
    return [chunk for chunk in chunks if chunk]


async def stream_explain(question: Question):
    """SSE：先模板全文，再 AI 段落；20s 上限，失败直接 done，不抛流错误。"""
    started = perf_counter()
    template = _template_explain(question)
    yield _sse("meta", {"engine": "template", "model": None})
    yield _sse("delta", {"content": template})
    try:
        content = await asyncio.wait_for(
            asyncio.to_thread(_ai_explain, question, stream=True),
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001 - 流内失败只降级
        logger.warning("explain stream fallback {}: {}", type(exc).__name__, str(exc)[:200])
        content = ""
    if content:
        for chunk in _split_ai(content):
            yield _sse("delta", {"content": chunk})
        yield _sse(
            "done",
            {
                "engine": "llm",
                "degraded": False,
                "elapsed_ms": round((perf_counter() - started) * 1000),
            },
        )
    else:
        yield _sse(
            "done",
            {
                "engine": "template",
                "degraded": True,
                "elapsed_ms": round((perf_counter() - started) * 1000),
            },
        )


def _template_explain(question: Question) -> str:
    if question.analysis and question.analysis.strip():
        return question.analysis.strip()
    return (
        f"本题为{question.type}题，标准答案为：{_answer_text(question.answer_json)}。"
        "请结合题干与标准答案复习对应知识点。"
    )
