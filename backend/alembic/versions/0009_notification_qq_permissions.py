"""M3.4 迁移 0009：QQ 机器人密钥移出 DB、群权限、作业截止、通知中心、机器人通知幂等。"""

from __future__ import annotations

from alembic import op

revision = "0009_notification_qq_permissions"
down_revision = "0008_daily_submission_xp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE `class_bot_config` DROP COLUMN `app_secret_cipher`")
    op.execute(
        """
        ALTER TABLE `class_bot_config`
          ADD COLUMN `group_openid` VARCHAR(64) DEFAULT NULL AFTER `enabled`,
          ADD COLUMN `binding_enabled` TINYINT NOT NULL DEFAULT 1 AFTER `group_openid`,
          ADD COLUMN `notify_assignment` TINYINT NOT NULL DEFAULT 1 AFTER `binding_enabled`,
          ADD COLUMN `notify_due_soon` TINYINT NOT NULL DEFAULT 1 AFTER `notify_assignment`,
          ADD COLUMN `mention_missing` TINYINT NOT NULL DEFAULT 0 AFTER `notify_due_soon`,
          ADD COLUMN `allow_query_assignments` TINYINT NOT NULL DEFAULT 1 AFTER `mention_missing`,
          ADD COLUMN `allow_query_scores` TINYINT NOT NULL DEFAULT 0 AFTER `allow_query_assignments`
        """
    )
    op.execute("ALTER TABLE `paper` ADD COLUMN `due_at` DATETIME DEFAULT NULL AFTER `published_at`")
    op.execute(
        """
        CREATE TABLE `notification` (
          `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          `recipient_role` VARCHAR(8) NOT NULL,
          `recipient_id` BIGINT UNSIGNED NOT NULL,
          `class_id` BIGINT UNSIGNED NOT NULL,
          `type` VARCHAR(32) NOT NULL,
          `title` VARCHAR(120) NOT NULL,
          `body` VARCHAR(500) NOT NULL,
          `target_path` VARCHAR(255) DEFAULT NULL,
          `payload_json` JSON DEFAULT NULL,
          `is_read` TINYINT NOT NULL DEFAULT 0,
          `read_at` DATETIME DEFAULT NULL,
          `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          KEY `idx_notification_recipient` (`recipient_role`, `recipient_id`, `is_read`, `created_at`),
          KEY `idx_notification_class_type` (`class_id`, `type`, `created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )
    op.execute(
        """
        CREATE TABLE `bot_notice` (
          `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          `class_id` BIGINT UNSIGNED NOT NULL,
          `paper_id` BIGINT UNSIGNED NOT NULL,
          `kind` VARCHAR(32) NOT NULL,
          `sent_at` DATETIME DEFAULT NULL,
          `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
          `message_id` VARCHAR(64) DEFAULT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uk_bot_notice_paper_kind` (`paper_id`, `kind`),
          KEY `idx_bot_notice_class` (`class_id`, `kind`),
          CONSTRAINT `fk_bot_notice_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
          CONSTRAINT `fk_bot_notice_paper` FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS `bot_notice`")
    op.execute("DROP TABLE IF EXISTS `notification`")
    op.execute("ALTER TABLE `paper` DROP COLUMN `due_at`")
    op.execute(
        """
        ALTER TABLE `class_bot_config`
          DROP COLUMN `allow_query_scores`,
          DROP COLUMN `allow_query_assignments`,
          DROP COLUMN `mention_missing`,
          DROP COLUMN `notify_due_soon`,
          DROP COLUMN `notify_assignment`,
          DROP COLUMN `binding_enabled`,
          DROP COLUMN `group_openid`
        """
    )
    op.execute(
        "ALTER TABLE `class_bot_config` ADD COLUMN `app_secret_cipher` VARBINARY(512) NULL AFTER `app_id`"
    )
