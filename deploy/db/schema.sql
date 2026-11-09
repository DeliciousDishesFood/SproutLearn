-- =====================================================================
-- 青芽 SproutLearn · M1 数据库结构（MySQL 8.0）
-- 用法：mysql -u<user> -p <database> < deploy/db/schema.sql
-- 说明：仅建表；演示数据使用独立 seed_data.sql，不在此文件内置。
-- =====================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 5.2 teacher
CREATE TABLE IF NOT EXISTS `teacher` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `account` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(100) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `email` VARCHAR(120) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1 正常 / 0 禁用',
  `last_login_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_teacher_account` (`account`),
  KEY `idx_teacher_email` (`email`),
  KEY `idx_teacher_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='教师';

-- 5.3 class
CREATE TABLE IF NOT EXISTS `class` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_code` VARCHAR(8) NOT NULL COMMENT '创建即生成，永不重置；实际长度 CLASS_CODE_LENGTH',
  `teacher_id` BIGINT UNSIGNED NOT NULL,
  `class_name` VARCHAR(80) NOT NULL,
  `course_name` VARCHAR(80) NOT NULL,
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1 正常 / 0 归档',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_class_code` (`class_code`),
  KEY `idx_class_teacher` (`teacher_id`),
  CONSTRAINT `fk_class_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `teacher` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='班级';

-- 5.4 class_invite
CREATE TABLE IF NOT EXISTS `class_invite` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `code` CHAR(6) NOT NULL COMMENT '大写字母+数字，排除 O/0/I/1',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1 有效 / 0 已作废',
  `expires_at` DATETIME DEFAULT NULL COMMENT 'NULL=长期有效',
  `created_by` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_invite_code` (`code`),
  KEY `idx_invite_class` (`class_id`),
  KEY `idx_invite_class_status` (`class_id`, `status`),
  CONSTRAINT `fk_invite_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_invite_created_by` FOREIGN KEY (`created_by`) REFERENCES `teacher` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='邀请码';

-- 5.5 student
CREATE TABLE IF NOT EXISTS `student` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `student_no` VARCHAR(32) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `password_hash` VARCHAR(100) NOT NULL,
  `xp_total` INT UNSIGNED NOT NULL DEFAULT 0,
  `level` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1 正常 / 0 禁用',
  `last_login_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_class_student_no` (`class_id`, `student_no`),
  KEY `idx_student_class` (`class_id`),
  CONSTRAINT `fk_student_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='学生';

-- 5.6 qq_binding：两个生成列实现条件唯一（status=0 时为 NULL）
-- 契约要求 STORED；MySQL 8.0 不允许 STORED 生成列引用被外键约束的列
-- （CREATE TABLE 报 ERROR 1215），为同时保留 student_id 外键与条件唯一，
-- 这里按最小技术偏差使用 VIRTUAL（唯一性与 NULL 语义等价）。契约异议见 handoff。
CREATE TABLE IF NOT EXISTS `qq_binding` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `qq_openid` VARCHAR(64) NOT NULL,
  `active_student_id` BIGINT UNSIGNED GENERATED ALWAYS AS (IF(`status` = 1, `student_id`, NULL)) VIRTUAL,
  `active_qq_openid` VARCHAR(64) GENERATED ALWAYS AS (IF(`status` = 1, `qq_openid`, NULL)) VIRTUAL,
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1 有效 / 0 已解绑（保留审计）',
  `bound_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_binding_student_active` (`active_student_id`),
  UNIQUE KEY `uk_binding_openid_active` (`active_qq_openid`),
  KEY `idx_binding_status` (`status`),
  CONSTRAINT `fk_binding_class` FOREIGN KEY (`class_id`) REFERENCES `class` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_binding_student` FOREIGN KEY (`student_id`) REFERENCES `student` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='QQ 绑定';

-- 5.7 xp_config
CREATE TABLE IF NOT EXISTS `xp_config` (
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `base_xp` INT NOT NULL DEFAULT 0,
  `enabled` TINYINT NOT NULL DEFAULT 1,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='行为经验配置';

-- 5.8 difficulty_factor
CREATE TABLE IF NOT EXISTS `difficulty_factor` (
  `code` VARCHAR(16) NOT NULL,
  `name` VARCHAR(16) NOT NULL,
  `factor` INT NOT NULL DEFAULT 1,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='难度系数';

-- 5.9 login_streak_rule
CREATE TABLE IF NOT EXISTS `login_streak_rule` (
  `streak_day` TINYINT UNSIGNED NOT NULL,
  `xp` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`streak_day`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='连续登录规则';

-- 5.10 xp_limit_config
CREATE TABLE IF NOT EXISTS `xp_limit_config` (
  `code` VARCHAR(32) NOT NULL,
  `value` INT NOT NULL DEFAULT 0,
  `unit` VARCHAR(16) NOT NULL,
  `remark` VARCHAR(100) DEFAULT NULL,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='防刷与封顶配置';

-- 5.11 level_def
CREATE TABLE IF NOT EXISTS `level_def` (
  `level` TINYINT UNSIGNED NOT NULL,
  `title` VARCHAR(20) NOT NULL,
  `min_xp` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='等级头衔';

-- 5.12 grading_config
CREATE TABLE IF NOT EXISTS `grading_config` (
  `code` VARCHAR(32) NOT NULL,
  `value` VARCHAR(64) NOT NULL,
  `remark` VARCHAR(100) DEFAULT NULL,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='判分配置（M2 使用）';

-- 5.13 knowledge_doc
CREATE TABLE IF NOT EXISTS `knowledge_doc` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `course_name` VARCHAR(80) NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `file_ext` VARCHAR(10) NOT NULL,
  `file_size` BIGINT UNSIGNED NOT NULL,
  `file_path` VARCHAR(500) NOT NULL COMMENT '相对 UPLOAD_DIR，禁止绝对路径',
  `file_hash` CHAR(64) NOT NULL,
  `status` TINYINT NOT NULL DEFAULT 0 COMMENT '0 待处理 / 1 解析中 / 2 成功 / 3 失败',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='课程文档';

-- 5.14 knowledge_chunk
CREATE TABLE IF NOT EXISTS `knowledge_chunk` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `doc_id` BIGINT UNSIGNED NOT NULL,
  `class_id` BIGINT UNSIGNED NOT NULL,
  `doc_name` VARCHAR(200) NOT NULL COMMENT '文档名冗余快照',
  `chunk_index` INT UNSIGNED NOT NULL COMMENT '文档内序号，从 0 开始',
  `content` MEDIUMTEXT NOT NULL,
  `char_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `chapter_title` VARCHAR(200) DEFAULT NULL,
  `page_no` INT UNSIGNED DEFAULT NULL,
  `vector_id` VARCHAR(64) DEFAULT NULL COMMENT 'Qdrant point id；M1 为空',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_chunk_doc_index` (`doc_id`, `chunk_index`),
  KEY `idx_chunk_doc` (`doc_id`),
  KEY `idx_chunk_class` (`class_id`),
  CONSTRAINT `fk_chunk_doc` FOREIGN KEY (`doc_id`) REFERENCES `knowledge_doc` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文档切片';

SET FOREIGN_KEY_CHECKS = 1;
