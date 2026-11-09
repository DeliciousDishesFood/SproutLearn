"""账号与鉴权业务：教师注册/登录、学生登录、当前用户、登出。"""

from __future__ import annotations

import json

import redis
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.middleware import rate_limit
from app.models.class_ import Class
from app.models.student import Student
from app.models.teacher import Teacher
from app.repositories.class_repo import ClassRepository
from app.repositories.qq_binding_repo import QqBindingRepository
from app.repositories.student_repo import StudentRepository
from app.repositories.teacher_repo import TeacherRepository
from app.schemas.auth import LoginRequest, TeacherRegisterRequest
from app.services.code_service import generate_class_code  # noqa: F401 - 保持编码服务统一入口
from app.utils import cache_keys
from app.utils.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    remaining_ttl,
    verify_password,
)
from app.utils.time import fmt_dt, now

_settings = get_settings()


def _redis() -> redis.Redis:
    from app.redis_client import get_redis_client

    return get_redis_client()


def issue_token(*, user_id: int, role: str, class_id: int | None) -> str:
    """签发 JWT 并写入 Redis 会话（TTL = SESSION_IDLE_MINUTES）。"""
    token, jti, _exp = create_access_token(user_id=user_id, role=role, class_id=class_id)
    payload = json.dumps({"user_id": user_id, "role": role, "class_id": class_id})
    try:
        _redis().set(cache_keys.session_key(jti), payload, ex=_settings.session_idle_seconds)
    except redis.RedisError as exc:
        logger.error("写入会话失败: {}", exc)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
    return token


def register_teacher(db: Session, payload: TeacherRegisterRequest) -> dict:
    """教师注册：账号大小写不敏感唯一，注册成功即签发会话。"""
    repo = TeacherRepository(db)
    if repo.get_by_account(payload.account):
        raise AppException(ErrorCode.ACCOUNT_EXISTS, "账号已存在")

    teacher = Teacher(
        account=payload.account,
        password_hash=hash_password(payload.password),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        status=1,
        last_login_at=now(),
    )
    db.add(teacher)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.ACCOUNT_EXISTS, "账号已存在") from exc
    except Exception:
        db.rollback()
        raise

    db.refresh(teacher)
    token = issue_token(user_id=teacher.id, role="teacher", class_id=None)
    return {
        "token": token,
        "user": {
            "id": teacher.id,
            "role": "teacher",
            "name": teacher.name,
            "account": teacher.account,
        },
    }


def _login_teacher(db: Session, payload: LoginRequest) -> dict:
    repo = TeacherRepository(db)
    account = (payload.account or "").lower()
    fail_key = cache_keys.login_fail_key(account)
    if rate_limit.is_failure_blocked(fail_key, _settings.rate_limit_login):
        raise AppException(ErrorCode.RATE_LIMITED, "请求过于频繁，请稍后再试")

    teacher = repo.get_by_account(account)
    if teacher is None:
        burn_password_check(payload.password)
        rate_limit.record_failure(fail_key, _settings.rate_limit_login)
        raise AppException(ErrorCode.BAD_CREDENTIALS, "账号或密码错误")

    if not verify_password(payload.password, teacher.password_hash) or teacher.status != 1:
        rate_limit.record_failure(fail_key, _settings.rate_limit_login)
        raise AppException(ErrorCode.BAD_CREDENTIALS, "账号或密码错误")

    rate_limit.clear_failure(fail_key)
    teacher.last_login_at = now()
    db.commit()
    token = issue_token(user_id=teacher.id, role="teacher", class_id=None)
    return {
        "token": token,
        "user": {
            "id": teacher.id,
            "role": "teacher",
            "name": teacher.name,
            "account": teacher.account,
        },
    }


def _login_student(db: Session, payload: LoginRequest) -> dict:
    class_repo = ClassRepository(db)
    student_repo = StudentRepository(db)
    class_code = (payload.class_code or "").upper()
    student_no = (payload.student_no or "").strip()
    fail_key = cache_keys.login_fail_key(f"{class_code}:{student_no}")
    if rate_limit.is_failure_blocked(fail_key, _settings.rate_limit_login):
        raise AppException(ErrorCode.RATE_LIMITED, "请求过于频繁，请稍后再试")

    klass = class_repo.get_by_code(class_code)
    student = None
    if klass is not None and klass.status == 1:
        student = student_repo.get_by_class_and_no(klass.id, student_no)

    if student is None:
        burn_password_check(payload.password)
        rate_limit.record_failure(fail_key, _settings.rate_limit_login)
        raise AppException(ErrorCode.BAD_CREDENTIALS, "账号或密码错误")

    if not verify_password(payload.password, student.password_hash) or student.status != 1:
        rate_limit.record_failure(fail_key, _settings.rate_limit_login)
        raise AppException(ErrorCode.BAD_CREDENTIALS, "账号或密码错误")

    rate_limit.clear_failure(fail_key)
    student.last_login_at = now()
    db.commit()
    token = issue_token(user_id=student.id, role="student", class_id=klass.id)
    return {
        "token": token,
        "user": {
            "id": student.id,
            "role": "student",
            "name": student.name,
            "class_id": klass.id,
            "class_code": klass.class_code,
            "student_no": student.student_no,
        },
    }


def login(db: Session, payload: LoginRequest) -> dict:
    """教师/学生共用登录入口，按 role 分流。"""
    if payload.role == "teacher":
        return _login_teacher(db, payload)
    return _login_student(db, payload)


def current_user_info(db: Session, current: CurrentUser) -> dict:
    """API-04 当前用户信息。"""
    if current.role == "teacher":
        teacher = TeacherRepository(db).get(current.user_id)
        if teacher is None or teacher.status != 1:
            raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
        return {
            "id": teacher.id,
            "role": "teacher",
            "name": teacher.name,
            "account": teacher.account,
            "created_at": fmt_dt(teacher.created_at),
        }

    student = db.get(Student, current.user_id)
    if student is None or student.status != 1:
        raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
    klass = db.get(Class, student.class_id)
    if klass is None:
        raise AppException(ErrorCode.SESSION_EXPIRED, "登录已过期")
    binding = QqBindingRepository(db).get_active_by_student(student.id)
    return {
        "id": student.id,
        "role": "student",
        "name": student.name,
        "class_id": student.class_id,
        "class_code": klass.class_code,
        "class_name": klass.class_name,
        "student_no": student.student_no,
        "level": student.level,
        "xp_total": student.xp_total,
        "qq_bound": binding is not None,
    }


def logout(current: CurrentUser) -> None:
    """删除会话并写黑名单；重复登出不报错（幂等）。"""
    _logout_jti(current.jti, current.exp)


def logout_claims(payload: dict) -> None:
    """幂等登出入口：只依赖已验证的 JWT claims，不要求会话仍存在。"""
    _logout_jti(str(payload.get("jti")), int(payload.get("exp", 0)))


def _logout_jti(jti: str, exp: int) -> None:
    ttl = remaining_ttl(exp)
    try:
        client = _redis()
        client.delete(cache_keys.session_key(jti))
        if ttl > 0:
            client.set(cache_keys.jwt_blacklist_key(jti), "1", ex=ttl)
    except redis.RedisError as exc:
        logger.error("登出时 Redis 不可用: {}", exc)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
