"""QQ 绑定路由：生成绑定码、机器人回调、解绑。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import CurrentUser, get_db, require_bot_secret, require_student
from app.schemas.binding import QqBindCallbackRequest
from app.services import binding_service
from app.utils.response import success

router = APIRouter(prefix="/binding", tags=["binding"])


@router.post("/qq-code")
def generate_qq_code(current: CurrentUser = Depends(require_student)):
    """API-17 生成 8 位一次性绑定码（学生本人）。"""
    return success(binding_service.generate_qq_code(current))


@router.post("/qq", dependencies=[Depends(require_bot_secret)])
def bind_qq(payload: QqBindCallbackRequest, db: Session = Depends(get_db)):
    """API-18 机器人回调绑定：X-Bot-Secret 鉴权，一次性消费绑定码。"""
    return success(binding_service.bind_qq(db, payload))


@router.delete("/qq")
def unbind_qq(
    current: CurrentUser = Depends(require_student),
    db: Session = Depends(get_db),
):
    """API-19 解绑 QQ：status=0 保留历史。"""
    binding_service.unbind_qq(db, current)
    return success(None)
