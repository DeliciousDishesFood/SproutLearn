"""M3.1 题库分类路由：列表、新建、改名/描述、软删。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_db, require_teacher
from app.schemas.question_bank import QuestionBankCreateRequest, QuestionBankUpdateRequest
from app.services import question_bank_service
from app.utils.response import success

router = APIRouter(tags=["question-banks"])


@router.get("/classes/{class_id}/banks")
def list_banks(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M3-01 班级题库列表（含题数）。"""
    return success(question_bank_service.list_banks(db, current, class_id=class_id))


@router.post("/classes/{class_id}/banks")
def create_bank(
    class_id: int,
    payload: QuestionBankCreateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M3-02 新建题库；重名 40913。"""
    return success(question_bank_service.create_bank(db, current, class_id=class_id, payload=payload))


@router.patch("/banks/{bank_id}")
def update_bank(
    bank_id: int,
    payload: QuestionBankUpdateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M3-03 改名/改描述；重名 40913。"""
    return success(
        question_bank_service.update_bank(
            db, current, bank_id=bank_id, payload=payload
        )
    )


@router.delete("/banks/{bank_id}")
def delete_bank(
    bank_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """API-M3-04 软删题库；库内有题 40912。"""
    question_bank_service.delete_bank(db, current, bank_id=bank_id)
    return success(None)
