"""M3.2 成长规则：登录/提交/练习/连击、每日封顶、等级与活动聚合。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.answer_record import AnswerRecord
from app.models.attempt import Attempt
from app.models.class_xp_switch import ClassXpSwitch
from app.models.difficulty_factor import DifficultyFactor
from app.models.level_def import LevelDef
from app.models.login_streak_rule import LoginStreakRule
from app.models.paper import Paper
from app.models.question import Question
from app.models.student import Student
from app.models.student_daily_xp import StudentDailyXp
from app.models.xp_config import XpConfig
from app.models.xp_ledger import XpLedger
from app.models.xp_limit_config import XpLimitConfig
from app.utils.time import now_naive


def today_date() -> date:
    return now_naive().date()


def level_info(db: Session, xp_total: int) -> dict[str, Any]:
    levels = db.query(LevelDef).order_by(LevelDef.min_xp.asc()).all()
    if not levels:
        return {
            "level": 1,
            "title": "",
            "min_xp": 0,
            "next_level": None,
            "next_min_xp": None,
            "xp_to_next": None,
            "progress_pct": 0,
        }
    current = levels[0]
    next_level = None
    for level in levels:
        if level.min_xp <= xp_total:
            current = level
        elif level.min_xp > xp_total:
            next_level = level
            break
    progress = 0
    if next_level is not None:
        span = max(1, next_level.min_xp - current.min_xp)
        progress = round((xp_total - current.min_xp) / span * 100, 1)
        progress = max(0, min(100, progress))
    return {
        "level": int(current.level),
        "title": current.title,
        "min_xp": int(current.min_xp),
        "next_level": int(next_level.level) if next_level else None,
        "next_min_xp": int(next_level.min_xp) if next_level else None,
        "xp_to_next": max(0, int(next_level.min_xp) - xp_total) if next_level else None,
        "progress_pct": progress,
    }


def _enabled(db: Session, class_id: int, code: str) -> bool:
    config = db.get(XpConfig, code)
    if config is None:
        return False
    switch = (
        db.query(ClassXpSwitch)
        .filter(ClassXpSwitch.class_id == class_id, ClassXpSwitch.code == code)
        .one_or_none()
    )
    return bool(switch.enabled) if switch is not None else bool(config.enabled)


def _base_xp(db: Session, code: str) -> int:
    config = db.get(XpConfig, code)
    return max(0, int(config.base_xp or 0)) if config is not None else 0


def _limit(db: Session, code: str) -> int:
    item = db.get(XpLimitConfig, code)
    return max(0, int(item.value or 0)) if item is not None else 0


def _daily(db: Session, student_id: int, *, lock: bool = False) -> StudentDailyXp:
    query = db.query(StudentDailyXp).filter(
        StudentDailyXp.student_id == student_id,
        StudentDailyXp.stat_date == today_date(),
    )
    if lock:
        query = query.with_for_update()
    row = query.one_or_none()
    if row is None:
        row = StudentDailyXp(
            student_id=student_id,
            stat_date=today_date(),
            login_xp=0,
            practice_xp=0,
            streak_xp=0,
            submission_xp=0,
            total_xp=0,
            login_awarded=0,
        )
        db.add(row)
        db.flush()
    return row


def _student_locked(db: Session, student_id: int) -> Student | None:
    return (
        db.query(Student)
        .filter(Student.id == student_id)
        .with_for_update()
        .one_or_none()
    )


def _ledger_exists(db: Session, student_id: int, source: str, ref_id: int) -> bool:
    return (
        db.query(XpLedger.id)
        .filter(
            XpLedger.student_id == student_id,
            XpLedger.source == source,
            XpLedger.ref_id == ref_id,
        )
        .first()
        is not None
    )


def _add_ledger(
    db: Session,
    *,
    student_id: int,
    source: str,
    ref_type: str,
    ref_id: int,
    xp: int,
    note: str,
) -> None:
    if xp <= 0 or _ledger_exists(db, student_id, source, ref_id):
        return
    db.add(
        XpLedger(
            student_id=student_id,
            source=source,
            ref_type=ref_type,
            ref_id=ref_id,
            xp=xp,
            note=note,
        )
    )
    db.flush()


def _set_level(db: Session, student: Student) -> None:
    info = level_info(db, int(student.xp_total or 0))
    student.level = int(info["level"])


def _login_xp(db: Session, streak: int) -> int:
    rules = db.query(LoginStreakRule).order_by(LoginStreakRule.streak_day.asc()).all()
    if not rules:
        return 0
    max_xp = max(int(rule.xp or 0) for rule in rules)
    selected = rules[0]
    for rule in rules:
        if int(rule.streak_day) <= streak:
            selected = rule
        else:
            break
    return min(max_xp, max(0, int(selected.xp or 0)))


def apply_login(db: Session, student_id: int) -> int:
    """每日首次登录；同日重复登录不发；断签重置。"""
    student = _student_locked(db, student_id)
    if student is None:
        return 0
    today = today_date()
    if student.last_login_date == today:
        return 0
    yesterday = today - timedelta(days=1)
    streak = int(student.streak_days or 0)
    streak = streak + 1 if student.last_login_date == yesterday else 1
    student.streak_days = streak
    student.last_login_date = today

    daily = _daily(db, student_id, lock=True)
    awarded = 0
    if _enabled(db, student.class_id, "daily_login") and not daily.login_awarded:
        awarded = _login_xp(db, streak)
        if awarded > 0:
            daily.login_xp = int(daily.login_xp or 0) + awarded
            daily.total_xp = int(daily.total_xp or 0) + awarded
            daily.login_awarded = 1
            _add_ledger(
                db,
                student_id=student_id,
                source="login",
                ref_type="day",
                ref_id=int(today.strftime("%Y%m%d")),
                xp=awarded,
                note=f"连续登录第 {streak} 天",
            )
            student.xp_total = int(student.xp_total or 0) + awarded
            _set_level(db, student)
    db.flush()
    return awarded


def award_submission(
    db: Session,
    *,
    attempt: Attempt,
    paper: Paper,
    rows: list[tuple[Any, Question]],
    results: list[dict[str, Any]],
) -> int:
    """提交事务内发经验：考试/作业提交奖励 + 练习逐题 + 连击。"""
    student = _student_locked(db, attempt.student_id)
    if student is None:
        return 0
    daily = _daily(db, attempt.student_id, lock=True)
    kind = (paper.kind or "practice").lower()
    total = 0

    if kind in ("exam", "homework") and _enabled(db, attempt.class_id, kind):
        xp = _base_xp(db, kind)
        if xp > 0 and not _ledger_exists(db, attempt.student_id, kind, attempt.id):
            daily.submission_xp = int(daily.submission_xp or 0) + xp
            daily.total_xp = int(daily.total_xp or 0) + xp
            _add_ledger(
                db,
                student_id=attempt.student_id,
                source=kind,
                ref_type="attempt",
                ref_id=attempt.id,
                xp=xp,
                note=f"{kind} 提交奖励",
            )
            total += xp

    if kind == "practice" and _enabled(db, attempt.class_id, "practice"):
        base = _base_xp(db, "practice")
        factors = {
            factor.code: max(0, int(factor.factor or 0))
            for factor in db.query(DifficultyFactor).all()
        }
        cap = _limit(db, "practice_daily_cap")
        available = max(0, cap - int(daily.practice_xp or 0))
        records = {
            record.question_id: record
            for record in db.query(AnswerRecord)
            .filter(AnswerRecord.attempt_id == attempt.id)
            .all()
        }
        for (pq, question), result in zip(rows, results):
            record = records.get(question.id)
            if record is None or not result.get("correct"):
                continue
            if _ledger_exists(db, attempt.student_id, "practice", record.id):
                continue
            factor = factors.get(question.difficulty, factors.get("unknown", 0))
            xp = min(available, max(0, base * factor))
            if xp <= 0:
                continue
            daily.practice_xp = int(daily.practice_xp or 0) + xp
            daily.total_xp = int(daily.total_xp or 0) + xp
            available -= xp
            _add_ledger(
                db,
                student_id=attempt.student_id,
                source="practice",
                ref_type="answer_record",
                ref_id=record.id,
                xp=xp,
                note=f"练习答对：{question.difficulty}",
            )
            total += xp

        if _enabled(db, attempt.class_id, "streak"):
            base_streak = _base_xp(db, "streak")
            streak_cap = _limit(db, "streak_daily_cap")
            available_streak = max(0, streak_cap - int(daily.streak_xp or 0))
            consecutive = 0
            blocks = 0
            for _pq, result in zip(rows, results):
                if result.get("correct"):
                    consecutive += 1
                    if consecutive % 5 == 0:
                        blocks += 1
                else:
                    consecutive = 0
            xp = min(available_streak, blocks * max(0, base_streak))
            if xp > 0 and not _ledger_exists(db, attempt.student_id, "streak", attempt.id):
                daily.streak_xp = int(daily.streak_xp or 0) + xp
                daily.total_xp = int(daily.total_xp or 0) + xp
                _add_ledger(
                    db,
                    student_id=attempt.student_id,
                    source="streak",
                    ref_type="attempt",
                    ref_id=attempt.id,
                    xp=xp,
                    note=f"连击 {blocks} 组",
                )
                total += xp

    if total > 0:
        student.xp_total = int(student.xp_total or 0) + total
        _set_level(db, student)
    db.flush()
    return total


def _activity_rows(
    db: Session,
    *,
    class_id: int,
    student_id: int | None,
    weeks: int,
) -> list[dict[str, Any]]:
    end = today_date()
    start = end - timedelta(days=weeks * 7 - 1)
    start_dt = datetime.combine(start, time.min)
    query = (
        db.query(
            func.date(AnswerRecord.updated_at).label("day"),
            func.count(AnswerRecord.id).label("answers"),
        )
        .join(Attempt, Attempt.id == AnswerRecord.attempt_id)
        .filter(Attempt.class_id == class_id, AnswerRecord.updated_at >= start_dt)
    )
    if student_id is not None:
        query = query.filter(Attempt.student_id == student_id)
    answer_map = {
        str(day): int(count)
        for day, count in query.group_by(func.date(AnswerRecord.updated_at)).all()
    }
    xp_query = (
        db.query(StudentDailyXp.stat_date, func.sum(StudentDailyXp.total_xp))
        .join(Student, Student.id == StudentDailyXp.student_id)
        .filter(Student.class_id == class_id, StudentDailyXp.stat_date >= start)
    )
    if student_id is not None:
        xp_query = xp_query.filter(StudentDailyXp.student_id == student_id)
    xp_map = {
        str(day): int(total or 0)
        for day, total in xp_query.group_by(StudentDailyXp.stat_date).all()
    }
    items = []
    for offset in range(weeks * 7):
        day = start + timedelta(days=offset)
        key = str(day)
        items.append(
            {
                "date": key,
                "answers": answer_map.get(key, 0),
                "xp": xp_map.get(key, 0),
            }
        )
    return items


def student_activity(db: Session, *, class_id: int, student_id: int, weeks: int) -> list[dict[str, Any]]:
    return _activity_rows(db, class_id=class_id, student_id=student_id, weeks=weeks)


def class_activity(db: Session, *, class_id: int, weeks: int) -> list[dict[str, Any]]:
    end = today_date()
    start = end - timedelta(days=weeks * 7 - 1)
    start_dt = datetime.combine(start, time.min)
    rows = (
        db.query(
            func.date(AnswerRecord.updated_at).label("day"),
            func.count(AnswerRecord.id).label("answers"),
            func.count(func.distinct(Attempt.student_id)).label("active"),
        )
        .join(Attempt, Attempt.id == AnswerRecord.attempt_id)
        .filter(Attempt.class_id == class_id, AnswerRecord.updated_at >= start_dt)
        .group_by(func.date(AnswerRecord.updated_at))
        .all()
    )
    data = {str(day): (int(answers), int(active)) for day, answers, active in rows}
    items = []
    for offset in range(weeks * 7):
        day = start + timedelta(days=offset)
        key = str(day)
        answers, active = data.get(key, (0, 0))
        items.append({"date": key, "answers": answers, "active_students": active})
    return items


def xp_config_items(db: Session, *, class_id: int) -> list[dict[str, Any]]:
    configs = db.query(XpConfig).order_by(XpConfig.code.asc()).all()
    switches = {
        switch.code: switch
        for switch in db.query(ClassXpSwitch)
        .filter(ClassXpSwitch.class_id == class_id)
        .all()
    }
    items = []
    for config in configs:
        switch = switches.get(config.code)
        items.append(
            {
                "code": config.code,
                "name": config.name,
                "base_xp": int(config.base_xp or 0),
                "enabled": bool(switch.enabled) if switch is not None else bool(config.enabled),
                "overridden": switch is not None,
            }
        )
    return items


def set_xp_config(
    db: Session, *, class_id: int, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    from app.exceptions import AppException, ErrorCode

    for item in items:
        code = str(item.get("code") or "").strip()
        if db.get(XpConfig, code) is None:
            raise AppException(ErrorCode.VALIDATION_ERROR, f"未知经验行为：{code}")
        switch = (
            db.query(ClassXpSwitch)
            .filter(ClassXpSwitch.class_id == class_id, ClassXpSwitch.code == code)
            .one_or_none()
        )
        if switch is None:
            switch = ClassXpSwitch(
                class_id=class_id,
                code=code,
                enabled=1 if item.get("enabled") else 0,
            )
            db.add(switch)
        else:
            switch.enabled = 1 if item.get("enabled") else 0
    db.commit()
    return xp_config_items(db, class_id=class_id)


def recent_ledger(db: Session, student_id: int, limit: int = 20) -> list[dict[str, Any]]:
    from app.utils.time import fmt_dt

    return [
        {
            "id": row.id,
            "source": row.source,
            "ref_type": row.ref_type,
            "ref_id": row.ref_id,
            "xp": int(row.xp or 0),
            "note": row.note,
            "created_at": fmt_dt(row.created_at),
        }
        for row in db.query(XpLedger)
        .filter(XpLedger.student_id == student_id)
        .order_by(XpLedger.id.desc())
        .limit(limit)
        .all()
    ]
