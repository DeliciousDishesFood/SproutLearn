"""v1.5 迁移 0012：QQ 主动通知结构化状态与失败原因。"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012_qq_notice_detail"
down_revision = "0011_account_class_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_notice", sa.Column("reason", sa.String(32), nullable=True))
    op.add_column("bot_notice", sa.Column("error_code", sa.String(32), nullable=True))
    op.add_column("bot_notice", sa.Column("error_message", sa.String(255), nullable=True))
    op.add_column(
        "bot_notice",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("bot_notice", sa.Column("last_attempt_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_notice", "last_attempt_at")
    op.drop_column("bot_notice", "attempt_count")
    op.drop_column("bot_notice", "error_message")
    op.drop_column("bot_notice", "error_code")
    op.drop_column("bot_notice", "reason")
