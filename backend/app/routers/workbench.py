"""M3.2 工作台、成长、班级开关与金句路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_db, require_student, require_teacher
from app.schemas.workbench import XpConfigUpdateRequest
from app.services import quote_service, workbench_service
from app.utils.response import success

router = APIRouter(tags=["workbench"])


@router.get("/me/workbench")
def me_workbench(
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """M3.2-01 学生工作台。"""
    return success(workbench_service.student_workbench(db, current))


@router.get("/classes/{class_id}/workbench")
def class_workbench(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.2-02 教师班级工作台。"""
    return success(workbench_service.teacher_workbench(db, current, class_id=class_id))


@router.get("/me/activity")
def me_activity(
    weeks: int = Query(default=12, ge=1, le=52),
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """M3.2-03 学生每日答题/经验。"""
    return success(workbench_service.student_activity(db, current, weeks=weeks))


@router.get("/classes/{class_id}/activity")
def class_activity(
    class_id: int,
    weeks: int = Query(default=12, ge=1, le=52),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.2-04 班级每日答题/活跃人数。"""
    return success(
        workbench_service.class_activity(
            db, current, class_id=class_id, weeks=weeks
        )
    )


@router.get("/me/growth")
def me_growth(
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """M3.2-05 等级进度、经验流水、热力图。"""
    return success(workbench_service.student_growth(db, current))


@router.get("/classes/{class_id}/xp-config")
def get_xp_config(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.2-06 班级经验开关。"""
    return success(workbench_service.xp_config(db, current, class_id=class_id))


@router.patch("/classes/{class_id}/xp-config")
def update_xp_config(
    class_id: int,
    payload: XpConfigUpdateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.2-06 逐项更新班级经验开关。"""
    items = [item.model_dump() for item in payload.items]
    return success(
        workbench_service.update_xp_config(
            db, current, class_id=class_id, items=items
        )
    )


@router.get("/quotes/random")
def random_quote(
    type: str | None = Query(default=None, max_length=32),
):
    """M3.2-07 金句代理：shiora → hitokoto → 本地池，始终 200。"""
    return success(quote_service.get_random_quote(type))
