"""v1.4 密码闭环：自助改密、教师重置学生临时密码、最小操作记录。"""

from __future__ import annotations

import secrets
import string

from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.student import Student
from app.models.teacher import Teacher
from app.redis_client import get_redis_client
from app.schemas.auth import PasswordChangeRequest
from app.services.audit_service import write_audit
from app.services.class_service import require_active_class
from app.utils import cache_keys
from app.utils.security import hash_password, verify_password
from app.utils.time import now_naive

_settings = get_settings()
_UNSAFE = set("O0Il1")


def _redis():
    return get_redis_client()


def _password_change_guard(role: str, user_id: int) -> str:
    key = cache_keys.password_change_fail_key(role, user_id)
    try:
        count = int(_redis().get(key) or 0)
    except Exception:  # noqa: BLE001 - Redis 故障不阻断改密
        return key
    if count >= _settings.password_change_max_failures:
        raise AppException(ErrorCode.RATE_LIMITED, "改密失败次数过多，请 15 分钟后再试")
    return key


def _record_change_failure(key: str) -> None:
    try:
        client = _redis()
        count = client.incr(key)
        if count == 1:
            client.expire(key, _settings.password_change_window_seconds)
        if count > _settings.password_change_max_failures:
            client.expire(key, _settings.password_change_window_seconds)
    except Exception:  # noqa: BLE001
        return


def change_password(
    db: Session,
    current: CurrentUser,
    payload: PasswordChangeRequest,
    *,
    request_id: str | None = None,
) -> None:
    if current.role == "teacher":
        user = db.get(Teacher, current.user_id)
        target_role = "teacher"
    else:
        user = db.get(Student, current.user_id)
        target_role = "student"
    if user is None or user.status != 1:
        raise AppException(ErrorCode.ACCOUNT_DISABLED, "账号已停用")
    key = _password_change_guard(current.role, current.user_id)
    if not verify_password(payload.current_password, user.password_hash):
        _record_change_failure(key)
        write_audit(
            db,
            actor_role=current.role,
            actor_id=current.user_id,
            target_role=target_role,
            target_id=current.user_id,
            class_id=current.class_id,
            action="password_change",
            result="failed",
            request_id=request_id,
        )
        db.commit()
        raise AppException(ErrorCode.VALIDATION_ERROR, "当前密码错误", http_status=400)
    if verify_password(payload.new_password, user.password_hash):
        raise AppException(ErrorCode.VALIDATION_ERROR, "新密码不能与当前密码相同", http_status=400)
    user.password_hash = hash_password(payload.new_password)
    user.auth_version = int(user.auth_version or 1) + 1
    user.must_change_password = 0
    write_audit(
        db,
        actor_role=current.role,
        actor_id=current.user_id,
        target_role=target_role,
        target_id=current.user_id,
        class_id=current.class_id,
        action="password_change",
        result="success",
        request_id=request_id,
    )
    db.commit()
    try:
        _redis().delete(key)
    except Exception:  # noqa: BLE001 - Redis 故障不阻断已完成的改密
        return


def _generate_temporary_password() -> str:
    alphabet = "".join(ch for ch in string.ascii_letters if ch not in _UNSAFE)
    digits = "".join(ch for ch in string.digits if ch not in _UNSAFE)
    while True:
        raw = (
            secrets.choice(alphabet)
            + secrets.choice(digits)
            + "".join(secrets.choice(alphabet + digits) for _ in range(8))
        )
        # 统一规则：8–32 位且同时含字母/数字；打乱避免固定位置
        chars = list(raw)
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        if any(ch.isalpha() for ch in candidate) and any(ch.isdigit() for ch in candidate):
            return candidate


def reset_student_password(
    db: Session,
    current: CurrentUser,
    *,
    class_id: int,
    student_id: int,
    request_id: str | None = None,
) -> dict:
    require_active_class(db, class_id, current.user_id)
    student = db.get(Student, student_id)
    if student is None or student.class_id != class_id:
        # 跨班/不存在统一 40302，不泄露目标存在性；失败也留最小记录
        write_audit(
            db,
            actor_role="teacher",
            actor_id=current.user_id,
            target_role="student",
            target_id=student_id,
            class_id=class_id,
            action="password_reset",
            result="failed",
            request_id=request_id,
        )
        db.commit()
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权操作该学生")
    try:
        hour = now_naive().strftime("%Y%m%d%H")
        day = now_naive().strftime("%Y-%m-%d")
        student_key = cache_keys.password_reset_student_key(student_id, hour)
        teacher_key = cache_keys.password_reset_teacher_key(current.user_id, day)
        client = _redis()
        student_count = client.incr(student_key)
        if student_count == 1:
            client.expire(student_key, 3600)
        teacher_count = client.incr(teacher_key)
        if teacher_count == 1:
            client.expire(teacher_key, 86400)
        if student_count > _settings.password_reset_student_hourly:
            write_audit(
                db, actor_role="teacher", actor_id=current.user_id, target_role="student",
                target_id=student.id, class_id=class_id, action="password_reset",
                result="failed", request_id=request_id,
            )
            db.commit()
            raise AppException(ErrorCode.RATE_LIMITED, "该学生重置过于频繁，请稍后再试")
        if teacher_count > _settings.password_reset_teacher_daily:
            write_audit(
                db, actor_role="teacher", actor_id=current.user_id, target_role="student",
                target_id=student.id, class_id=class_id, action="password_reset",
                result="failed", request_id=request_id,
            )
            db.commit()
            raise AppException(ErrorCode.RATE_LIMITED, "今日重置次数已用完")
    except AppException:
        raise
    except Exception:  # noqa: BLE001, S110 - Redis 故障时按设计放行重置
        pass

    temporary = _generate_temporary_password()
    student.password_hash = hash_password(temporary)
    student.auth_version = int(student.auth_version or 1) + 1
    student.must_change_password = 1
    write_audit(
        db,
        actor_role="teacher",
        actor_id=current.user_id,
        target_role="student",
        target_id=student.id,
        class_id=class_id,
        action="password_reset",
        result="success",
        request_id=request_id,
    )
    db.commit()
    return {"student_id": student.id, "temporary_password": temporary}
