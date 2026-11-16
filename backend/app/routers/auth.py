"""鉴权路由：教师注册、登录、登出、当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, get_current_user, get_token_claims_optional
from app.database import get_db
from app.middleware import rate_limit
from app.middleware.rate_limit import client_ip
from app.schemas.auth import LoginRequest, TeacherRegisterRequest
from app.services import auth_service
from app.utils import cache_keys
from app.utils.response import success

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()


@router.post("/teacher/register")
def register_teacher(payload: TeacherRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """API-01 教师注册：限流 → 唯一校验 → 建号 → 签发会话。"""
    rate_limit.enforce(
        cache_keys.rate_login_key(client_ip(request)), _settings.rate_limit_login
    )
    return success(auth_service.register_teacher(db, payload))


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """API-02 教师/学生登录：共用入口，按 role 分流。"""
    rate_limit.enforce(
        cache_keys.rate_login_key(client_ip(request)), _settings.rate_limit_login
    )
    return success(auth_service.login(db, payload))


@router.post("/logout")
def logout(payload: dict | None = Depends(get_token_claims_optional)):
    """API-03 登出：合法 token 删会话/写黑名单；无 token/坏 token/重复也 200。"""
    if payload:
        auth_service.logout_claims(payload)
    return success(None)


@router.get("/me")
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """API-04 当前用户信息（教师/学生字段不同）。"""
    return success(auth_service.current_user_info(db, current))
