"""最小操作记录写入（不含密码/hash/token）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.account_audit_log import AccountAuditLog


def write_audit(
    db: Session,
    *,
    actor_role: str,
    actor_id: int,
    target_role: str,
    target_id: int,
    class_id: int | None,
    action: str,
    result: str,
    request_id: str | None,
) -> None:
    db.add(
        AccountAuditLog(
            actor_role=actor_role,
            actor_id=actor_id,
            target_role=target_role,
            target_id=target_id,
            class_id=class_id,
            action=action,
            result=result,
            request_id=request_id,
        )
    )
