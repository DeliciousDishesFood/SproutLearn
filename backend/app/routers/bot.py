"""M3.3 机器人配置与文档中心路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_current_user, get_db, require_teacher
from app.schemas.bot import BotConfigUpdateRequest
from app.services import bot_service, doc_service
from app.utils.response import success

router = APIRouter(tags=["bot-docs"])


@router.get("/classes/{class_id}/bot-config")
def get_bot_config(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.3-01 机器人配置；Secret 只返回 has_secret/末 4 位。"""
    return success(bot_service.get_config(db, current, class_id=class_id))


@router.put("/classes/{class_id}/bot-config")
def put_bot_config(
    class_id: int,
    payload: BotConfigUpdateRequest,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.3-02 保存配置；Secret 空表示不修改。"""
    return success(
        bot_service.save_config(db, current, class_id=class_id, payload=payload)
    )


@router.post("/classes/{class_id}/bot-config/test")
def test_bot_config(
    class_id: int,
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """M3.3-03 测试 QQ getAppAccessToken，8 秒超时。"""
    return success(bot_service.test_config(db, current, class_id=class_id))


@router.get("/docs")
def list_docs(current: CurrentUser = Depends(get_current_user)):
    """M3.3-04 文档清单。"""
    return success(doc_service.list_docs())


@router.get("/docs/{slug}")
def get_doc(slug: str, current: CurrentUser = Depends(get_current_user)):
    """M3.3-05 文档详情；不存在 40401。"""
    return success(doc_service.get_doc(slug))
