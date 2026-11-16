"""M2B 作答路由：自动保存、提交、结果、教师复核。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_current_user, get_db, require_student, require_teacher
from app.schemas.attempt import AnswerSaveRequest, AskSproutRequest, ReviewCreateRequest
from app.services import attempt_service, paper_service, student_chat_service
from app.utils.response import success

router = APIRouter(tags=["attempts"])


@router.get("/attempts/mine")
def list_my_attempts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M2C-05 我的作答记录（仅学生，班级作用域）。"""
    return success(
        paper_service.list_my_attempts(
            db,
            current,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/attempts/{attempt_id}")
def get_attempt(
    attempt_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API-M2D-01 恢复作答：学生本人/同班教师，学生视角无标准答案。"""
    return success(attempt_service.get_attempt_resume(db, current, attempt_id=attempt_id))


@router.put("/attempts/{attempt_id}/answers/{question_id}")
def save_answer(
    attempt_id: int,
    question_id: int,
    payload: AnswerSaveRequest,
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M2-10 自动保存单题作答（upsert）。"""
    return success(
        attempt_service.save_answer(
            db,
            current,
            attempt_id=attempt_id,
            question_id=question_id,
            payload=payload,
        )
    )


@router.post("/attempts/{attempt_id}/ask")
def ask_sprout(
    attempt_id: int,
    payload: AskSproutRequest,
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M36 练习页「问问小芽」：苏格拉底式引导，不返回标准答案。"""
    return success(
        student_chat_service.ask_sprout(
            db,
            current,
            attempt_id=attempt_id,
            payload=payload,
        )
    )


@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: int,
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-M2-11 提交判分；行锁 + 幂等。"""
    return success(attempt_service.submit_attempt(db, current, attempt_id=attempt_id))


@router.get("/attempts/{attempt_id}/result")
def get_result(
    attempt_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API-M2-12 学生看自己 / 教师看全班。"""
    return success(attempt_service.get_result(db, current, attempt_id=attempt_id))


@router.post("/attempts/{attempt_id}/reviews")
def review_attempt(
    attempt_id: int,
    payload: ReviewCreateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M2-13 教师复核改分，写 review 并重算总分。"""
    return success(
        attempt_service.review_attempt(
            db,
            current,
            attempt_id=attempt_id,
            payload=payload,
        )
    )
