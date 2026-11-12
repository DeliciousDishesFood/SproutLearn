"""M3.3 迁移 0007：班级 QQ 机器人配置。"""

from __future__ import annotations

from alembic import op

revision = "0007_bot_config_docs"
down_revision = "0006_workbench_growth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE `class_bot_config` (
          `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          `class_id` BIGINT UNSIGNED NOT NULL,
          `app_id` VARCHAR(64) NOT NULL,
          `app_secret_cipher` VARBINARY(512) NOT NULL,
          `callback_url` VARCHAR(255) DEFAULT NULL,
          `enabled` TINYINT NOT NULL DEFAULT 0,
          `last_check_at` DATETIME DEFAULT NULL,
          `last_check_status` VARCHAR(16) NOT NULL DEFAULT 'never',
          `created_by` BIGINT UNSIGNED NOT NULL,
          `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uk_bot_class` (`class_id`),
          CONSTRAINT `fk_bot_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='班级 QQ 机器人配置'
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS `class_bot_config`")
