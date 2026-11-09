"""班级业务：创建、列表、详情、邀请码查询/重置、学生加入与列表。"""

from __future__ import annotations

from datetime import timedelta

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.class_ import Class
from app.models.class_invite import ClassInvite
from app.models.student import Student
from app.repositories.class_invite_repo import ClassInviteRepository
from app.repositories.class_repo import ClassRepository
from app.repositories.knowledge_doc_repo import KnowledgeDocRepository
from app.repositories.student_repo import StudentRepository
from app.schemas.auth import StudentJoinRequest
from app.schemas.class_ import ClassCreateRequest
from app.services.auth_service import issue_token
from app.services.code_service import generate_class_code, generate_invite_code
from app.utils.response import page_data
from app.utils.security import hash_password
from app.utils.time import fmt_dt, now_naive
from app.utils.validators import validate_name, validate_password, validate_student_no

_settings = get_settings()


def require_owned_class(db: Session, class_id: int, teacher_id: int) -> Class:
    """教师访问班级的统一入口：不存在 40401，非本班 40302。"""
    klass = ClassRepository(db).get_by_id(class_id)
    if klass is None:
        raise AppException(ErrorCode.NOT_FOUND, "班级不存在")
    if klass.teacher_id != teacher_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    return klass


def _counts(db: Session, klass: Class) -> tuple[int, int]:
    student_count = StudentRepository(db).count_by_class(klass.id)
    doc_count = KnowledgeDocRepository(db).count_by_class(klass.id)
    return student_count, doc_count


def _class_list_item(db: Session, klass: Class) -> dict:
    student_count, doc_count = _counts(db, klass)
    return {
        "id": klass.id,
        "class_code": klass.class_code,
        "class_name": klass.class_name,
        "course_name": klass.course_name,
        "student_count": student_count,
        "doc_count": doc_count,
        "status": klass.status,
        "created_at": fmt_dt(klass.created_at),
    }


def create_class(db: Session, current: CurrentUser, payload: ClassCreateRequest) -> dict:
    """创建班级：class_code 与首个 invite_code 同事务生成，碰撞重试 3 次。"""
    class_repo = ClassRepository(db)
    if class_repo.count_by_teacher(current.user_id, status=1) >= _settings.max_classes_per_teacher:
        raise AppException(ErrorCode.CLASS_LIMIT, "班级数量已达上限，请归档旧班后再创建")

    expires_at = None
    if _settings.invite_code_ttl_minutes > 0:
        expires_at = now_naive() + timedelta(minutes=_settings.invite_code_ttl_minutes)

    for attempt in range(1, _settings.code_retry_limit + 1):
        try:
            klass = Class(
                class_code=generate_class_code(),
                teacher_id=current.user_id,
                class_name=payload.class_name,
                course_name=payload.course_name,
                status=1,
            )
            db.add(klass)
            db.flush()
            invite = ClassInvite(
                class_id=klass.id,
                code=generate_invite_code(),
                status=1,
                expires_at=expires_at,
                created_by=current.user_id,
            )
            db.add(invite)
            db.commit()
            db.refresh(klass)
            db.refresh(invite)
            return {
                "id": klass.id,
                "class_code": klass.class_code,
                "class_name": klass.class_name,
                "course_name": klass.course_name,
                "invite_code": invite.code,
                "invite_expires_at": fmt_dt(invite.expires_at),
                "created_at": fmt_dt(klass.created_at),
            }
        except IntegrityError:
            db.rollback()
            logger.warning("班级/邀请码生成碰撞，第 {} 次重试", attempt)
            continue
        except Exception:
            db.rollback()
            raise
    raise AppException(ErrorCode.INTERNAL_ERROR, "班级编号生成失败，请稍后重试")


def list_classes(
    db: Session, current: CurrentUser, *, status: int | None, page: int, page_size: int
) -> dict:
    repo = ClassRepository(db)
    total = repo.count_by_teacher(current.user_id, status=status)
    rows = repo.list_by_teacher(
        current.user_id, status=status, offset=(page - 1) * page_size, limit=page_size
    )
    return page_data([_class_list_item(db, klass) for klass in rows], total, page, page_size)


def get_class_detail(db: Session, current: CurrentUser, class_id: int) -> dict:
    klass = require_owned_class(db, class_id, current.user_id)
    student_count, doc_count = _counts(db, klass)
    invite = ClassInviteRepository(db).get_active(klass.id)
    return {
        "id": klass.id,
        "class_code": klass.class_code,
        "class_name": klass.class_name,
        "course_name": klass.course_name,
        "student_count": student_count,
        "doc_count": doc_count,
        "invite_code": invite.code if invite else None,
        "created_at": fmt_dt(klass.created_at),
    }


