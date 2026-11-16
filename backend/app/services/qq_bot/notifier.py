"""QQ 群通知：发布作业、T-2h 提醒、教师公告；失败只记录不抛出。"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.bot_notice import BotNotice
from app.models.class_bot_config import ClassBotConfig
from app.models.paper import Paper
from app.models.qq_binding import QqBinding
from app.services.qq_bot import client
from app.utils.time import fmt_dt, now_naive


def _enabled_config(db: Session, class_id: int) -> ClassBotConfig | None:
    if not get_settings().qq_bot_enabled:
        return None
    config = (
        db.query(ClassBotConfig)
        .filter(ClassBotConfig.class_id == class_id, ClassBotConfig.enabled == 1)
        .one_or_none()
    )
    if config is None or not config.group_openid:
        return None
    return config


def _start_notice(db: Session, *, class_id: int, paper_id: int, kind: str) -> BotNotice | None:
    existing = (
        db.query(BotNotice)
        .filter(BotNotice.paper_id == paper_id, BotNotice.kind == kind)
        .one_or_none()
    )
    if existing is not None:
        return None
    notice = BotNotice(
        class_id=class_id,
        paper_id=paper_id,
        kind=kind,
        status="pending",
    )
    db.add(notice)
    try:
        db.commit()
    except Exception:
        db.rollback()
        return None
    db.refresh(notice)
    return notice


def _finish(db: Session, notice: BotNotice, *, status: str, message_id: str | None = None) -> None:
    notice.status = status
    notice.sent_at = now_naive() if status == "sent" else None
    notice.message_id = message_id
    try:
        db.commit()
    except Exception:
        db.rollback()


def build_assignment_notice(paper: Paper) -> str:
    start = fmt_dt(paper.published_at) or "-"
    due = fmt_dt(paper.due_at) or "未设置"
    return f"【新作业】《{paper.title}》\n开始：{start}\n截止：{due}\n请到青芽完成。"


def send_assignment_published(db: Session, paper: Paper) -> str:
    config = _enabled_config(db, paper.class_id)
    if config is None or not config.notify_assignment:
        return "skipped"
    notice = _start_notice(
        db, class_id=paper.class_id, paper_id=paper.id, kind="assignment"
    )
    if notice is None:
        return "skipped"
    content = build_assignment_notice(paper)
    try:
        result = client.send_group_message(config.group_openid, content)
        _finish(db, notice, status="sent", message_id=result.get("message_id"))
        return "sent"
    except client.QQBotError as exc:
        _finish(db, notice, status="failed")
        logger.warning(
            "qq assignment notice failed class_id={} paper_id={} error={}",
            paper.class_id,
            paper.id,
            exc.safe_message,
        )
        return "failed"


def send_due_soon(
    db: Session,
    paper: Paper,
    *,
    missing_students: list[Any],
    submitted: int,
    total: int,
    remaining_text: str,
) -> bool:
    notice = _start_notice(db, class_id=paper.class_id, paper_id=paper.id, kind="due_soon")
    if notice is None:
        return False
    config = _enabled_config(db, paper.class_id)
    if config is None or not config.notify_due_soon:
        _finish(db, notice, status="skipped")
        return False
    names = "、".join(student.name for student in missing_students[:20]) or "无"
    content = (
        f"【作业提醒】《{paper.title}》还有 {remaining_text} 截止，"
        f"已交 {submitted}/{total}，未交：{names}"
    )
    mention_ids: list[str] = []
    if config.mention_missing and missing_students:
        bindings = (
            db.query(QqBinding)
            .filter(
                QqBinding.student_id.in_([student.id for student in missing_students]),
                QqBinding.status == 1,
            )
            .all()
        )
        mention_ids = [binding.qq_openid for binding in bindings]
    try:
        try:
            result = client.send_group_message(
                config.group_openid, content, mention_openids=mention_ids
            )
        except client.QQBotError:
            if not mention_ids:
                raise
            # @ 不支持时降级为纯名单，不声称已 @
            result = client.send_group_message(config.group_openid, content)
        _finish(db, notice, status="sent", message_id=result.get("message_id"))
        return True
    except client.QQBotError as exc:
        _finish(db, notice, status="failed")
        logger.warning(
            "qq due notice failed class_id={} paper_id={} error={}",
            paper.class_id,
            paper.id,
            exc.safe_message,
        )
        return False


def send_announcement(
    db: Session, *, class_id: int, title: str, body: str
) -> bool:
    config = _enabled_config(db, class_id)
    if config is None or not config.notify_assignment:
        return False
    content = f"【班级公告】{title}\n{body}"
    try:
        client.send_group_message(config.group_openid, content)
        return True
    except client.QQBotError as exc:
        logger.warning(
            "qq announcement failed class_id={} error={}",
            class_id,
            exc.safe_message,
        )
        return False
