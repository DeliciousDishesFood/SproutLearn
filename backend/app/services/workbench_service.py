"""M3.2 工作台与成长聚合查询。"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import CurrentUser
from app.models.answer_record import AnswerRecord
from app.models.attempt import Attempt
from app.models.paper import Paper
from app.models.student import Student
from app.models.student_daily_xp import StudentDailyXp
from app.models.xp_limit_config import XpLimitConfig
from app.services import growth_service
from app.services.class_service import require_owned_class
from app.utils.time import fmt_dt


def _paper_brief(paper: Paper) -> dict[str, Any]:
    return {
        "id": paper.id,
        "title": paper.title,
        "mode": paper.mode,
        "kind": paper.kind,
        "status": paper.status,
        "question_count": paper.question_count,
        "total_score": float(paper.total_score or 0),
        "duration_minutes": paper.duration_minutes,
        "published_at": fmt_dt(paper.published_at),
        "due_at": fmt_dt(paper.due_at),
        "created_at": fmt_dt(paper.created_at),
    }


def _attempt_needs_review(db: Session, attempt_id: int) -> bool:
    return (
        db.query(AnswerRecord.id)
        .filter(AnswerRecord.attempt_id == attempt_id, AnswerRecord.needs_review == 1)
        .first()
        is not None
    )


def _daily(db: Session, student_id: int) -> StudentDailyXp | None:
    return (
        db.query(StudentDailyXp)
        .filter(
            StudentDailyXp.student_id == student_id,
            StudentDailyXp.stat_date == growth_service.today_date(),
        )
        .one_or_none()
    )


def _practice_cap(db: Session) -> int:
    item = db.get(XpLimitConfig, "practice_daily_cap")
    return max(0, int(item.value or 0)) if item is not None else 0


def student_workbench(db: Session, current: CurrentUser) -> dict[str, Any]:
    student = db.get(Student, current.user_id)
    if student is None:
        return {}
    class_id = int(current.class_id or student.class_id)
    info = growth_service.level_info(db, int(student.xp_total or 0))
    daily = _daily(db, student.id)
    attempts = {
        attempt.paper_id: attempt
        for attempt in db.query(Attempt)
        .filter(Attempt.class_id == class_id, Attempt.student_id == student.id)
        .all()
    }
    papers = (
        db.query(Paper)
        .filter(Paper.class_id == class_id, Paper.status == "published")
        .order_by(Paper.created_at.desc(), Paper.id.desc())
        .all()
    )
    pending = [
        _paper_brief(paper)
        for paper in papers
        if attempts.get(paper.id) is None
        or attempts[paper.id].status not in ("submitted", "graded")
    ]
    recent_rows = (
        db.query(Attempt, Paper)
        .join(Paper, Paper.id == Attempt.paper_id)
        .filter(
            Attempt.class_id == class_id,
            Attempt.student_id == student.id,
            Attempt.status.in_(("submitted", "graded")),
        )
        .order_by(Attempt.submitted_at.desc(), Attempt.id.desc())
        .limit(5)
        .all()
    )
    recent = [
        {
            "attempt_id": attempt.id,
            "paper_id": paper.id,
            "paper_title": paper.title,
            "kind": paper.kind,
            "total_score": float(attempt.total_score or 0),
            "full_score": float(attempt.full_score or 0),
            "status": attempt.status,
            "needs_review": _attempt_needs_review(db, attempt.id),
            "submitted_at": fmt_dt(attempt.submitted_at),
        }
        for attempt, paper in recent_rows
    ]
    activity = growth_service.student_activity(
        db, class_id=class_id, student_id=student.id, weeks=12
    )
    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "class_id": student.class_id,
            "xp_total": int(student.xp_total or 0),
            "streak_days": int(student.streak_days or 0),
        },
        "level": info,
        "xp_total": int(student.xp_total or 0),
        "streak_days": int(student.streak_days or 0),
        "today_xp": int(daily.total_xp or 0) if daily else 0,
        "today": {
            "login_xp": int(daily.login_xp or 0) if daily else 0,
            "practice_xp": int(daily.practice_xp or 0) if daily else 0,
            "streak_xp": int(daily.streak_xp or 0) if daily else 0,
            "submission_xp": int(daily.submission_xp or 0) if daily else 0,
            "total_xp": int(daily.total_xp or 0) if daily else 0,
            "cap": _practice_cap(db),
        },
        "pending": pending,
        "pending_papers": pending,
        "recent": recent,
        "recent_scores": recent,
        "activity": activity,
    }


def teacher_workbench(
    db: Session, current: CurrentUser, *, class_id: int
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    today_start = datetime.combine(growth_service.today_date(), time.min)
    pending_review = (
        db.query(func.count(AnswerRecord.id))
        .join(Attempt, Attempt.id == AnswerRecord.attempt_id)
        .filter(
            Attempt.class_id == class_id,
            Attempt.status.in_(("submitted", "graded")),
            AnswerRecord.needs_review == 1,
        )
        .scalar()
        or 0
    )
    today_submissions = (
        db.query(func.count(Attempt.id))
        .filter(
            Attempt.class_id == class_id,
            Attempt.status.in_(("submitted", "graded")),
            Attempt.submitted_at >= today_start,
        )
        .scalar()
        or 0
    )
    active_students = (
        db.query(func.count(func.distinct(Attempt.student_id)))
        .join(AnswerRecord, AnswerRecord.attempt_id == Attempt.id)
        .filter(
            Attempt.class_id == class_id,
            AnswerRecord.updated_at >= today_start,
        )
        .scalar()
        or 0
    )
    average_score = (
        db.query(func.avg(Attempt.total_score))
        .filter(
            Attempt.class_id == class_id,
            Attempt.status.in_(("submitted", "graded")),
        )
        .scalar()
    )
    average_score_rate = (
        db.query(func.avg(Attempt.total_score / func.nullif(Attempt.full_score, 0)))
        .filter(
            Attempt.class_id == class_id,
            Attempt.status.in_(("submitted", "graded")),
            Attempt.full_score > 0,
        )
        .scalar()
    )
    papers = (
        db.query(Paper)
        .filter(Paper.class_id == class_id)
        .order_by(Paper.created_at.desc(), Paper.id.desc())
        .limit(5)
        .all()
    )
    top_students = (
        db.query(Student)
        .filter(Student.class_id == class_id)
        .order_by(Student.xp_total.desc(), Student.id.asc())
        .limit(5)
        .all()
    )
    top = []
    for student in top_students:
        info = growth_service.level_info(db, int(student.xp_total or 0))
        top.append(
            {
                "student_id": student.id,
                "student_no": student.student_no,
                "name": student.name,
                "xp_total": int(student.xp_total or 0),
                "level": info["level"],
                "title": info["title"],
            }
        )
    activity = growth_service.class_activity(db, class_id=class_id, weeks=12)
    return {
        "class_id": class_id,
        "pending_review": int(pending_review),
        "today_submissions": int(today_submissions),
        "active_students": int(active_students),
        "average_score": round(float(average_score or 0), 2),
        "average_score_rate": round(float(average_score_rate or 0), 4),
        "recent_papers": [_paper_brief(paper) for paper in papers],
        "top_students": top,
        "top5": top,
        "activity": activity,
    }


def student_activity(
    db: Session, current: CurrentUser, *, weeks: int
) -> dict[str, Any]:
    class_id = int(current.class_id or 0)
    items = growth_service.student_activity(
        db, class_id=class_id, student_id=current.user_id, weeks=weeks
    )
    return {"weeks": weeks, "items": items, "activity": items}


def class_activity(
    db: Session, current: CurrentUser, *, class_id: int, weeks: int
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    items = growth_service.class_activity(db, class_id=class_id, weeks=weeks)
    return {"weeks": weeks, "items": items, "activity": items}


def student_growth(db: Session, current: CurrentUser) -> dict[str, Any]:
    class_id = int(current.class_id or 0)
    student = db.get(Student, current.user_id)
    xp_total = int(student.xp_total or 0) if student else 0
    level = growth_service.level_info(db, xp_total)
    items = growth_service.student_activity(
        db, class_id=class_id, student_id=current.user_id, weeks=12
    )
    return {
        "xp_total": xp_total,
        "level": level,
        "ledger": growth_service.recent_ledger(db, current.user_id),
        "activity": items,
        "heatmap": items,
    }


def xp_config(db: Session, current: CurrentUser, *, class_id: int) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    items = growth_service.xp_config_items(db, class_id=class_id)
    return {"class_id": class_id, "items": items, "list": items}


def update_xp_config(
    db: Session, current: CurrentUser, *, class_id: int, items: list[dict[str, Any]]
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    updated = growth_service.set_xp_config(db, class_id=class_id, items=items)
    return {"class_id": class_id, "items": updated, "list": updated}
