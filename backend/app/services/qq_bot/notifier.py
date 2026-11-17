"""QQ 群通知：发布作业、T-2h 提醒、教师公告；失败只记录不抛出。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.bot_notice import BotNotice
from app.models.class_ import Class
from app.models.class_bot_config import ClassBotConfig
from app.models.paper import Paper
from app.models.qq_binding import QqBinding
from app.services.qq_bot import client
from app.utils.time import fmt_dt, now_naive

PERMISSION_MESSAGE = "QQ 未允许机器人向该群主动发言，请由群主在手机 QQ 中开启主动发言权限。"
SKIP_MESSAGES = {
    "qq_disabled": "QQ 机器人总开关未开启",
    "class_missing": "班级不存在",
    "class_archived": "班级已归档",
    "config_missing": "班级尚未保存机器人配置",
    "bot_disabled": "班级机器人未启用",
    "group_unbound": "班级群尚未绑定",
    "notify_assignment_disabled": "班级关闭了新作业群通知",
    "notify_due_soon_disabled": "班级关闭了到期提醒",
    "already_notified": "该作业已有通知记录",
    "notice_incomplete": "上次通知未完成，可重试",
    "notice_create_failed": "通知记录创建失败",
}


@dataclass
class NoticeResult:
    status: str
    reason: str
    message: str
    error_code: str | None = None
    attempt_count: int = 0
    sent_at: Any = None

    def as_detail(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "error_code": self.error_code,
            "message": self.message,
            "attempt_count": self.attempt_count,
            "sent_at": fmt_dt(self.sent_at) if self.sent_at else None,
        }


def _skip(reason: str, *, attempt_count: int = 0) -> NoticeResult:
    return NoticeResult(
        status="skipped",
        reason=reason,
        message=SKIP_MESSAGES.get(reason, "未发送"),
        attempt_count=attempt_count,
    )


def _context(
    db: Session, class_id: int
) -> tuple[ClassBotConfig | None, NoticeResult | None]:
    if not get_settings().qq_bot_enabled:
        return None, _skip("qq_disabled")
    klass = db.get(Class, class_id)
    if klass is None:
        return None, _skip("class_missing")
    if klass.status != 1:
        return None, _skip("class_archived")
    config = (
        db.query(ClassBotConfig)
        .filter(ClassBotConfig.class_id == class_id)
        .one_or_none()
    )
    if config is None:
        return None, _skip("config_missing")
    if not config.enabled:
        return None, _skip("bot_disabled")
    if not config.group_openid:
        return None, _skip("group_unbound")
    return config, None


def _enabled_config(db: Session, class_id: int) -> ClassBotConfig | None:
    config, _skip_result = _context(db, class_id)
    return config


def _find_notice(db: Session, paper_id: int, kind: str) -> BotNotice | None:
    return (
        db.query(BotNotice)
        .filter(BotNotice.paper_id == paper_id, BotNotice.kind == kind)
        .one_or_none()
    )


def _start_notice(
    db: Session,
    *,
    class_id: int,
    paper_id: int,
    kind: str,
    allow_retry: bool = False,
) -> tuple[BotNotice | None, NoticeResult | None]:
    existing = _find_notice(db, paper_id, kind)
    if existing is not None:
        if existing.status == "sent":
            if allow_retry:
                return existing, NoticeResult(
                    "sent", "already_sent", "该通知已发送", attempt_count=existing.attempt_count or 0
                )
            return existing, NoticeResult(
                "skipped",
                "already_notified",
                SKIP_MESSAGES["already_notified"],
                attempt_count=existing.attempt_count or 0,
            )
        if not allow_retry:
            if existing.status == "pending":
                existing.status = "failed"
                existing.reason = "notice_incomplete"
                existing.error_message = "上次通知未完成，可重试"
                existing.last_attempt_at = now_naive()
                db.commit()
                db.refresh(existing)
            return existing, NoticeResult(
                existing.status,
                existing.reason or "already_notified",
                existing.error_message or SKIP_MESSAGES["already_notified"],
                error_code=existing.error_code,
                attempt_count=existing.attempt_count or 0,
                sent_at=existing.sent_at,
            )
        existing.status = "pending"
        existing.reason = None
        existing.error_code = None
        existing.error_message = None
        existing.last_attempt_at = now_naive()
        existing.attempt_count = int(existing.attempt_count or 0) + 1
        db.commit()
        db.refresh(existing)
        return existing, None
    notice = BotNotice(
        class_id=class_id,
        paper_id=paper_id,
        kind=kind,
        status="pending",
        attempt_count=1,
        last_attempt_at=now_naive(),
    )
    db.add(notice)
    try:
        db.commit()
    except Exception:  # noqa: BLE001 - 通知记录失败时降级，不影响试卷发布
        db.rollback()
        return None, _skip("notice_create_failed")
    db.refresh(notice)
    return notice, None


def _finish(
    db: Session,
    notice: BotNotice,
    *,
    status: str,
    reason: str,
    message_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> NoticeResult:
    notice.status = status
    notice.reason = reason
    notice.sent_at = now_naive() if status == "sent" else None
    notice.message_id = message_id
    notice.error_code = error_code
    notice.error_message = error_message[:255] if error_message else None
    notice.attempt_count = int(notice.attempt_count or 1)
    notice.last_attempt_at = now_naive()
    try:
        db.commit()
        db.refresh(notice)
    except Exception:  # noqa: BLE001 - 外部发送结果优先返回，持久化失败继续降级
        db.rollback()
    return NoticeResult(
        status=status,
        reason=reason,
        message=error_message or ("已发送" if status == "sent" else SKIP_MESSAGES.get(reason, "未发送")),
        error_code=error_code,
        attempt_count=notice.attempt_count,
        sent_at=notice.sent_at,
    )


def _classify_error(exc: client.QQBotError) -> tuple[str, str]:
    code = str(exc.code or "").strip()
    message = exc.safe_message or "QQ 发送失败"
    if code == "40034105" or "主动消息失败" in message or "无权限" in message:
        return "qq_permission_denied", PERMISSION_MESSAGE
    if code in {"40034", "40035", "429"} or exc.status == 429 or "频率" in message:
        return "qq_rate_limited", "QQ 主动消息发送过于频繁，请稍后重试。"
    if "超时" in message or "timeout" in message.lower():
        return "qq_timeout", "QQ 主动消息发送超时，请稍后重试。"
    if "连接" in message or "network" in message.lower():
        return "qq_network_error", "QQ 接口连接失败，请检查网络后重试。"
    return "qq_send_failed", f"QQ 主动消息发送失败：{message[:160]}"


def build_assignment_notice(paper: Paper) -> str:
    start = fmt_dt(paper.published_at) or "-"
    due = fmt_dt(paper.due_at) or "未设置"
    return f"【新作业】《{paper.title}》\n开始：{start}\n截止：{due}\n请到青芽完成。"


def _send_assignment(
    db: Session, paper: Paper, *, allow_retry: bool
) -> NoticeResult:
    config, skip_result = _context(db, paper.class_id)
    if skip_result is not None:
        return skip_result
    assert config is not None
    if not config.notify_assignment:
        return _skip("notify_assignment_disabled")
    notice, existing_result = _start_notice(
        db,
        class_id=paper.class_id,
        paper_id=paper.id,
        kind="assignment",
        allow_retry=allow_retry,
    )
    if existing_result is not None:
        return existing_result
    assert notice is not None
    content = build_assignment_notice(paper)
    try:
        result = client.send_group_message(config.group_openid, content)
        return _finish(
            db, notice, status="sent", reason="sent", message_id=result.get("message_id")
        )
    except client.QQBotError as exc:
        reason, message = _classify_error(exc)
        logger.warning(
            "qq assignment notice failed class_id={} paper_id={} reason={} error_code={}",
            paper.class_id,
            paper.id,
            reason,
            exc.code,
        )
        return _finish(
            db,
            notice,
            status="failed",
            reason=reason,
            error_code=str(exc.code) if exc.code else None,
            error_message=message,
        )


def send_assignment_published_detail(db: Session, paper: Paper) -> dict[str, Any]:
    return _send_assignment(db, paper, allow_retry=False).as_detail()


def send_assignment_published(db: Session, paper: Paper) -> str:
    """兼容旧调用：只返回 sent/failed/skipped 字符串。"""
    return send_assignment_published_detail(db, paper)["status"]


def retry_assignment_notice(db: Session, paper: Paper) -> dict[str, Any]:
    return _send_assignment(db, paper, allow_retry=True).as_detail()


def send_due_soon(
    db: Session,
    paper: Paper,
    *,
    missing_students: list[Any],
    submitted: int,
    total: int,
    remaining_text: str,
) -> bool:
    config, skip_result = _context(db, paper.class_id)
    if skip_result is not None:
        notice, _existing = _start_notice(
            db, class_id=paper.class_id, paper_id=paper.id, kind="due_soon", allow_retry=False
        )
        if notice is not None and notice.status == "pending":
            _finish(
                db,
                notice,
                status="skipped",
                reason=skip_result.reason,
                error_message=skip_result.message,
            )
        return False
    assert config is not None
    notice, existing = _start_notice(
        db, class_id=paper.class_id, paper_id=paper.id, kind="due_soon", allow_retry=False
    )
    if existing is not None:
        return existing.status == "sent"
    if not config.notify_due_soon:
        if notice is not None:
            _finish(db, notice, status="skipped", reason="notify_due_soon_disabled")
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
    assert notice is not None
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
        _finish(db, notice, status="sent", reason="sent", message_id=result.get("message_id"))
        return True
    except client.QQBotError as exc:
        reason, message = _classify_error(exc)
        logger.warning(
            "qq due notice failed class_id={} paper_id={} reason={} error_code={}",
            paper.class_id,
            paper.id,
            reason,
            exc.code,
        )
        _finish(
            db,
            notice,
            status="failed",
            reason=reason,
            error_code=str(exc.code) if exc.code else None,
            error_message=message,
        )
        return False


def send_announcement(
    db: Session, *, class_id: int, title: str, body: str
) -> bool:
    config, skip_result = _context(db, class_id)
    if skip_result is not None or not config.notify_assignment:
        return False
    content = f"【班级公告】{title}\n{body}"
    try:
        client.send_group_message(config.group_openid, content)
        return True
    except client.QQBotError as exc:
        logger.warning(
            "qq announcement failed class_id={} reason={} error_code={}",
            class_id,
            _classify_error(exc)[0],
            exc.code,
        )
        return False
