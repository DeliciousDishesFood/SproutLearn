"""M3.4 通知中心：站内信写入、分页、已读与公告。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.notification import Notification
from app.models.student import Student
from app.services.class_service import require_owned_class
from app.utils.response import page_data
from app.utils.time import fmt_dt, now_naive


def add(
    db: Session,
    *,
    recipient_role: str,
    recipient_id: int,
    class_id: int,
    type: str,
    title: str,
    body: str,
    target_path: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Notification:
    item = Notification(
        recipient_role=recipient_role,
        recipient_id=recipient_id,
        class_id=class_id,
        type=type,
        title=title[:120],
        body=body[:500],
        target_path=target_path,
        payload_json=payload,
        is_read=0,
        created_at=now_naive(),
    )
    db.add(item)
    return item


def add_for_class(
    db: Session,
    *,
    class_id: int,
    type: str,
    title: str,
    body: str,
    target_path: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    students = (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.status == 1)
        .all()
    )
    for student in students:
        add(
            db,
            recipient_role="student",
            recipient_id=student.id,
            class_id=class_id,
            type=type,
            title=title,
            body=body,
            target_path=target_path,
            payload=payload,
        )
    return len(students)


def _item(row: Notification) -> dict[str, Any]:
    return {
        "id": row.id,
        "recipient_role": row.recipient_role,
        "recipient_id": row.recipient_id,
        "class_id": row.class_id,
        "type": row.type,
        "title": row.title,
        "body": row.body,
        "target_path": row.target_path,
        "payload": row.payload_json,
        "is_read": bool(row.is_read),
        "read_at": fmt_dt(row.read_at),
        "created_at": fmt_dt(row.created_at),
    }


def list_notifications(
    db: Session,
    current: CurrentUser,
    *,
    page: int,
    page_size: int,
    unread_only: bool,
) -> dict[str, Any]:
    query = db.query(Notification).filter(
        Notification.recipient_role == current.role,
        Notification.recipient_id == current.user_id,
    )
    if unread_only:
        query = query.filter(Notification.is_read == 0)
    total = query.count()
    rows = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    unread = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.recipient_role == current.role,
            Notification.recipient_id == current.user_id,
            Notification.is_read == 0,
        )
        .scalar()
        or 0
    )
    data = page_data([_item(row) for row in rows], total, page, page_size)
    data["items"] = data["list"]
    data["unread_count"] = int(unread)
    return data


def unread_count(db: Session, current: CurrentUser) -> dict[str, int]:
    count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.recipient_role == current.role,
            Notification.recipient_id == current.user_id,
            Notification.is_read == 0,
        )
        .scalar()
        or 0
    )
    return {"count": int(count)}


def mark_read(db: Session, current: CurrentUser, *, notification_id: int) -> None:
    row = db.get(Notification, notification_id)
    if (
        row is None
        or row.recipient_role != current.role
        or row.recipient_id != current.user_id
    ):
        raise AppException(ErrorCode.NOT_FOUND, "通知不存在")
    if not row.is_read:
        row.is_read = 1
        row.read_at = now_naive()
        db.commit()


def mark_all_read(db: Session, current: CurrentUser) -> int:
    rows = (
        db.query(Notification)
        .filter(
            Notification.recipient_role == current.role,
            Notification.recipient_id == current.user_id,
            Notification.is_read == 0,
        )
        .all()
    )
    for row in rows:
        row.is_read = 1
        row.read_at = now_naive()
    db.commit()
    return len(rows)


def announce(
    db: Session, current: CurrentUser, *, class_id: int, title: str, body: str
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    count = add_for_class(
        db,
        class_id=class_id,
        type="teacher_message",
        title=title,
        body=body,
        target_path="/student/notifications",
    )
    db.commit()
    from app.services.qq_bot import notifier

    notifier.send_announcement(db, class_id=class_id, title=title, body=body)
    return {"recipient_count": count}
