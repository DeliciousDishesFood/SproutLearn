"""M2B 题库路由：导入预览/提交、列表、编辑、软删除、讲评。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, get_current_user, get_db, require_teacher
from app.schemas.question import QuestionUpdateRequest
from app.services import question_service
from app.utils.response import success

router = APIRouter(tags=["questions"])
_settings = get_settings()


@router.post("/classes/{class_id}/questions/import/preview")
async def preview_import(
    class_id: int,
    file: UploadFile = File(...),
    bank_id: int | None = Form(default=None),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-01 上传 JSON/XLSX/XLS/CSV 预览，不落库。"""
    content = await file.read()
    await file.close()
    return success(
        question_service.preview_import(
            db,
            current,
            class_id=class_id,
            content=content,
            filename=file.filename or "",
            bank_id=bank_id,
        )
    )


@router.post("/classes/{class_id}/questions/import/commit")
async def commit_import(
    class_id: int,
    request: Request,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-02 提交预览 token 或直接上传文件，落库 draft。"""
    token: str | None = None
    content: bytes | None = None
    filename: str | None = None
    rows = None
    bank_id = None
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        if isinstance(body, dict):
            token = body.get("token")
            rows = body.get("rows")
            bank_id = body.get("bank_id")
    else:
        form = await request.form()
        raw_token = form.get("token")
        token = str(raw_token) if raw_token else None
        raw_bank = form.get("bank_id")
        bank_id = int(raw_bank) if raw_bank not in (None, "") else None
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            content = await upload.read()
            filename = getattr(upload, "filename", "") or ""
            await upload.close()
    return success(
        question_service.commit_import(
            db,
            current,
            class_id=class_id,
            token=token,
            content=content,
            filename=filename,
            rows=rows,
            bank_id=bank_id,
        )
    )


@router.get("/classes/{class_id}/questions")
def list_questions(
    class_id: int,
    bank_id: int | None = Query(default=None, ge=1),
    type_: str | None = Query(default=None, alias="type"),
    tag: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_settings.pagination_default_size, ge=1, le=_settings.pagination_max_size),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-03 题库筛选列表（M3.1 增加 bank_id）。"""
    return success(
        question_service.list_questions(
            db,
            current,
            class_id=class_id,
            bank_id=bank_id,
            type_=type_,
            tag=tag,
            difficulty=difficulty,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    )


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    payload: QuestionUpdateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-04 编辑题目；已发布试卷引用时仅允许 analysis。"""
    return success(question_service.update_question(db, current, question_id=question_id, payload=payload))


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-05 软删除题目；被已发布试卷引用则 40909。"""
    question_service.delete_question(db, current, question_id=question_id)
    return success(None)


@router.post("/questions/{question_id}/explain")
def explain_question(
    question_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API-M2-14 按需讲评：LLM 可用走模型，否则模板，绝不 500。"""
    return success(question_service.explain_question(db, current, question_id=question_id))


@router.post("/questions/{question_id}/explain/stream")
async def explain_question_stream(
    question_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """M2.5 伪流式讲评：200ms 内先模板全文，再 AI 段落，失败不断流。"""
    question = question_service.get_explain_question(db, current, question_id=question_id)
    return StreamingResponse(
        question_service.stream_explain(question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
