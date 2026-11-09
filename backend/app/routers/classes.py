"""班级路由：创建/列表/详情/邀请码/学生列表/加入。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, get_db, require_teacher
from app.middleware import rate_limit
from app.middleware.rate_limit import client_ip
from app.schemas.auth import StudentJoinRequest
from app.schemas.class_ import ClassCreateRequest
from app.services import class_service
from app.utils import cache_keys
from app.utils.response import success

router = APIRouter(prefix="/classes", tags=["classes"])
_settings = get_settings()


@router.post("")
def create_class(
    payload: ClassCreateRequest,
    request: Request,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-05 创建班级：class_code + 首个 invite_code 同事务生成。"""
    rate_limit.enforce(
        cache_keys.rate_login_key(client_ip(request)), _settings.rate_limit_login
    )
    return success(class_service.create_class(db, current, payload))


@router.get("")
def list_classes(
    status: int | None = Query(default=None, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_settings.pagination_default_size, ge=1, le=_settings.pagination_max_size),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-06 我的班级列表（仅 teacher_id = 当前用户）。"""
    return success(
        class_service.list_classes(
            db, current, status=status, page=page, page_size=page_size
        )
    )


@router.post("/join")
def join_class(payload: StudentJoinRequest, request: Request, db: Session = Depends(get_db)):
    """API-11 学生加入班级：邀请码 + 学号 + 密码，成功即登录。"""
    rate_limit.enforce(cache_keys.rate_join_key(client_ip(request)), _settings.rate_limit_join)
    return success(class_service.join_class(db, payload))


@router.get("/{class_id}")
def get_class_detail(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-07 班级详情（仅本班）。"""
    return success(class_service.get_class_detail(db, current, class_id))


@router.get("/{class_id}/invite-code")
def get_invite_code(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-08 查询当前有效邀请码。"""
    return success(class_service.get_invite_code(db, current, class_id))


@router.post("/{class_id}/invite-code/reset")
def reset_invite_code(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-09 重置邀请码：class 行锁 + 连点限流。"""
    rate_limit.enforce(
        cache_keys.rate_invite_reset_key(class_id), _settings.rate_limit_invite_reset
    )
    return success(class_service.reset_invite_code(db, current, class_id))


@router.get("/{class_id}/students")
def list_students(
    class_id: int,
    keyword: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=_settings.pagination_default_size, ge=1, le=_settings.pagination_max_size),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-10 学生列表：学号升序，qq_bound 由绑定表派生。"""
    return success(
        class_service.list_students(
            db,
            current,
            class_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    )
