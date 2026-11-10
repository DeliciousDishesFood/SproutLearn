"""M2B 迁移 0003：题库/组卷/作答/复核六表，并补 grading_result 外键。"""

from __future__ import annotations

from alembic import op

revision = "0003_question_paper_attempt"
down_revision = "0002_grading_result"
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = [
    """
    CREATE TABLE `question` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `type` VARCHAR(16) NOT NULL,
      `stem` TEXT NOT NULL,
      `options_json` JSON DEFAULT NULL,
      `answer_json` JSON NOT NULL,
      `analysis` TEXT DEFAULT NULL,
      `knowledge_tag` VARCHAR(50) NOT NULL DEFAULT '未分类',
      `difficulty` VARCHAR(16) NOT NULL DEFAULT 'medium',
      `status` VARCHAR(16) NOT NULL DEFAULT 'draft',
      `created_by` BIGINT UNSIGNED NOT NULL,
      `deleted_at` DATETIME DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      KEY `idx_question_class_status_deleted` (`class_id`, `status`, `deleted_at`),
      KEY `idx_question_class_tag` (`class_id`, `knowledge_tag`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `paper` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `title` VARCHAR(200) NOT NULL,
      `mode` VARCHAR(16) NOT NULL,
      `duration_minutes` INT NOT NULL DEFAULT 0,
      `shuffle` TINYINT NOT NULL DEFAULT 0,
      `question_count` INT NOT NULL DEFAULT 0,
      `total_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      `status` VARCHAR(16) NOT NULL DEFAULT 'draft',
      `created_by` BIGINT UNSIGNED NOT NULL,
      `published_at` DATETIME DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      KEY `idx_paper_class_status` (`class_id`, `status`),
      CONSTRAINT `fk_paper_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `paper_question` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `paper_id` BIGINT UNSIGNED NOT NULL,
      `question_id` BIGINT UNSIGNED NOT NULL,
      `seq` INT NOT NULL,
      `score` DECIMAL(8,2) NOT NULL DEFAULT 1.00,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_paper_question_seq` (`paper_id`, `seq`),
      UNIQUE KEY `uk_paper_question_question` (`paper_id`, `question_id`),
      KEY `idx_paper_question_question` (`question_id`),
      CONSTRAINT `fk_paper_question_paper` FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `attempt` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `paper_id` BIGINT UNSIGNED NOT NULL,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `student_id` BIGINT UNSIGNED NOT NULL,
      `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `deadline_at` DATETIME DEFAULT NULL,
      `submitted_at` DATETIME DEFAULT NULL,
      `status` VARCHAR(16) NOT NULL DEFAULT 'doing',
      `total_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      `full_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_attempt_paper_student` (`paper_id`, `student_id`),
      KEY `idx_attempt_class_student` (`class_id`, `student_id`),
      CONSTRAINT `fk_attempt_paper` FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `answer_record` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `attempt_id` BIGINT UNSIGNED NOT NULL,
      `question_id` BIGINT UNSIGNED NOT NULL,
      `raw_answer_json` JSON DEFAULT NULL,
      `score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      `is_correct` TINYINT NOT NULL DEFAULT 0,
      `engine` VARCHAR(16) NOT NULL,
      `confidence` DECIMAL(4,3) NOT NULL DEFAULT 0.000,
      `needs_review` TINYINT NOT NULL DEFAULT 0,
      `detail_json` JSON NOT NULL,
      `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_answer_attempt_question` (`attempt_id`, `question_id`),
      CONSTRAINT `fk_answer_record_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `attempt` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `review` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `attempt_id` BIGINT UNSIGNED NOT NULL,
      `answer_record_id` BIGINT UNSIGNED NOT NULL,
      `teacher_id` BIGINT UNSIGNED NOT NULL,
      `old_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      `new_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
      `comment` VARCHAR(500) DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    ALTER TABLE `grading_result`
      ADD CONSTRAINT `fk_grading_result_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
      ADD CONSTRAINT `fk_grading_result_student` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`) ON DELETE CASCADE
    """,
]

DOWNGRADE_TABLES = [
    "review",
    "answer_record",
    "attempt",
    "paper_question",
    "paper",
    "question",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("ALTER TABLE `grading_result` DROP FOREIGN KEY `fk_grading_result_class`")
    op.execute("ALTER TABLE `grading_result` DROP FOREIGN KEY `fk_grading_result_student`")
    for table in DOWNGRADE_TABLES:
        op.execute(f"DROP TABLE IF EXISTS `{table}`")
