"""M3.4 通知中心路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_current_user, get_db, require_teacher
from app.services import notification_service
from app.utils.response import success

router = APIRouter(tags=["notifications"])


class AnnouncementRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=500)


@router.get("/notifications")
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success(
        notification_service.list_notifications(
            db, current, page=page, page_size=page_size, unread_only=unread_only
        )
    )


@router.get("/notifications/unread-count")
def unread_count(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success(notification_service.unread_count(db, current))


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification_service.mark_read(db, current, notification_id=notification_id)
    return success(None)


@router.post("/notifications/read-all")
def mark_all_read(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success({"count": notification_service.mark_all_read(db, current)})


@router.post("/classes/{class_id}/announcements")
def create_announcement(
    class_id: int,
    payload: AnnouncementRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return success(
        notification_service.announce(
            db,
            current,
            class_id=class_id,
            title=payload.title,
            body=payload.body,
        )
    )
