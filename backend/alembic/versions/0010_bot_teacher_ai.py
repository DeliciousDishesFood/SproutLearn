"""M3.5 迁移 0010：机器人教师身份与 AI 问答配置。"""

from __future__ import annotations

from alembic import op

revision = "0010_bot_teacher_ai"
down_revision = "0009_notification_qq_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE `class_bot_config`
          ADD COLUMN `teacher_openid` VARCHAR(64) DEFAULT NULL AFTER `group_openid`,
          ADD COLUMN `teacher_bound_at` DATETIME DEFAULT NULL AFTER `teacher_openid`,
          ADD COLUMN `bot_chat_mode` VARCHAR(16) NOT NULL DEFAULT 'balanced' AFTER `allow_query_scores`,
          ADD COLUMN `bot_chat_enabled` TINYINT NOT NULL DEFAULT 1 AFTER `bot_chat_mode`,
          ADD COLUMN `bot_chat_max_chars` INT NOT NULL DEFAULT 600 AFTER `bot_chat_enabled`
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE `class_bot_config`
          DROP COLUMN `bot_chat_max_chars`,
          DROP COLUMN `bot_chat_enabled`,
          DROP COLUMN `bot_chat_mode`,
          DROP COLUMN `teacher_bound_at`,
          DROP COLUMN `teacher_openid`
        """
    )
