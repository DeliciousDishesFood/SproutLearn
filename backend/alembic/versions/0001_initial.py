"""初始迁移：创建 M1 的 13 张表（严格按契约第 5 章）。

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-08
"""

from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = [
    """
    CREATE TABLE `teacher` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `account` VARCHAR(64) NOT NULL,
      `password_hash` VARCHAR(100) NOT NULL,
      `name` VARCHAR(50) NOT NULL,
      `email` VARCHAR(120) DEFAULT NULL,
      `phone` VARCHAR(20) DEFAULT NULL,
      `status` TINYINT NOT NULL DEFAULT 1,
      `last_login_at` DATETIME DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_teacher_account` (`account`),
      KEY `idx_teacher_email` (`email`),
      KEY `idx_teacher_phone` (`phone`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `class` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_code` VARCHAR(8) NOT NULL,
      `teacher_id` BIGINT UNSIGNED NOT NULL,
      `class_name` VARCHAR(80) NOT NULL,
      `course_name` VARCHAR(80) NOT NULL,
      `status` TINYINT NOT NULL DEFAULT 1,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_class_code` (`class_code`),
      KEY `idx_class_teacher` (`teacher_id`),
      CONSTRAINT `fk_class_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `teacher` (`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `class_invite` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `code` CHAR(6) NOT NULL,
      `status` TINYINT NOT NULL DEFAULT 1,
      `expires_at` DATETIME DEFAULT NULL,
      `created_by` BIGINT UNSIGNED NOT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_invite_code` (`code`),
      KEY `idx_invite_class` (`class_id`),
      KEY `idx_invite_class_status` (`class_id`, `status`),
      CONSTRAINT `fk_invite_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
      CONSTRAINT `fk_invite_created_by` FOREIGN KEY (`created_by`) REFERENCES `teacher` (`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `student` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `student_no` VARCHAR(32) NOT NULL,
      `name` VARCHAR(50) NOT NULL,
      `password_hash` VARCHAR(100) NOT NULL,
      `xp_total` INT UNSIGNED NOT NULL DEFAULT 0,
      `level` TINYINT UNSIGNED NOT NULL DEFAULT 1,
      `status` TINYINT NOT NULL DEFAULT 1,
      `last_login_at` DATETIME DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_class_student_no` (`class_id`, `student_no`),
      KEY `idx_student_class` (`class_id`),
      CONSTRAINT `fk_student_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    -- 契约要求 STORED；MySQL 8.0 的 STORED 生成列不能引用 FK 列（ERROR 1215），
    -- 为保留 student_id 外键与条件唯一，使用 VIRTUAL（唯一/NULL 语义等价）。
    CREATE TABLE `qq_binding` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `student_id` BIGINT UNSIGNED NOT NULL,
      `qq_openid` VARCHAR(64) NOT NULL,
      `active_student_id` BIGINT UNSIGNED GENERATED ALWAYS AS (IF(`status` = 1, `student_id`, NULL)) VIRTUAL,
      `active_qq_openid` VARCHAR(64) GENERATED ALWAYS AS (IF(`status` = 1, `qq_openid`, NULL)) VIRTUAL,
      `status` TINYINT NOT NULL DEFAULT 1,
      `bound_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_binding_student_active` (`active_student_id`),
      UNIQUE KEY `uk_binding_openid_active` (`active_qq_openid`),
      KEY `idx_binding_status` (`status`),
      CONSTRAINT `fk_binding_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
      CONSTRAINT `fk_binding_student` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `xp_config` (
      `code` VARCHAR(32) NOT NULL,
      `name` VARCHAR(50) NOT NULL,
      `base_xp` INT NOT NULL DEFAULT 0,
      `enabled` TINYINT NOT NULL DEFAULT 1,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `difficulty_factor` (
      `code` VARCHAR(16) NOT NULL,
      `name` VARCHAR(16) NOT NULL,
      `factor` INT NOT NULL DEFAULT 1,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `login_streak_rule` (
      `streak_day` TINYINT UNSIGNED NOT NULL,
      `xp` INT NOT NULL DEFAULT 0,
      PRIMARY KEY (`streak_day`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `xp_limit_config` (
      `code` VARCHAR(32) NOT NULL,
      `value` INT NOT NULL DEFAULT 0,
      `unit` VARCHAR(16) NOT NULL,
      `remark` VARCHAR(100) DEFAULT NULL,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `level_def` (
      `level` TINYINT UNSIGNED NOT NULL,
      `title` VARCHAR(20) NOT NULL,
      `min_xp` INT NOT NULL DEFAULT 0,
      PRIMARY KEY (`level`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `grading_config` (
      `code` VARCHAR(32) NOT NULL,
      `value` VARCHAR(64) NOT NULL,
      `remark` VARCHAR(100) DEFAULT NULL,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `knowledge_doc` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `course_name` VARCHAR(80) NOT NULL,
      `title` VARCHAR(200) NOT NULL,
      `file_name` VARCHAR(255) NOT NULL,
      `file_ext` VARCHAR(10) NOT NULL,
      `file_size` BIGINT UNSIGNED NOT NULL,
      `file_path` VARCHAR(500) NOT NULL,
      `file_hash` CHAR(64) NOT NULL,
      `status` TINYINT NOT NULL DEFAULT 0,
      `error_code` VARCHAR(32) DEFAULT NULL,
      `error_message` VARCHAR(500) DEFAULT NULL,
      `page_count` INT UNSIGNED DEFAULT NULL,
      `chunk_count` INT UNSIGNED NOT NULL DEFAULT 0,
      `created_by` BIGINT UNSIGNED NOT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_doc_class_hash` (`class_id`, `file_hash`),
      KEY `idx_doc_class_status` (`class_id`, `status`),
      CONSTRAINT `fk_doc_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
      CONSTRAINT `fk_doc_created_by` FOREIGN KEY (`created_by`) REFERENCES `teacher` (`id`) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
    """
    CREATE TABLE `knowledge_chunk` (
      `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      `doc_id` BIGINT UNSIGNED NOT NULL,
      `class_id` BIGINT UNSIGNED NOT NULL,
      `doc_name` VARCHAR(200) NOT NULL,
      `chunk_index` INT UNSIGNED NOT NULL,
      `content` MEDIUMTEXT NOT NULL,
      `char_count` INT UNSIGNED NOT NULL DEFAULT 0,
      `chapter_title` VARCHAR(200) DEFAULT NULL,
      `page_no` INT UNSIGNED DEFAULT NULL,
      `vector_id` VARCHAR(64) DEFAULT NULL,
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_chunk_doc_index` (`doc_id`, `chunk_index`),
      KEY `idx_chunk_doc` (`doc_id`),
      KEY `idx_chunk_class` (`class_id`),
      CONSTRAINT `fk_chunk_doc` FOREIGN KEY (`doc_id`) REFERENCES `knowledge_doc` (`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """,
]

DOWNGRADE_TABLES = [
    "knowledge_chunk",
    "knowledge_doc",
    "grading_config",
    "level_def",
    "xp_limit_config",
    "login_streak_rule",
    "difficulty_factor",
    "xp_config",
    "qq_binding",
    "student",
    "class_invite",
    "class",
    "teacher",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in DOWNGRADE_TABLES:
        op.execute(f"DROP TABLE IF EXISTS `{table}`")
    op.execute("SET FOREIGN_KEY_CHECKS = 1")
