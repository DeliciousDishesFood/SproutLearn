"""M3.1 题库分类业务：列表、建库、改名、软删、导入自动建库。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import CurrentUser
from app.exceptions import AppException, ErrorCode
from app.models.question_bank import QuestionBank
from app.repositories.question_bank_repo import QuestionBankRepository
from app.schemas.question_bank import QuestionBankCreateRequest, QuestionBankUpdateRequest
from app.services.class_service import require_owned_class
from app.utils.time import fmt_dt, now_naive


def _item(bank: QuestionBank, question_count: int = 0) -> dict[str, Any]:
    return {
        "id": bank.id,
        "class_id": bank.class_id,
        "name": bank.name,
        "description": bank.description,
        "question_count": question_count,
        "created_at": fmt_dt(bank.created_at),
        "updated_at": fmt_dt(bank.updated_at),
    }


def list_banks(db: Session, current: CurrentUser, *, class_id: int) -> list[dict[str, Any]]:
    require_owned_class(db, class_id, current.user_id)
    repo = QuestionBankRepository(db)
    banks = repo.list_scoped(class_id)
    counts = repo.question_counts([bank.id for bank in banks])
    return [_item(bank, counts.get(bank.id, 0)) for bank in banks]


def create_bank(
    db: Session, current: CurrentUser, *, class_id: int, payload: QuestionBankCreateRequest
) -> dict[str, Any]:
    require_owned_class(db, class_id, current.user_id)
    repo = QuestionBankRepository(db)
    if repo.name_exists(class_id, payload.name):
        raise AppException(ErrorCode.QUESTION_BANK_NAME_EXISTS, "题库名称已存在")
    bank = QuestionBank(
        class_id=class_id,
        name=payload.name,
        description=payload.description,
        created_by=current.user_id,
    )
    db.add(bank)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.QUESTION_BANK_NAME_EXISTS, "题库名称已存在") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(bank)
    return _item(bank)


def update_bank(
    db: Session,
    current: CurrentUser,
    *,
    bank_id: int,
    payload: QuestionBankUpdateRequest,
) -> dict[str, Any]:
    bank = QuestionBankRepository(db).get_by_id(bank_id)
    if bank is None or bank.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题库不存在")
    require_owned_class(db, bank.class_id, current.user_id)
    repo = QuestionBankRepository(db)
    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None and payload.name != bank.name:
        if repo.name_exists(bank.class_id, payload.name, exclude_id=bank.id):
            raise AppException(ErrorCode.QUESTION_BANK_NAME_EXISTS, "题库名称已存在")
        bank.name = payload.name
    if "description" in fields:
        bank.description = payload.description
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.QUESTION_BANK_NAME_EXISTS, "题库名称已存在") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(bank)
    return _item(bank, repo.count_questions(bank.id))


def delete_bank(db: Session, current: CurrentUser, *, bank_id: int) -> None:
    bank = QuestionBankRepository(db).get_by_id(bank_id)
    if bank is None or bank.deleted_at is not None:
        raise AppException(ErrorCode.NOT_FOUND, "题库不存在")
    require_owned_class(db, bank.class_id, current.user_id)
    repo = QuestionBankRepository(db)
    if repo.count_questions(bank.id) > 0:
        raise AppException(ErrorCode.QUESTION_BANK_NOT_EMPTY, "题库内仍有题目，禁止删除")
    bank.deleted_at = now_naive()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def resolve_bank(db: Session, *, class_id: int, bank_id: int) -> QuestionBank:
    bank = QuestionBankRepository(db).get_scoped(bank_id, class_id)
    if bank is None:
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    return bank


def resolve_banks(db: Session, *, class_id: int, bank_ids: list[int]) -> list[QuestionBank]:
    unique_ids = list(dict.fromkeys(bank_ids))
    if not unique_ids:
        return []
    repo = QuestionBankRepository(db)
    banks = repo.get_many_scoped(class_id, unique_ids)
    if len(banks) != len(unique_ids):
        raise AppException(ErrorCode.CLASS_FORBIDDEN, "无权访问该班级资源")
    order = {bank_id: index for index, bank_id in enumerate(unique_ids)}
    banks.sort(key=lambda bank: order[bank.id])
    return banks


def suggested_bank_name(filename: str | None) -> str:
    stem = Path(filename or "").stem.strip()
    return (stem or "未命名题库")[:60]


def get_or_create_import_bank(
    db: Session, *, class_id: int, teacher_id: int, now: datetime | None = None
) -> QuestionBank:
    current = now or now_naive()
    repo = QuestionBankRepository(db)
    base_name = f"导入题库-{current.strftime('%Y-%m-%d')}"
    existing = (
        db.query(QuestionBank)
        .filter(
            QuestionBank.class_id == class_id,
            QuestionBank.name == base_name,
            QuestionBank.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if existing is not None:
        return existing
    name = base_name
    suffix = 2
    while repo.name_exists(class_id, name):
        name = f"{base_name}-{suffix}"[:60]
        suffix += 1
    bank = QuestionBank(
        class_id=class_id,
        name=name,
        description="导入时自动创建",
        created_by=teacher_id,
    )
    db.add(bank)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(ErrorCode.QUESTION_BANK_NAME_EXISTS, "题库名称已存在") from exc
    return bank
