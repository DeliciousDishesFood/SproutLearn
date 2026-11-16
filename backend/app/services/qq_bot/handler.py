"""QQ 官方机器人消息处理：学生绑定/查询、教师作业概览/催交/被动通知。"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppException, ErrorCode
from app.models.attempt import Attempt
from app.models.class_ import Class
from app.models.class_bot_config import ClassBotConfig
from app.models.paper import Paper
from app.models.qq_binding import QqBinding
from app.models.student import Student
from app.services import binding_service, bot_service
from app.services import bot_chat_service
from app.services.qq_bot import notifier
from app.utils.time import fmt_dt, now_naive

_MENTION_RE = re.compile(r"<@!?[^>]+>")


def clean_content(content: str) -> str:
    return _MENTION_RE.sub("", content or "").strip()


def _author_openid(d: dict[str, Any]) -> str | None:
    author = d.get("author") if isinstance(d.get("author"), dict) else {}
    return (
        author.get("member_openid")
        or author.get("user_openid")
        or author.get("id")
        or d.get("user_openid")
    )


def _event_context(event: dict[str, Any]) -> tuple[str | None, str | None, str]:
    t = str(event.get("t") or "")
    d = event.get("d") if isinstance(event.get("d"), dict) else {}
    content = clean_content(str(d.get("content") or ""))
    if t == "GROUP_AT_MESSAGE_CREATE":
        return d.get("group_openid"), _author_openid(d), content
    if t == "C2C_MESSAGE_CREATE":
        return None, _author_openid(d), content
    return None, None, content


def _reply(
    content: str,
    *,
    group_openid: str | None,
    user_openid: str | None,
    mention_openids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "content": content[:1800],
        "group_openid": group_openid,
        "user_openid": user_openid,
        "mention_openids": mention_openids or [],
    }


def _config(db: Session, class_id: int) -> ClassBotConfig | None:
    return db.query(ClassBotConfig).filter(ClassBotConfig.class_id == class_id).one_or_none()


def _config_by_group(db: Session, group_openid: str | None) -> ClassBotConfig | None:
    if not group_openid:
        return None
    return (
        db.query(ClassBotConfig)
        .filter(ClassBotConfig.group_openid == group_openid)
        .one_or_none()
    )


def _config_by_teacher(db: Session, openid: str | None) -> ClassBotConfig | None:
    if not openid:
        return None
    return (
        db.query(ClassBotConfig)
        .filter(ClassBotConfig.teacher_openid == openid)
        .one_or_none()
    )


def _context_config(
    db: Session, *, group_openid: str | None, openid: str | None
) -> ClassBotConfig | None:
    return _config_by_group(db, group_openid) or _config_by_teacher(db, openid)


def _binding(db: Session, openid: str | None) -> QqBinding | None:
    if not openid:
        return None
    return (
        db.query(QqBinding)
        .filter(QqBinding.qq_openid == openid, QqBinding.status == 1)
        .one_or_none()
    )


def _remaining(due_at) -> str:
    if due_at is None:
        return "未设置截止"
    delta = due_at - now_naive()
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "已截止"
    if seconds >= 86400:
        return f"{seconds // 86400} 天"
    if seconds >= 3600:
        return f"{seconds // 3600} 小时"
    return f"{max(1, seconds // 60)} 分钟"


def _help_text(*, teacher: bool = False) -> str:
    if teacher:
        return (
            "可用教师命令：\n"
            "作业：最近一次作业概览\n"
            "作业情况：完整未交名单\n"
            "催交：提醒未交学生（@ 失败时发名单）\n"
            "作业通知：把最近作业以被动消息发到本群\n"
            "解绑教师：解除本群教师身份（保留群绑定）\n"
            "绑定群 <8位群绑定码>：把本群绑定到班级"
        )
    return (
        "可用命令：\n"
        "绑定 <8位数字>：绑定学号\n"
        "作业：查看待做作业\n"
        "成绩：查看最近成绩\n"
        "解绑：解除当前绑定\n"
        "绑定群 <8位群绑定码>：教师把本群绑定到班级"
    )


def _do_bind(db: Session, *, code: str, openid: str) -> str:
    try:
        result = binding_service.bind_qq_by_openid(db, code=code, qq_openid=openid)
    except AppException as exc:
        if exc.code == ErrorCode.QQ_ALREADY_BOUND:
            return "绑定码无效/已被占用"
        if exc.code == ErrorCode.CLASS_FORBIDDEN:
            return "老师未开放机器人绑定"
        if exc.code == ErrorCode.BIND_CODE_INVALID:
            return "绑定码无效/已过期"
        return "绑定失败，请稍后重试"
    except Exception:  # noqa: BLE001 - 机器人回复不抛第三方栈
        logger.warning("qq bind failed")
        return "绑定失败，请稍后重试"
    class_name = ""
    klass = db.get(Class, result["class_id"])
    if klass is not None:
        class_name = klass.class_name
    return f"已绑定 {result['student_no']}/{class_name or result['class_code']}"


def _do_group_bind(
    db: Session, *, group_openid: str, code: str, author_openid: str
) -> str:
    payload = bot_service.consume_group_code(code)
    if payload is None:
        return "群绑定码无效/已过期"
    class_id = payload["class_id"]
    klass = db.get(Class, class_id)
    if klass is None:
        return "群绑定码无效/已过期"
    config = _config(db, class_id)
    if config is not None and config.teacher_openid and config.teacher_openid != author_openid:
        return "本群已由其他老师绑定，如需更换请先解绑教师"
    if config is None:
        config = ClassBotConfig(
            class_id=class_id,
            app_id=get_settings().qq_bot_app_id or "env",
            enabled=1,
            group_openid=group_openid,
            teacher_openid=author_openid,
            teacher_bound_at=now_naive(),
            created_by=payload.get("teacher_id") or klass.teacher_id,
        )
        db.add(config)
    else:
        config.group_openid = group_openid
        config.teacher_openid = author_openid
        config.teacher_bound_at = now_naive()
    try:
        db.commit()
    except Exception:
        db.rollback()
        return "群绑定失败，请稍后重试"
    return f"本群已绑定班级 {klass.class_name}，教师身份已绑定"


def _latest_homework(db: Session, class_id: int) -> Paper | None:
    return (
        db.query(Paper)
        .filter(
            Paper.class_id == class_id,
            Paper.status == "published",
            # 组卷默认 practice；老师口中的“作业”包含练习，不能只认 homework
            Paper.kind.in_(("homework", "practice")),
        )
        .order_by(Paper.published_at.desc(), Paper.id.desc())
        .first()
    )


def _homework_stats(db: Session, paper: Paper) -> tuple[int, list[Student]]:
    total = (
        db.query(Student)
        .filter(Student.class_id == paper.class_id, Student.status == 1)
        .count()
    )
    submitted_ids = {
        row[0]
        for row in db.query(Attempt.student_id)
        .filter(
            Attempt.paper_id == paper.id,
            Attempt.status.in_(("submitted", "graded")),
        )
        .all()
    }
    missing = (
        db.query(Student)
        .filter(
            Student.class_id == paper.class_id,
            Student.status == 1,
            Student.id.notin_(submitted_ids) if submitted_ids else True,
        )
        .order_by(Student.student_no.asc())
        .all()
    )
    return int(total), missing


def _teacher_overview(db: Session, *, class_id: int, full: bool = False) -> str:
    paper = _latest_homework(db, class_id)
    if paper is None:
        return "班级暂无已发布作业。"
    total, missing = _homework_stats(db, paper)
    submitted = max(0, total - len(missing))
    limit = len(missing) if full else 10
    names = "、".join(student.name for student in missing[:limit]) or "无"
    suffix = "" if full or len(missing) <= limit else f" 等 {len(missing)} 人"
    return (
        f"最近作业：《{paper.title}》\n"
        f"开始：{fmt_dt(paper.published_at) or '-'}\n"
        f"截止：{fmt_dt(paper.due_at) or '未设置'}（{_remaining(paper.due_at)}）\n"
        f"已交：{submitted}/{total}\n"
        f"未交（{len(missing)}）：{names}{suffix}"
    )


def _teacher_remind(db: Session, *, config: ClassBotConfig) -> dict[str, Any]:
    paper = _latest_homework(db, config.class_id)
    if paper is None:
        return _reply(
            "班级暂无已发布作业。",
            group_openid=config.group_openid,
            user_openid=None,
        )
    total, missing = _homework_stats(db, paper)
    if not missing:
        return _reply(
            f"《{paper.title}》已全部提交。",
            group_openid=config.group_openid,
            user_openid=None,
        )
    names = "、".join(student.name for student in missing[:30]) or "无"
    mention_ids: list[str] = []
    if config.mention_missing:
        mention_ids = [
            row[0]
            for row in db.query(QqBinding.qq_openid)
            .filter(
                QqBinding.student_id.in_([student.id for student in missing]),
                QqBinding.status == 1,
            )
            .all()
        ]
    content = (
        f"【催交】《{paper.title}》\n"
        f"已交：{max(0, total - len(missing))}/{total}\n"
        f"未交：{names}\n请尽快完成。"
    )
    return _reply(
        content,
        group_openid=config.group_openid,
        user_openid=None,
        mention_openids=mention_ids,
    )


def _teacher_notice(db: Session, *, config: ClassBotConfig) -> dict[str, Any]:
    paper = _latest_homework(db, config.class_id)
    if paper is None:
        return _reply(
            "班级暂无已发布作业。",
            group_openid=config.group_openid,
            user_openid=None,
        )
    return _reply(
        notifier.build_assignment_notice(paper),
        group_openid=config.group_openid,
        user_openid=None,
    )


def _teacher_unbind(db: Session, *, config: ClassBotConfig, openid: str) -> str:
    if config.teacher_openid != openid:
        return "仅绑定教师本人可解绑教师身份。"
    config.teacher_openid = None
    config.teacher_bound_at = None
    try:
        db.commit()
    except Exception:
        db.rollback()
        return "解绑教师失败，请稍后重试。"
    return "已解绑教师身份，群绑定保留。"


def _do_assignments(db: Session, *, binding: QqBinding) -> str:
    config = _config(db, binding.class_id)
    if config is None or not config.allow_query_assignments:
        return "老师未开放作业查询"
    papers = (
        db.query(Paper)
        .filter(
            Paper.class_id == binding.class_id,
            Paper.status == "published",
            Paper.kind.in_(("homework", "practice")),
        )
        .order_by(Paper.published_at.desc(), Paper.id.desc())
        .all()
    )
    attempts = {
        attempt.paper_id: attempt.status
        for attempt in db.query(Attempt)
        .filter(Attempt.class_id == binding.class_id, Attempt.student_id == binding.student_id)
        .all()
    }
    pending = [p for p in papers if attempts.get(p.id) not in ("submitted", "graded")]
    if not pending:
        return "当前没有待做作业。"
    lines = ["待做作业："]
    for paper in pending[:8]:
        lines.append(
            f"《{paper.title}》 截止：{fmt_dt(paper.due_at) or '未设置'}（{_remaining(paper.due_at)}）"
        )
    return "\n".join(lines)


def _do_scores(db: Session, *, binding: QqBinding) -> str:
    config = _config(db, binding.class_id)
    if config is None or not config.allow_query_scores:
        return "老师未开放成绩查询"
    rows = (
        db.query(Attempt, Paper)
        .join(Paper, Paper.id == Attempt.paper_id)
        .filter(
            Attempt.class_id == binding.class_id,
            Attempt.student_id == binding.student_id,
            Attempt.status.in_(("graded", "submitted")),
        )
        .order_by(Attempt.submitted_at.desc(), Attempt.id.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return "暂无可查询成绩。"
    lines = ["最近成绩："]
    for attempt, paper in rows:
        lines.append(
            f"《{paper.title}》 {float(attempt.total_score or 0):g}/{float(attempt.full_score or 0):g}"
            f"（{'已复核' if attempt.status == 'graded' else '待复核'}）"
        )
    return "\n".join(lines)


def handle_event(db: Session, event: dict[str, Any]) -> dict[str, Any] | None:
    group_openid, openid, content = _event_context(event)
    if not content or not openid:
        return None
    command, _, arg = content.partition(" ")
    command = command.strip()
    arg = arg.strip()
    config = _context_config(db, group_openid=group_openid, openid=openid)
    is_teacher = bool(config and config.teacher_openid == openid)

    if command == "帮助":
        return _reply(
            _help_text(teacher=is_teacher),
            group_openid=group_openid,
            user_openid=openid,
        )
    if command == "绑定群":
        if not group_openid:
            return _reply("请在群聊中使用群绑定。", group_openid=None, user_openid=openid)
        return _reply(
            _do_group_bind(
                db, group_openid=group_openid, code=arg, author_openid=openid
            ),
            group_openid=group_openid,
            user_openid=None,
        )
    if command == "解绑教师":
        if config is None:
            return _reply(
                "本群尚未绑定班级。", group_openid=group_openid, user_openid=openid
            )
        return _reply(
            _teacher_unbind(db, config=config, openid=openid),
            group_openid=group_openid,
            user_openid=openid,
        )
    if command in ("作业", "作业情况", "催交", "作业通知"):
        if is_teacher:
            if command == "作业":
                text = _teacher_overview(db, class_id=config.class_id, full=False)
                return _reply(text, group_openid=group_openid, user_openid=openid)
            if command == "作业情况":
                text = _teacher_overview(db, class_id=config.class_id, full=True)
                return _reply(text, group_openid=group_openid, user_openid=openid)
            if command == "催交":
                return _teacher_remind(db, config=config)
            return _teacher_notice(db, config=config)
        if command != "作业":
            return _reply(
                "仅老师可用该命令。", group_openid=group_openid, user_openid=openid
            )
    if command == "绑定":
        if not arg.isdigit() or len(arg) != 8 or arg.startswith("0"):
            return _reply(
                "绑定码必须是 8 位数字。", group_openid=group_openid, user_openid=openid
            )
        return _reply(
            _do_bind(db, code=arg, openid=openid),
            group_openid=group_openid,
            user_openid=openid,
        )
    if command == "解绑":
        ok = binding_service.unbind_qq_by_openid(db, qq_openid=openid)
        return _reply(
            "已解除绑定。" if ok else "当前没有绑定。",
            group_openid=group_openid,
            user_openid=openid,
        )
    if command == "作业":
        binding = _binding(db, openid)
        if binding is None:
            return _reply(
                "请先绑定：发送 绑定 <8位绑定码>。",
                group_openid=group_openid,
                user_openid=openid,
            )
        cfg = _config(db, binding.class_id)
        if cfg is not None and not cfg.binding_enabled:
            return _reply(
                "老师未开放机器人绑定。", group_openid=group_openid, user_openid=openid
            )
        return _reply(
            _do_assignments(db, binding=binding),
            group_openid=group_openid,
            user_openid=openid,
        )
    if command == "成绩":
        binding = _binding(db, openid)
        if binding is None:
            return _reply(
                "请先绑定：发送 绑定 <8位绑定码>。",
                group_openid=group_openid,
                user_openid=openid,
            )
        return _reply(
            _do_scores(db, binding=binding),
            group_openid=group_openid,
            user_openid=openid,
        )

    chat_config = config
    if chat_config is None:
        binding = _binding(db, openid)
        if binding is not None:
            chat_config = _config(db, binding.class_id)
    if chat_config is not None and chat_config.bot_chat_enabled:
        text = bot_chat_service.answer(
            db,
            config=chat_config,
            class_id=chat_config.class_id,
            openid=openid,
            question=content,
        )
        return _reply(text, group_openid=group_openid, user_openid=openid)

    return _reply(
        "未识别命令。发送“帮助”查看可用命令。",
        group_openid=group_openid,
        user_openid=openid,
    )
