"""M2B 组卷业务：固定/随机组卷、试卷详情、发布、学生开卷。"""

from __future__ import annotations

import random
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.attempt import Attempt
from app.models.paper import Paper
from app.models.paper_question import PaperQuestion
from app.models.question import Question
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.question_repo import QuestionRepository
from app.schemas.paper import PaperCreateRequest
from app.services.class_service import require_owned_class
from app.utils.time import fmt_dt, now_naive

_settings = get_settings()
DEFAULT_QUESTION_SCORE = 1.0


def _paper_item(paper: Paper) -> dict[str, Any]:
    return {
        "id": paper.id,
        "class_id": paper.class_id,
        "title": paper.title,
        "mode": paper.mode,
        "duration_minutes": paper.duration_minutes,
        "shuffle": bool(paper.shuffle),
        "question_count": paper.question_count,
        "total_score": float(paper.total_score or 0),
        "status": paper.status,
        "published_at": fmt_dt(paper.published_at),
        "created_at": fmt_dt(paper.created_at),
    }


def _teacher_question(question: Question, pq: PaperQuestion) -> dict[str, Any]:
    return {
        "id": question.id,
        "seq": pq.seq,
        "score": float(pq.score or 0),
        "type": question.type,
        "stem": question.stem,
        "options": question.options_json,
        "answer": question.answer_json,
        "analysis": question.analysis,
        "knowledge_tag": question.knowledge_tag,
        "difficulty": question.difficulty,
    }


def _student_question(question: Question, pq: PaperQuestion) -> dict[str, Any]:
    return {
        "id": question.id,
        "seq": pq.seq,
        "score": float(pq.score or 0),
        "type": question.type,
        "stem": question.stem,
        "options": question.options_json,
        "knowledge_tag": question.knowledge_tag,
        "difficulty": question.difficulty,
    }


def _require_paper_for_teacher(db: Session, paper_id: int, teacher_id: int) -> Paper:
    paper = PaperRepository(db).get_by_id(paper_id)
    if paper is None:
        raise AppException(ErrorCode.NOT_FOUND, "试卷不存在")
    if paper.class_id:
        require_owned_class(db, paper.class_id, teacher_id)
    return paper


