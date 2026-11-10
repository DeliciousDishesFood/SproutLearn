"""M2A 迁移 0002：新增 grading_result 判分结果表（只加表）。"""

from __future__ import annotations

from alembic import op

revision = "0002_grading_result"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


CREATE_SQL = """
CREATE TABLE `grading_result` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `question_ref` VARCHAR(128) NOT NULL,
  `engine` VARCHAR(16) NOT NULL,
  `score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  `full_score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  `correct` TINYINT NOT NULL DEFAULT 0,
  `confidence` DECIMAL(4,3) NOT NULL DEFAULT 0.000,
  `needs_review` TINYINT NOT NULL DEFAULT 0,
  `detail_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_grading_result_class_student` (`class_id`, `student_id`),
  KEY `idx_grading_result_class_created` (`class_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


def upgrade() -> None:
    op.execute(CREATE_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS `grading_result`")
