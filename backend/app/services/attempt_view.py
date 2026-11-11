"""M2D 作答恢复的时间字段：server_now 与 remaining_seconds。"""

from __future__ import annotations

from datetime import datetime

from app.models.attempt import Attempt
from app.utils.time import now_naive


def attempt_time_fields(
    attempt: Attempt,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """返回统一的服务端时间字段；已提交/已复核 remaining 固定为 0。"""
    current = now or now_naive()
    if attempt.status in ("submitted", "graded"):
        remaining: int | None = 0
    elif attempt.deadline_at is None:
        remaining = None
    else:
        remaining = max(0, int((attempt.deadline_at - current).total_seconds()))
    return {
        "server_now": current.isoformat(timespec="seconds"),
        "remaining_seconds": remaining,
    }