def create_paper(
    db: Session, current: CurrentUser, *, class_id: int, payload: PaperCreateRequest
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    question_repo = QuestionRepository(db)
    selected: list[Question]

    if payload.mode == "fixed":
        ids = list(dict.fromkeys(payload.question_ids or []))
        selected = question_repo.get_many(class_id, ids)
        if len(selected) != len(ids):
            raise AppException(ErrorCode.VALIDATION_ERROR, "存在不属于本班或已删除的题目")
        order = {question_id: index for index, question_id in enumerate(ids)}
        selected.sort(key=lambda question: order[question.id])
    else:
        if not payload.count:
            raise AppException(ErrorCode.VALIDATION_ERROR, "随机组卷必须提供 count")
        candidates = question_repo.random_candidates(
            class_id, tag=payload.knowledge_tag, difficulty=payload.difficulty
        )
        # R1-5：带标签/难度抽不到时回落整库随机
        if not candidates and (payload.knowledge_tag or payload.difficulty):
            candidates = question_repo.random_candidates(class_id, tag=None, difficulty=None)
        if not candidates:
            raise AppException(ErrorCode.QUESTION_BANK_EMPTY, "题库为空，无法组卷")
        if len(candidates) < payload.count:
            raise AppException(ErrorCode.QUESTION_BANK_EMPTY, "题库数量不足，无法组卷")
        selected = random.sample(candidates, payload.count)

    if not selected:
        raise AppException(ErrorCode.QUESTION_BANK_EMPTY, "题库为空，无法组卷")

    total_score = round(len(selected) * DEFAULT_QUESTION_SCORE, 2)
    paper = Paper(
        class_id=class_id,
        title=payload.title,
        mode=payload.mode,
        duration_minutes=payload.duration_minutes,
        shuffle=1 if payload.shuffle else 0,
        question_count=len(selected),
        total_score=total_score,
        status="draft",
        created_by=current.user_id,
    )
    db.add(paper)
    try:
        db.flush()
        for seq, question in enumerate(selected, start=1):
            db.add(
                PaperQuestion(
                    paper_id=paper.id,
                    question_id=question.id,
                    seq=seq,
                    score=DEFAULT_QUESTION_SCORE,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(paper)
    return paper_detail(db, current, paper_id=paper.id)


def paper_detail(db: Session, current: CurrentUser, *, paper_id: int) -> dict[str, Any]:
    paper = _require_paper_for_teacher(db, paper_id, current.user_id)
    rows = PaperRepository(db).questions(paper.id)
    return {
        **_paper_item(paper),
        "questions": [_teacher_question(question, pq) for pq, question in rows],
    }


def publish_paper(db: Session, current: CurrentUser, *, paper_id: int) -> dict[str, Any]:
    repo = PaperRepository(db)
    paper = repo.lock_by_id(paper_id)
    if paper is None:
        raise AppException(ErrorCode.NOT_FOUND, "试卷不存在")
    require_owned_class(db, paper.class_id, current.user_id)
    if paper.status == "closed":
        raise AppException(ErrorCode.PAPER_PUBLISHED_FORBIDDEN, "试卷已关闭，不能再次发布")
    rows = repo.questions(paper.id)
    if not rows:
        raise AppException(ErrorCode.QUESTION_BANK_EMPTY, "试卷没有题目，无法发布")
    if any(question.deleted_at is not None for _pq, question in rows):
        raise AppException(ErrorCode.PAPER_PUBLISHED_FORBIDDEN, "试卷包含已删除题目，无法发布")
    paper.status = "published"
    paper.published_at = now_naive()
    paper.question_count = len(rows)
    paper.total_score = round(sum(float(pq.score or 0) for pq, _question in rows), 2)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(paper)
    return paper_detail(db, current, paper_id=paper.id)


def _attempt_item(attempt: Attempt, paper: Paper) -> dict[str, Any]:
    return {
        "id": attempt.id,
        "paper_id": attempt.paper_id,
        "class_id": attempt.class_id,
        "student_id": attempt.student_id,
        "started_at": fmt_dt(attempt.started_at),
        "deadline_at": fmt_dt(attempt.deadline_at),
        "submitted_at": fmt_dt(attempt.submitted_at),
        "status": attempt.status,
        "total_score": float(attempt.total_score or 0),
        "full_score": float(attempt.full_score or 0),
        "paper": _paper_item(paper),
    }


def _attempt_with_questions(db: Session, attempt: Attempt, paper: Paper) -> dict[str, Any]:
    data = _attempt_item(attempt, paper)
    rows = PaperRepository(db).questions(paper.id)
    data["questions"] = [_student_question(question, pq) for pq, question in rows]
    return data


def start_attempt(db: Session, current: CurrentUser, *, paper_id: int) -> dict[str, Any]:
    paper_repo = PaperRepository(db)
    attempt_repo = AttemptRepository(db)
    paper = paper_repo.get_by_id(paper_id)
    if paper is None:
        raise AppException(ErrorCode.NOT_FOUND, "试卷不存在")
    if current.class_id != paper.class_id:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    existing = attempt_repo.get_by_paper_student(paper.id, current.user_id)
    if existing is not None:
        return _attempt_with_questions(db, existing, paper)
    if paper.status != "published":
        raise AppException(ErrorCode.PAPER_PUBLISHED_FORBIDDEN, "试卷尚未发布")
    now = now_naive()
    deadline = None
    if paper.duration_minutes and paper.duration_minutes > 0:
        from datetime import timedelta

        deadline = now + timedelta(minutes=paper.duration_minutes)
    attempt = Attempt(
        paper_id=paper.id,
        class_id=paper.class_id,
        student_id=current.user_id,
        started_at=now,
        deadline_at=deadline,
        status="doing",
        total_score=0,
        full_score=paper.total_score or 0,
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = attempt_repo.get_by_paper_student(paper.id, current.user_id)
        if existing is None:
            raise
        return _attempt_with_questions(db, existing, paper)
    except Exception:
        db.rollback()
        raise
    db.refresh(attempt)
    return _attempt_with_questions(db, attempt, paper)


def paper_questions_for_teacher(db: Session, paper_id: int) -> list[tuple[PaperQuestion, Question]]:
    return PaperRepository(db).questions(paper_id)
