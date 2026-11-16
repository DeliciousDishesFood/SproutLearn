"""机器人独立 worker：网关事件循环 + 每 60s 到期提醒。"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func

from app.config import get_settings
from app.database import SessionLocal
from app.models.attempt import Attempt
from app.models.bot_notice import BotNotice
from app.models.paper import Paper
from app.models.student import Student
from app.services import notification_service
from app.services.qq_bot import gateway, handler
from app.services.qq_bot import notifier
from app.utils.time import now_naive

REMINDER_SECONDS = 60
DUE_WINDOW_SECONDS = 2 * 3600


def _handle_event(event: dict[str, Any]) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        return handler.handle_event(db, event)
    except Exception as exc:  # noqa: BLE001 - 单条消息失败不能终止 worker
        logger.warning("qq handler error: {}", type(exc).__name__)
        return None
    finally:
        db.close()


def _due_reminders() -> None:
    db = SessionLocal()
    try:
        now = now_naive()
        papers = (
            db.query(Paper)
            .filter(
                Paper.status == "published",
                Paper.due_at.is_not(None),
                Paper.due_at > now,
                Paper.due_at <= now + timedelta(seconds=DUE_WINDOW_SECONDS),
            )
            .all()
        )
        for paper in papers:
            exists = (
                db.query(BotNotice.id)
                .filter(BotNotice.paper_id == paper.id, BotNotice.kind == "due_soon")
                .first()
            )
            if exists is not None:
                continue
            total = (
                db.query(func.count(Student.id))
                .filter(Student.class_id == paper.class_id, Student.status == 1)
                .scalar()
                or 0
            )
            submitted_rows = (
                db.query(Attempt.student_id)
                .filter(
                    Attempt.paper_id == paper.id,
                    Attempt.status.in_(("submitted", "graded")),
                )
                .all()
            )
            submitted_ids = {row[0] for row in submitted_rows}
            missing = (
                db.query(Student)
                .filter(
                    Student.class_id == paper.class_id,
                    Student.status == 1,
                    Student.id.notin_(submitted_ids) if submitted_ids else True,
                )
                .all()
            )
            remaining = max(0, int((paper.due_at - now).total_seconds() // 3600))
            notifier.send_due_soon(
                db,
                paper,
                missing_students=missing,
                submitted=len(submitted_ids),
                total=int(total),
                remaining_text=f"{remaining} 小时",
            )
            for student in missing:
                notification_service.add(
                    db,
                    recipient_role="student",
                    recipient_id=student.id,
                    class_id=paper.class_id,
                    type="paper_due_soon",
                    title=f"作业即将截止：{paper.title}",
                    body=f"还有约 {remaining} 小时截止，请尽快完成。",
                    target_path=f"/student/papers/{paper.id}",
                    payload={"paper_id": paper.id},
                )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("qq due reminder error: {}", type(exc).__name__)
        db.rollback()
    finally:
        db.close()


async def _reminder_loop() -> None:
    while True:
        await asyncio.to_thread(_due_reminders)
        await asyncio.sleep(REMINDER_SECONDS)


async def run_worker() -> None:
    settings = get_settings()
    if not settings.qq_bot_enabled:
        logger.warning("QQ_BOT_ENABLED=false，机器人 worker 不连接网关")
        return
    reminder = asyncio.create_task(_reminder_loop())
    try:
        await gateway.run_gateway(_handle_event)
    finally:
        reminder.cancel()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
