"""M2B 题库业务：导入预览/提交、筛选、编辑、软删除、讲评。"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.question import Question
from app.repositories.question_repo import QuestionRepository
from app.schemas.question import QuestionUpdateRequest
from app.services.class_service import require_owned_class
from app.services.question_import import (
    clear_preview,
    commit_questions,
    load_preview,
    normalize_item,
    parse_import,
    store_preview,
)
from app.services.llm.router import build_router
from app.utils.response import page_data
from app.utils.time import fmt_dt, now_naive

_settings = get_settings()


def _item(question: Question) -> dict[str, Any]:
    return {
        "id": question.id,
        "class_id": question.class_id,
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
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    parsed = parse_import(content, filename)
    token = store_preview(class_id=class_id, teacher_id=current.user_id, parsed=parsed)
    return {
        "token": token,
        "total": parsed["total"],
        "valid_count": len(parsed["items"]),
        "error_count": len(parsed["errors"]),
        "errors": parsed["errors"],
        "preview": parsed["items"],
    }


def commit_import(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    token: str | None,
    content: bytes | None,
    filename: str | None,
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    errors: list[dict[str, Any]] = []
    if token:
        payload = load_preview(token, class_id=class_id, teacher_id=current.user_id)
        items = payload.get("items") or []
        errors = payload.get("errors") or []
    else:
        if content is None:
            raise AppException(ErrorCode.VALIDATION_ERROR, "必须提供 token 或导入文件")
        parsed = parse_import(content, filename or "")
        items = parsed["items"]
        errors = parsed["errors"]
    if errors:
        raise AppException(ErrorCode.IMPORT_FORMAT_ERROR, "导入存在格式错误，请修正后重试", data={"errors": errors})
    ids = commit_questions(db, class_id=class_id, teacher_id=current.user_id, items=items)
    if token:
        clear_preview(token)
    return {"inserted": len(ids), "question_ids": ids}


def list_questions(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
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
    total = repo.count_scoped(
        class_id,
        type_=type_,
        tag=tag,
        difficulty=difficulty,
        status=status,
        keyword=keyword,
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
    )
    return page_data([_item(row) for row in rows], total, page, page_size)


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
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    return _item(question)


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


def explain_question(db: Session, current: CurrentUser, *, question_id: int) -> dict[str, Any]:
    question = QuestionRepository(db).get_by_id(question_id)
    if question is None or question.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不存在")
    if current.role == "teacher":
        require_owned_class(db, question.class_id, current.user_id)
    elif current.class_id != question.class_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")

    prompt = (
        f"题干：{question.stem}\n"
        f"标准答案：{_answer_text(question.answer_json)}\n"
        f"已有解析：{question.analysis or '无'}\n"
        "请用中文给出一段简洁、可教学的讲评，说明考点、正确答案和易错点。"
    )
    template = _template_explain(question)
    try:
        explain_settings = _settings.model_copy(
            update={"llm_timeout_seconds": _settings.llm_explain_timeout_seconds}
        )
        router = build_router(explain_settings)
        result = router.chat(
            [
                {"role": "system", "content": "你是青芽 SproutLearn 的讲评助手，只输出中文讲评。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=256,
        )
        logger.info("explain llm provider={} model={} content_len={}", result.provider, result.model, len(result.content or ""))
        if result.content.strip():
            return {"explanation": result.content.strip(), "engine": "llm", "degraded": False}
        return {"explanation": template, "engine": "template", "degraded": True}
    except Exception as exc:  # noqa: BLE001 - 讲评绝不 500
        logger.warning("explain template fallback {}: {}", type(exc).__name__, str(exc)[:200])
        return {"explanation": template, "engine": "template", "degraded": True}


def _template_explain(question: Question) -> str:
    if question.analysis and question.analysis.strip():
        return question.analysis.strip()
    return (
        f"本题为{question.type}题，标准答案为：{_answer_text(question.answer_json)}。"
        "请结合题干与标准答案复习对应知识点。"
    )
