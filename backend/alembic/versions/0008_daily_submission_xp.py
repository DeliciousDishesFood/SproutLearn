"""M3.2 补丁 0008：每日经验拆出 submission_xp。"""

from __future__ import annotations

from alembic import op

revision = "0008_daily_submission_xp"
down_revision = "0007_bot_config_docs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE `student_daily_xp`
        ADD COLUMN `submission_xp` INT NOT NULL DEFAULT 0 AFTER `streak_xp`
        """
    )
    op.execute(
        """
        UPDATE `student_daily_xp`
        SET `submission_xp` = GREATEST(
            `total_xp` - `login_xp` - `practice_xp` - `streak_xp`, 0
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE `student_daily_xp` DROP COLUMN `submission_xp`")
