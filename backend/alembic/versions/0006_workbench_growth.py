"""M3.2 迁移 0006：试卷用途、学生连续登录、每日经验、经验流水、班级开关。"""

from __future__ import annotations

from alembic import op

revision = "0006_workbench_growth"
down_revision = "0005_question_bank"
branch_labels = None
depends_on = None

UPGRADE = [
    "ALTER TABLE `paper` ADD COLUMN `kind` VARCHAR(16) NOT NULL DEFAULT 'practice' AFTER `mode`",
    "ALTER TABLE `student` ADD COLUMN `streak_days` SMALLINT UNSIGNED NOT NULL DEFAULT 0 AFTER `last_login_at`",
    "ALTER TABLE `student` ADD COLUMN `last_login_date` DATE DEFAULT NULL AFTER `streak_days`",
    """
    CREATE TABLE `student_daily_xp` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `student_id` BIGINT UNSIGNED NOT NULL,
      `stat_date` DATE NOT NULL,
      `login_xp` INT NOT NULL DEFAULT 0,
      `practice_xp` INT NOT NULL DEFAULT 0,
      `streak_xp` INT NOT NULL DEFAULT 0,
      `total_xp` INT NOT NULL DEFAULT 0,
      `login_awarded` TINYINT NOT NULL DEFAULT 0,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_daily_student_date` (`student_id`, `stat_date`),
      CONSTRAINT `fk_daily_student` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `xp_ledger` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `student_id` BIGINT UNSIGNED NOT NULL,
      `source` VARCHAR(16) NOT NULL,
      `ref_type` VARCHAR(16) NOT NULL,
      `ref_id` BIGINT UNSIGNED NOT NULL,
      `xp` INT NOT NULL DEFAULT 0,
      `note` VARCHAR(100) DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_ledger_student_source_ref` (`student_id`, `source`, `ref_id`),
      KEY `idx_ledger_student_created` (`student_id`, `created_at`),
      CONSTRAINT `fk_ledger_student` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `class_xp_switch` (
      `class_id` BIGINT UNSIGNED NOT NULL,
      `code` VARCHAR(32) NOT NULL,
      `enabled` TINYINT NOT NULL DEFAULT 1,
      PRIMARY KEY (`class_id`, `code`),
      CONSTRAINT `fk_xp_switch_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS `class_xp_switch`")
    op.execute("DROP TABLE IF EXISTS `xp_ledger`")
    op.execute("DROP TABLE IF EXISTS `student_daily_xp`")
    op.execute("ALTER TABLE `student` DROP COLUMN `last_login_date`")
    op.execute("ALTER TABLE `student` DROP COLUMN `streak_days`")
    op.execute("ALTER TABLE `paper` DROP COLUMN `kind`")