def get_invite_code(db: Session, current: CurrentUser, class_id: int) -> dict:
    klass = require_owned_class(db, class_id, current.user_id)
    invite = ClassInviteRepository(db).get_active(klass.id)
    if invite is None:
        raise AppException(ErrorCode.NOT_FOUND, "当前没有有效邀请码，请重置生成")
    return {
        "invite_code": invite.code,
        "status": invite.status,
        "expires_at": fmt_dt(invite.expires_at),
        "created_at": fmt_dt(invite.created_at),
    }


def reset_invite_code(db: Session, current: CurrentUser, class_id: int) -> dict:
    """重置邀请码：class 行锁 + 事务内作废旧码、插入新码；Redis 只做连点限流。"""
    class_repo = ClassRepository(db)
    invite_repo = ClassInviteRepository(db)
    expires_at = None
    if _settings.invite_code_ttl_minutes > 0:
        expires_at = now_naive() + timedelta(minutes=_settings.invite_code_ttl_minutes)

    for attempt in range(1, _settings.code_retry_limit + 1):
        try:
            klass = class_repo.lock_by_id(class_id)
            if klass is None:
                raise AppException(ErrorCode.NOT_FOUND, "班级不存在")
            if klass.teacher_id != current.user_id:
                raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
            invite_repo.deactivate_all(class_id)
            invite = ClassInvite(
                class_id=class_id,
                code=generate_invite_code(),
                status=1,
                expires_at=expires_at,
                created_by=current.user_id,
            )
            db.add(invite)
            db.commit()
            db.refresh(invite)
            return {"invite_code": invite.code, "created_at": fmt_dt(invite.created_at)}
        except IntegrityError:
            db.rollback()
            logger.warning("邀请码生成碰撞，第 {} 次重试", attempt)
            continue
        except AppException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
    raise AppException(ErrorCode.INTERNAL_ERROR, "邀请码生成失败，请稍后重试")


def join_class(db: Session, payload: StudentJoinRequest) -> dict:
    """学生加入：先校验邀请码，再查班内学号；成功即签发会话。"""
    invite_repo = ClassInviteRepository(db)
    class_repo = ClassRepository(db)
    student_repo = StudentRepository(db)

    invite = invite_repo.get_by_code(payload.invite_code)
    if invite is None:
        raise AppException(ErrorCode.INVITE_INVALID, "邀请码无效或已失效")
    if invite.expires_at is not None and invite.expires_at < now_naive():
        raise AppException(ErrorCode.INVITE_INVALID, "邀请码无效或已失效")

    klass = class_repo.get_by_id(invite.class_id)
    if klass is None or klass.status != 1:
        raise AppException(ErrorCode.INVITE_INVALID, "邀请码无效或已失效")

    if student_repo.get_by_class_and_no(klass.id, payload.student_no) is not None:
        raise AppException(ErrorCode.STUDENT_NO_EXISTS, "该班学号已存在")

    student = Student(
        class_id=klass.id,
        student_no=payload.student_no,
        name=payload.name,
        password_hash=hash_password(payload.password),
        xp_total=0,
        level=1,
        status=1,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.STUDENT_NO_EXISTS, "该班学号已存在") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(student)
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
        "class": {
            "id": klass.id,
            "class_code": klass.class_code,
            "class_name": klass.class_name,
            "course_name": klass.course_name,
        },
    }


def list_students(
    db: Session,
    current: CurrentUser,
    class_id: int,
    *,
    keyword: str | None,
    page: int,
    page_size: int,
) -> dict:
    require_owned_class(db, class_id, current.user_id)
    repo = StudentRepository(db)
    total = repo.count_by_class(class_id, keyword=keyword)
    rows = repo.list_by_class(
        class_id, keyword=keyword, offset=(page - 1) * page_size, limit=page_size
    )
    items = [
        {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "level": student.level,
            "xp_total": student.xp_total,
            "qq_bound": binding_id is not None,
            "created_at": fmt_dt(student.created_at),
            "last_login_at": fmt_dt(student.last_login_at),
        }
        for student, binding_id in rows
    ]
    return page_data(items, total, page, page_size)


# 供其他 service 复用的校验函数（避免路由层重复写规则）
def validate_join_payload(payload: StudentJoinRequest) -> None:
    validate_name(payload.name)
    validate_student_no(payload.student_no)
    validate_password(payload.password)
