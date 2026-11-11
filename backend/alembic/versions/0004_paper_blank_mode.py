"""M2C 迁移 0004：paper 增加 blank_mode（默认 smart）。"""

from __future__ import annotations

from alembic import op

revision = "0004_paper_blank_mode"
down_revision = "0003_question_paper_attempt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE `paper` "
        "ADD COLUMN `blank_mode` VARCHAR(8) NOT NULL DEFAULT 'smart' AFTER `mode`"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE `paper` DROP COLUMN `blank_mode`")
