"""知识库路由：批量上传、列表、详情、切片预览、删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, get_db, require_teacher
from app.exceptions import AppException, ErrorCode
from app.middleware import rate_limit
from app.services import knowledge_service
from app.utils import cache_keys
from app.utils.response import success

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
_settings = get_settings()


@router.post("/documents")
async def upload_documents(
    class_id: int = Form(...),
    course_name: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-12 批量上传：请求级错误 40001，单文件问题进 fail_list。"""
    rate_limit.enforce(
        cache_keys.rate_upload_key(current.user_id), _settings.rate_limit_upload
    )

    if not files or len(files) == 0:
        raise AppException(ErrorCode.VALIDATION_ERROR, "至少上传 1 个文件")
    if len(files) > _settings.max_files_per_request:
        raise AppException(
            ErrorCode.VALIDATION_ERROR,
            f"单次最多上传 {_settings.max_files_per_request} 个文件",
        )

    items: list[tuple[str, bytes]] = []
    total_bytes = 0
    for upload in files:
        content = await upload.read()
        total_bytes += len(content)
        items.append((upload.filename or "unnamed", content))
        await upload.close()

    if total_bytes > _settings.max_total_upload_bytes:
        raise AppException(
            ErrorCode.VALIDATION_ERROR,
            f"单次上传总大小超过 {_settings.max_total_upload_mb}MB 上限",
        )

    return success(
        knowledge_service.upload_documents(
            db,
            current,
            class_id=class_id,
            course_name=course_name,
            files=items,
        )
    )


@router.get("/documents")
def list_documents(
    class_id: int = Query(..., ge=1),
    status: int | None = Query(default=None, ge=0, le=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_settings.pagination_default_size, ge=1, le=_settings.pagination_max_size),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-13 文档列表。"""
    return success(
        knowledge_service.list_documents(
            db,
            current,
            class_id=class_id,
            status=status,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-14 文档详情。"""
    return success(knowledge_service.get_document(db, current, doc_id))


@router.get("/documents/{doc_id}/chunks")
def list_chunks(
    doc_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_settings.pagination_default_size, ge=1, le=_settings.pagination_max_size),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-15 切片预览：返回全文，前端负责折叠。"""
    return success(
        knowledge_service.list_chunks(
            db, current, doc_id, page=page, page_size=page_size
        )
    )


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-16 删除文档：先删库，提交后删磁盘文件。"""
    knowledge_service.delete_document(db, current, doc_id)
    return success(None)
