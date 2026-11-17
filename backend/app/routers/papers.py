"""M2B/M2C 试卷路由：组卷、详情、发布/撤回、学生开卷、列表。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_current_user, get_db, require_student, require_teacher
from app.schemas.paper import PaperCreateRequest, PaperUpdateRequest
from app.services import paper_service
from app.utils.response import success

router = APIRouter(tags=["papers"])
PAGE_SIZE = Query(default=20, ge=1, le=100)


@router.post("/classes/{class_id}/papers")
def create_paper(
    class_id: int,
    payload: PaperCreateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-06 固定/随机组卷。"""
    return success(paper_service.create_paper(db, current, class_id=class_id, payload=payload))


@router.get("/classes/{class_id}/papers")
def list_class_papers(
    class_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = PAGE_SIZE,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API-M2C-03 班级试卷列表：教师全部，学生仅 published。"""
    return success(
        paper_service.list_class_papers(
            db,
            current,
            class_id=class_id,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-07 教师视角试卷详情。"""
    return success(paper_service.paper_detail(db, current, paper_id=paper_id))


@router.patch("/papers/{paper_id}")
def update_paper(
    paper_id: int,
    payload: PaperUpdateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2C-01 修改草稿/已撤回试卷的 title/duration_minutes/blank_mode。"""
    return success(
        paper_service.update_paper(db, current, paper_id=paper_id, payload=payload)
    )


@router.patch("/papers/{paper_id}/withdraw")
def withdraw_paper(
    paper_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API-M2C-02 仅创建者撤回 published → closed。"""
    return success(paper_service.withdraw_paper(db, current, paper_id=paper_id))


@router.post("/papers/{paper_id}/group-notice/retry")
@router.post("/papers/{paper_id}/notify")
def retry_group_notice(
    paper_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """教师显式重试主动作业通知；不重发历史批量、不改试卷状态。"""
    return success(paper_service.retry_group_notice(db, current, paper_id=paper_id))


@router.post("/papers/{paper_id}/publish")
def publish_paper(
    paper_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-08 发布试卷（draft/closed → published）。"""
    return success(paper_service.publish_paper(db, current, paper_id=paper_id))


@router.get("/papers/{paper_id}/attempts")
def list_paper_attempts(
    paper_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = PAGE_SIZE,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2C-04 某卷成绩列表（仅教师）。"""
    return success(
        paper_service.list_paper_attempts(
            db,
            current,
            paper_id=paper_id,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/papers/{paper_id}/attempts")
def start_attempt(
    paper_id: int,
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M2-09 学生开卷；重复调用返回原 attempt（幂等）。"""
    return success(paper_service.start_attempt(db, current, paper_id=paper_id))
