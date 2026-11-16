"""M2B 作答业务：自动保存 upsert、行锁提交、幂等判分、结果、复核。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.answer_record import AnswerRecord
from app.models.class_ import Class
from app.models.attempt import Attempt
from app.models.grading_result import GradingResult
from app.models.paper import Paper
from app.models.paper_question import PaperQuestion
from app.models.question import Question
from app.models.review import Review
from app.repositories.answer_record_repo import AnswerRecordRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.review_repo import ReviewRepository
from app.schemas.attempt import AnswerSaveRequest, ReviewCreateRequest
from app.services import growth_service, notification_service
from app.services.attempt_view import attempt_time_fields
from app.services.class_service import require_owned_class
from app.services.grading.grader import Grader
from app.services.grading.result_service import sanitize_detail
from app.services.llm.jev_client import build_jev_client
from app.services.llm.router import build_router
from app.utils.time import fmt_dt, now_naive

_settings = get_settings()
DEFAULT_BLANK_MODE = "smart"


def _require_attempt(
    db: Session,
    current: CurrentUser,
    attempt_id: int,
    *,
    lock: bool = False,
) -> tuple[Attempt, Paper]:
    repo = AttemptRepository(db)
    attempt = repo.lock_by_id(attempt_id) if lock else repo.get_by_id(attempt_id)
    if attempt is None:
        raise AppException(ErrorCode.NOT_FOUND, "作答记录不存在")
    paper = db.get(Paper, attempt.paper_id)
    if paper is None:
        raise AppException(ErrorCode.NOT_FOUND, "试卷不存在")
    if current.role == "teacher":
        require_owned_class(db, attempt.class_id, current.user_id)
    else:
        if attempt.student_id != current.user_id or attempt.class_id != current.class_id:
            raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    return attempt, paper


def _paper_rows(db: Session, paper_id: int) -> list[tuple[PaperQuestion, Question]]:
    return PaperRepository(db).questions(paper_id)


def _paper_map(rows: list[tuple[PaperQuestion, Question]]) -> dict[int, tuple[PaperQuestion, Question]]:
    return {question.id: (pq, question) for pq, question in rows}


def _raw_value(raw: Any) -> Any:
    if isinstance(raw, dict) and "answer" in raw:
        return raw.get("answer")
    return raw


def _blank_student_value(raw: Any, count: int) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    if raw is None:
        return [""] * count
    return [raw]


def _aggregate_blank(
    grader: Grader,
    question: Question,
    pq: PaperQuestion,
    raw: Any,
    blank_mode: str,
) -> dict[str, Any]:
    """多空填空：按空计费，总分平均分摊，聚合引擎/置信度/复核标记。"""
    standards = question.answer_json if isinstance(question.answer_json, list) else [question.answer_json]
    students = _blank_student_value(raw, len(standards))
    if len(students) < len(standards):
        students += [""] * (len(standards) - len(students))
    per_score = float(pq.score or 0) / max(1, len(standards))
    total = 0.0
    correct = True
    confidence = 1.0
    needs_review = False
    degraded = False
    engines: list[str] = []
    basis: list[str] = []
    deductions: list[str] = []
    raws: list[Any] = []
    for index, (standard, student) in enumerate(zip(standards, students), start=1):
        result = grader.grade(
            question_type="blank",
            standard=standard,
            student=student,
            full_score=per_score,
            question=f"{question.stem}（第 {index} 空）",
            knowledge_tags=[question.knowledge_tag],
            blank_mode=blank_mode,
        )
        total += float(result["score"])
        correct = correct and bool(result["correct"])
        confidence = min(confidence, float(result["confidence"]))
        needs_review = needs_review or bool(result["needs_review"])
        degraded = degraded or bool(result["degraded"])
        engines.append(str(result["engine"]))
        basis.append(str(result["basis"]))
        deductions.extend(result.get("deductions") or [])
        raws.append(result.get("raw") or {})
    engine = "llm" if "llm" in engines else ("jev" if "jev" in engines else "deterministic")
    return {
        "score": round(total, 2),
        "full_score": round(float(pq.score or 0), 2),
        "correct": correct,
        "basis": "；".join(basis),
        "deductions": deductions,
        "knowledge_tags": [question.knowledge_tag],
        "confidence": round(confidence, 4),
        "needs_review": needs_review,
        "engine": engine,
        "degraded": degraded,
        "raw": {"blanks": raws},
    }


def _grade_one(
    grader: Grader,
    question: Question,
    pq: PaperQuestion,
    raw: Any,
    blank_mode: str,
) -> dict[str, Any]:
    if (question.type or "").lower() == "blank" and isinstance(question.answer_json, list):
        return _aggregate_blank(grader, question, pq, raw, blank_mode)
    student = raw if raw is not None else ""
    return grader.grade(
        question_type=question.type,
        standard=question.answer_json,
        student=student,
        full_score=float(pq.score or 0),
        question=question.stem,
        knowledge_tags=[question.knowledge_tag],
        blank_mode=blank_mode,
    )


def _safe_grade(
    grader: Grader,
    question: Question,
    pq: PaperQuestion,
    raw: Any,
    blank_mode: str,
) -> dict[str, Any]:
    try:
        return _grade_one(grader, question, pq, raw, blank_mode)
    except Exception as exc:  # noqa: BLE001 - 单题异常不阻塞整卷
        return {
            "score": 0.0,
            "full_score": float(pq.score or 0),
            "correct": False,
            "basis": "判分异常，已标记人工复核",
            "deductions": ["判分异常"],
            "knowledge_tags": [question.knowledge_tag],
            "confidence": 0.0,
            "needs_review": True,
            "engine": "deterministic",
            "degraded": True,
            "raw": {"error": type(exc).__name__},
        }


def _grade_all(
    paper_rows: list[tuple[PaperQuestion, Question]],
    raws: dict[int, Any],
    blank_mode: str,
) -> tuple[list[dict[str, Any]], float]:
    settings = get_settings()
    grader = Grader(jev_client=build_jev_client(), llm_router=build_router(), blank_mode=blank_mode)
    started = perf_counter()
    results: list[dict[str, Any]] = []
    workers = max(1, settings.grading_concurrency)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_safe_grade, grader, question, pq, raws.get(question.id), blank_mode)
            for pq, question in paper_rows
        ]
        for future in futures:
            results.append(future.result())
    return results, round((perf_counter() - started) * 1000, 2)


def save_answer(
    db: Session,
    current: CurrentUser,
    *,
    attempt_id: int,
    question_id: int,
    payload: AnswerSaveRequest,
) -> dict[str, Any]:
    attempt, paper = _require_attempt(db, current, attempt_id, lock=True)
    if current.role == "student":
        klass = db.get(Class, attempt.class_id)
        if klass is None or klass.status != 1:
            raise AppException(ErrorCode.CLASS_ARCHIVED, "班级已归档，暂停作答")
    if attempt.status != "doing":
        raise AppException(ErrorCode.ATTEMPT_SUBMITTED, "本次作答已提交，禁止再改")
    rows = _paper_rows(db, paper.id)
    if question_id not in {question.id for _pq, question in rows}:
        raise AppException(ErrorCode.NOT_FOUND, "题目不属于该试卷")
    repo = AnswerRecordRepository(db)
    record = repo.get_by_attempt_question(attempt.id, question_id)
    now = now_naive()
    if record is None:
        record = AnswerRecord(
            attempt_id=attempt.id,
            question_id=question_id,
            raw_answer_json={"answer": payload.answer},
            score=0,
            is_correct=0,
            engine="pending",
            confidence=0,
            needs_review=0,
            detail_json={},
            updated_at=now,
        )
        db.add(record)
    else:
        record.raw_answer_json = {"answer": payload.answer}
        record.updated_at = now
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return {
        "attempt_id": attempt.id,
        "question_id": question_id,
        "answer": payload.answer,
        "updated_at": fmt_dt(record.updated_at),
    }


def _result_payload(
    db: Session,
    attempt: Attempt,
    paper: Paper,
    *,
    grading_ms: float | None = None,
) -> dict[str, Any]:
    rows = _paper_rows(db, paper.id)
    records = {record.question_id: record for record in AnswerRecordRepository(db).list_by_attempt(attempt.id)}
    answers: list[dict[str, Any]] = []
    for pq, question in rows:
        record = records.get(question.id)
        answers.append(
            {
                "id": record.id if record else None,
                "answer_record_id": record.id if record else None,
                "question_id": question.id,
                "seq": pq.seq,
                "type": question.type,
                "stem": question.stem,
                "options": question.options_json,
                "standard_answer": question.answer_json,
                "analysis": question.analysis,
                "knowledge_tag": question.knowledge_tag,
                "difficulty": question.difficulty,
                "full_score": float(pq.score or 0),
                "raw_answer": _raw_value(record.raw_answer_json) if record else None,
                "score": float(record.score or 0) if record else 0.0,
                "is_correct": bool(record.is_correct) if record else False,
                "engine": record.engine if record else "pending",
                "confidence": float(record.confidence or 0) if record else 0.0,
                "needs_review": bool(record.needs_review) if record else False,
                "detail": record.detail_json if record else {},
            }
        )
    reviews = [
        {
            "id": review.id,
            "answer_record_id": review.answer_record_id,
            "old_score": float(review.old_score or 0),
            "new_score": float(review.new_score or 0),
            "comment": review.comment,
            "created_at": fmt_dt(review.created_at),
        }
        for review in ReviewRepository(db).list_by_attempt(attempt.id)
    ]
    late = bool(
        attempt.deadline_at
        and attempt.submitted_at
        and attempt.submitted_at > attempt.deadline_at
    )
    return {
        "attempt": {
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
            "late": late,
            "needs_review": any(item["needs_review"] for item in answers),
        },
        "paper": {
            "id": paper.id,
            "class_id": paper.class_id,
            "title": paper.title,
            "mode": paper.mode,
            "kind": paper.kind,
            "blank_mode": paper.blank_mode,
            "duration_minutes": paper.duration_minutes,
            "status": paper.status,
        },
        "answers": answers,
        "reviews": reviews,
        "grading_ms": grading_ms,
    }


def submit_attempt(db: Session, current: CurrentUser, *, attempt_id: int) -> dict[str, Any]:
    attempt, paper = _require_attempt(db, current, attempt_id, lock=True)
    if current.role == "student":
        klass = db.get(Class, attempt.class_id)
        if klass is None or klass.status != 1:
            raise AppException(ErrorCode.CLASS_ARCHIVED, "班级已归档，暂停作答")
    if attempt.status != "doing":
        # 幂等：不重复判分、不重复写 grading_result
        return _result_payload(db, attempt, paper)
    rows = _paper_rows(db, paper.id)
    if not rows:
        raise AppException(ErrorCode.QUESTION_BANK_EMPTY, "试卷没有题目，无法提交")
    now = now_naive()
    records = {record.question_id: record for record in AnswerRecordRepository(db).list_by_attempt(attempt.id)}
    raws: dict[int, Any] = {}
    truncated: set[int] = set()
    for _pq, question in rows:
        record = records.get(question.id)
        raw = _raw_value(record.raw_answer_json) if record else None
        if (
            attempt.deadline_at
            and record is not None
            and record.updated_at is not None
            and record.updated_at > attempt.deadline_at
        ):
            raw = None
            truncated.add(question.id)
        raws[question.id] = raw

    results, grading_ms = _grade_all(rows, raws, paper.blank_mode or DEFAULT_BLANK_MODE)
    answer_repo = AnswerRecordRepository(db)
    total_score = 0.0
    full_score = 0.0
    for (pq, question), result in zip(rows, results):
        if question.id in truncated:
            result["late_truncated"] = True
        record = answer_repo.get_by_attempt_question(attempt.id, question.id)
        if record is None:
            record = AnswerRecord(
                attempt_id=attempt.id,
                question_id=question.id,
                raw_answer_json=None,
                engine="pending",
                detail_json={},
                updated_at=now,
            )
            db.add(record)
        record.score = float(result["score"])
        record.is_correct = 1 if result["correct"] else 0
        record.engine = str(result["engine"])
        record.confidence = float(result["confidence"])
        record.needs_review = 1 if result["needs_review"] else 0
        record.detail_json = result
        record.updated_at = now
        total_score += float(result["score"])
        full_score += float(pq.score or 0)
        db.add(
            GradingResult(
                class_id=attempt.class_id,
                student_id=attempt.student_id,
                question_ref=str(question.id),
                engine=str(result["engine"]),
                score=float(result["score"]),
                full_score=float(pq.score or 0),
                correct=1 if result["correct"] else 0,
                confidence=float(result["confidence"]),
                needs_review=1 if result["needs_review"] else 0,
                detail_json=sanitize_detail(result),
            )
        )
    attempt.status = "submitted"
    attempt.submitted_at = now
    attempt.total_score = round(total_score, 2)
    attempt.full_score = round(full_score, 2)
    db.flush()
    growth_service.award_submission(
        db,
        attempt=attempt,
        paper=paper,
        rows=rows,
        results=results,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(attempt)
    return _result_payload(db, attempt, paper, grading_ms=grading_ms)


def get_result(db: Session, current: CurrentUser, *, attempt_id: int) -> dict[str, Any]:
    attempt, paper = _require_attempt(db, current, attempt_id)
    if current.role == "student" and attempt.status == "doing":
        raise AppException(ErrorCode.ATTEMPT_SUBMITTED, "本次作答尚未提交，不能查看结果")
    return _result_payload(db, attempt, paper)


def _student_question(question: Question, pq: PaperQuestion) -> dict[str, Any]:
    """恢复/答题用学生视角：不返回标准答案、解析。"""
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


def get_attempt_resume(db: Session, current: CurrentUser, *, attempt_id: int) -> dict[str, Any]:
    """GET /attempts/{id}：学生本人/同班教师恢复已存答案与剩余时间。"""
    attempt, paper = _require_attempt(db, current, attempt_id)
    now = now_naive()
    rows = _paper_rows(db, paper.id)
    records = AnswerRecordRepository(db).list_by_attempt(attempt.id)
    answers = {
        str(record.question_id): _raw_value(record.raw_answer_json)
        for record in records
        if record.raw_answer_json is not None
    }
    return {
        "attempt": {
            "id": attempt.id,
            "paper_id": attempt.paper_id,
            "class_id": attempt.class_id,
            "student_id": attempt.student_id,
            "status": attempt.status,
            "total_score": float(attempt.total_score or 0),
            "full_score": float(attempt.full_score or 0),
            "started_at": fmt_dt(attempt.started_at),
            "deadline_at": fmt_dt(attempt.deadline_at),
            "submitted_at": fmt_dt(attempt.submitted_at),
        },
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "duration_minutes": paper.duration_minutes,
            "blank_mode": paper.blank_mode,
            "kind": paper.kind,
        },
        "questions": [_student_question(question, pq) for pq, question in rows],
        "answers": answers,
        **attempt_time_fields(attempt, now=now),
    }


def review_attempt(
    db: Session,
    current: CurrentUser,
    *,
    attempt_id: int,
    payload: ReviewCreateRequest,
) -> dict[str, Any]:
    attempt, paper = _require_attempt(db, current, attempt_id, lock=True)
    if current.role != "teacher":
        raise AppException(ErrorCode.ROLE_FORBIDDEN, "角色无权限")
    if attempt.status not in ("submitted", "graded"):
        raise AppException(ErrorCode.ATTEMPT_SUBMITTED, "本次作答尚未提交，不能复核")
    record = db.get(AnswerRecord, payload.answer_record_id)
    if record is None or record.attempt_id != attempt.id:
        raise AppException(ErrorCode.NOT_FOUND, "作答记录不存在")
    paper_rows = _paper_map(_paper_rows(db, paper.id))
    pair = paper_rows.get(record.question_id)
    if pair is None:
        raise AppException(ErrorCode.NOT_FOUND, "题目不属于该试卷")
    _pq, _question = pair
    full_score = float(_pq.score or 0)
    if payload.new_score > full_score:
        raise AppException(ErrorCode.VALIDATION_ERROR, "改分不能超过该题满分")
    old_score = float(record.score or 0)
    record.score = payload.new_score
    record.is_correct = 1 if payload.new_score >= full_score else 0
    record.engine = "manual"
    record.confidence = 1.0
    record.needs_review = 0
    record.detail_json = {**(record.detail_json or {}), "manual_review": True}
    db.add(
        Review(
            attempt_id=attempt.id,
            answer_record_id=record.id,
            teacher_id=current.user_id,
            old_score=old_score,
            new_score=payload.new_score,
            comment=payload.comment,
        )
    )
    db.flush()
    total = (
        db.query(func.coalesce(func.sum(AnswerRecord.score), 0))
        .filter(AnswerRecord.attempt_id == attempt.id)
        .scalar()
        or 0
    )
    attempt.total_score = round(float(total), 2)
    attempt.status = "graded"
    body = f"教师已复核，总分 {attempt.total_score}"
    if payload.comment:
        body += f"；评语：{payload.comment}"
    notification_service.add(
        db,
        recipient_role="student",
        recipient_id=attempt.student_id,
        class_id=attempt.class_id,
        type="grading_reviewed",
        title=f"成绩已复核：{paper.title}",
        body=body,
        target_path=f"/student/attempts/{attempt.id}/result",
        payload={"attempt_id": attempt.id, "total_score": float(attempt.total_score)},
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(attempt)
    return _result_payload(db, attempt, paper)
