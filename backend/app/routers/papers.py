"""M2B 试卷路由：组卷、详情、发布、学生开卷。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_db, require_student, require_teacher
from app.schemas.paper import PaperCreateRequest
from app.services import paper_service
from app.utils.response import success

router = APIRouter(tags=["papers"])


@router.post("/classes/{class_id}/papers")
def create_paper(
    class_id: int,
    payload: PaperCreateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-06 固定/随机组卷。"""
    return success(paper_service.create_paper(db, current, class_id=class_id, payload=payload))


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-07 教师视角试卷详情。"""
    return success(paper_service.paper_detail(db, current, paper_id=paper_id))


@router.post("/papers/{paper_id}/publish")
def publish_paper(
    paper_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-08 发布试卷（校验题量/分值/已删除题）。"""
    return success(paper_service.publish_paper(db, current, paper_id=paper_id))


@router.post("/papers/{paper_id}/attempts")
def start_attempt(
    paper_id: int,
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M2-09 学生开卷；重复调用返回原 attempt（幂等）。"""
    return success(paper_service.start_attempt(db, current, paper_id=paper_id))
