"""QQ 绑定业务：一次性绑定码、机器人回调、改绑与解绑。"""

from __future__ import annotations

import json
from datetime import timedelta

import redis
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.qq_binding import QqBinding
from app.repositories.class_repo import ClassRepository
from app.repositories.qq_binding_repo import QqBindingRepository
from app.repositories.student_repo import StudentRepository
from app.schemas.binding import QqBindCallbackRequest
from app.services.code_service import generate_bind_code
from app.utils import cache_keys
from app.utils.time import fmt_dt, now, now_naive

_settings = get_settings()


def _redis() -> redis.Redis:
    from app.redis_client import get_redis_client

    return get_redis_client()


def generate_qq_code(current: CurrentUser) -> dict:
    """生成 8 位一次性绑定码；重复生成时旧码立即失效。"""
    client = _redis()
    student_id = current.user_id
    student_key = cache_keys.qq_bind_student_key(student_id)
    ttl = _settings.bind_code_ttl_seconds
    try:
        old_code = client.get(student_key)
        if old_code:
            client.delete(cache_keys.qq_bind_code_key(old_code))

        payload = json.dumps({"student_id": student_id, "class_id": current.class_id})
        code = ""
        for _ in range(_settings.code_retry_limit):
            code = generate_bind_code()
            if client.set(cache_keys.qq_bind_code_key(code), payload, ex=ttl, nx=True):
                break
        else:
            raise AppException(ErrorCode.INTERNAL_ERROR, "绑定码生成失败，请重试")
        client.set(student_key, code, ex=ttl)
    except redis.RedisError as exc:
        logger.error("生成绑定码时 Redis 不可用: {}", exc)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc

    expires_at = now().replace(microsecond=0) + timedelta(seconds=ttl)
    return {"code": code, "expires_in": ttl, "expires_at": fmt_dt(expires_at)}


def bind_qq(db: Session, payload: QqBindCallbackRequest) -> dict:
    """机器人回调：尝试计数 → 原子消费码 → 冲突校验 → 改绑/插入。"""
    client = _redis()
    attempt_key = cache_keys.qq_bind_attempt_key(payload.qq_openid)
    try:
        attempts = client.incr(attempt_key)
        if attempts == 1:
            client.expire(attempt_key, _settings.bind_attempt_ttl_seconds)
        if attempts > _settings.bind_max_attempts:
            raise AppException(ErrorCode.RATE_LIMITED, "绑定尝试过于频繁，请稍后再试")
    except redis.RedisError as exc:
        logger.error("绑定尝试计数 Redis 不可用: {}", exc)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc

    try:
        raw = client.getdel(cache_keys.qq_bind_code_key(payload.code))
    except redis.RedisError as exc:
        logger.error("消费绑定码 Redis 不可用: {}", exc)
        raise AppException(ErrorCode.DEPENDENCY_UNAVAILABLE, "依赖服务不可用") from exc
    if not raw:
        raise AppException(ErrorCode.BIND_CODE_INVALID, "绑定码无效或已过期")

    try:
        code_data = json.loads(raw)
        student_id = int(code_data["student_id"])
        class_id = int(code_data["class_id"])
    except (TypeError, ValueError, KeyError) as exc:
        raise AppException(ErrorCode.BIND_CODE_INVALID, "绑定码无效或已过期") from exc

    student = StudentRepository(db).get_by_id_scoped(student_id, class_id)
    klass = ClassRepository(db).get_by_id(class_id)
    if student is None or student.status != 1 or klass is None or klass.status != 1:
        raise AppException(ErrorCode.BIND_CODE_INVALID, "绑定码无效或已过期")

    binding_repo = QqBindingRepository(db)
    existing_openid = binding_repo.get_active_by_openid(payload.qq_openid)
    if existing_openid is not None:
        if existing_openid.student_id != student.id:
            raise AppException(ErrorCode.QQ_ALREADY_BOUND, "该 QQ 已绑定其他学号")
        return {
            "student_id": student.id,
            "student_no": student.student_no,
            "class_id": class_id,
            "class_code": klass.class_code,
            "bound_at": fmt_dt(existing_openid.bound_at),
        }

    # 改绑：旧有效行先置 0，生成列变 NULL，再插入新行
    binding_repo.deactivate_by_student(student.id)
    binding = QqBinding(
        class_id=class_id,
        student_id=student.id,
        qq_openid=payload.qq_openid,
        status=1,
        bound_at=now_naive(),
    )
    db.add(binding)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.QQ_ALREADY_BOUND, "该 QQ 已绑定其他学号") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(binding)
    return {
        "student_id": student.id,
        "student_no": student.student_no,
        "class_id": class_id,
        "class_code": klass.class_code,
        "bound_at": fmt_dt(binding.bound_at),
    }


def unbind_qq(db: Session, current: CurrentUser) -> None:
    """解绑：status 置 0 保留历史，不物理删除。"""
    binding = QqBindingRepository(db).get_active_by_student(current.user_id)
    if binding is None:
        raise AppException(ErrorCode.NOT_FOUND, "当前没有 QQ 绑定")
    binding.status = 0
    db.commit()
