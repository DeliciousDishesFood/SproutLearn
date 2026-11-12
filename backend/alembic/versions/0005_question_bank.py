"""M3.1 迁移 0005：题库分类、未分类回填、question.bank_id 必填。"""

from __future__ import annotations

from alembic import op

revision = "0005_question_bank"
down_revision = "0004_paper_blank_mode"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    CREATE TABLE `question_bank` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `name` VARCHAR(60) NOT NULL,
      `description` VARCHAR(200) DEFAULT NULL,
      `created_by` BIGINT UNSIGNED NOT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      `deleted_at` DATETIME DEFAULT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_bank_class_name` (`class_id`, `name`),
      KEY `idx_bank_class_deleted` (`class_id`, `deleted_at`),
      CONSTRAINT `fk_bank_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    INSERT INTO `question_bank` (`class_id`, `name`, `description`, `created_by`)
    SELECT `class_id`, '未分类题库', NULL, MIN(`created_by`)
    FROM `question`
    GROUP BY `class_id`
    """,
    "ALTER TABLE `question` ADD COLUMN `bank_id` BIGINT UNSIGNED DEFAULT NULL AFTER `class_id`",
    """
    UPDATE `question` q
    JOIN `question_bank` b ON b.`class_id` = q.`class_id` AND b.`name` = '未分类题库'
    SET q.`bank_id` = b.`id`
    WHERE q.`bank_id` IS NULL
    """,
    "ALTER TABLE `question` MODIFY COLUMN `bank_id` BIGINT UNSIGNED NOT NULL",
    """
    ALTER TABLE `question`
      ADD CONSTRAINT `fk_question_bank` FOREIGN KEY (`bank_id`) REFERENCES `question_bank` (`id`) ON DELETE RESTRICT,
      ADD KEY `idx_question_bank_status_deleted` (`bank_id`, `status`, `deleted_at`)
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("ALTER TABLE `question` DROP FOREIGN KEY `fk_question_bank`")
    op.execute("ALTER TABLE `question` DROP INDEX `idx_question_bank_status_deleted`")
    op.execute("ALTER TABLE `question` DROP COLUMN `bank_id`")
    op.execute("DROP TABLE IF EXISTS `question_bank`")
