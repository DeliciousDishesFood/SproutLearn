-- ============================================================
-- 智能助学平台 · 演示数据脚本（seed_data.sql）
-- 版本：V1.2（对齐 M1 落地文档 V1.0 的表结构）｜ 日期：2026-11-07
-- ------------------------------------------------------------
-- 说明：
-- 1) 本脚本不是系统功能，仅用于演示/录制前的数据重置。
-- 2) 表名与字段严格对应 M1 落地文档第 5 章：
--    teacher / class / class_invite / student / qq_binding /
--    xp_config / difficulty_factor / login_streak_rule /
--    xp_limit_config / level_def / grading_config
-- 3) 题库数据不在此脚本：通过系统「题库导入」功能加载
--    docs/demo/题库演示数据.json（同时演示导入链路）。
-- 4) password_hash 已内置 Demo@123 的 BCrypt 哈希（cost 12，与 BCRYPT_ROUNDS 一致），
--    可直接登录；若改演示密码，用后端 hash_password 生成后替换。
-- 5) 学生登录凭证 = 班级编号 C26A79 + 学号 + 密码（不是邀请码）。
-- 执行顺序：alembic upgrade head → 本脚本。
-- ============================================================

SET NAMES utf8mb4;

-- 幂等保护：演示重置时允许重复执行（先清业务数据）
DELETE FROM knowledge_chunk WHERE class_id = 1;
DELETE FROM knowledge_doc   WHERE class_id = 1;
DELETE FROM class_invite    WHERE class_id = 1;
DELETE FROM qq_binding      WHERE class_id = 1;
DELETE FROM student         WHERE class_id = 1;
DELETE FROM class           WHERE id = 1;
DELETE FROM teacher         WHERE id = 1;
-- 配置表也属于本脚本的重置范围；不清理会在第二次执行时撞 PRIMARY KEY
DELETE FROM xp_config;
DELETE FROM difficulty_factor;
DELETE FROM login_streak_rule;
DELETE FROM xp_limit_config;
DELETE FROM level_def;
DELETE FROM grading_config;

-- ------------------------------------------------------------
-- 1. 教师（1 名，账号 demo.teacher@school.edu.cn / Demo@123）
-- ------------------------------------------------------------
INSERT INTO teacher (id, account, password_hash, name, status, created_at) VALUES
(1, 'demo.teacher@school.edu.cn', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', '王老师', 1, NOW());

-- ------------------------------------------------------------
-- 2. 班级（1 个）
--    class_code = C26A79  班级编号（学生登录用，永不重置）
--    invite = CLASS6    邀请码（可重置，仅用于新生加入）
-- ------------------------------------------------------------
INSERT INTO class (id, class_code, teacher_id, class_name, course_name, status, created_at) VALUES
(1, 'C26A79', 1, '计算机应用基础 2026 秋', '计算机应用基础', 1, NOW());

INSERT INTO class_invite (id, class_id, code, status, expires_at, created_by, created_at) VALUES
(1, 1, 'CLASS6', 1, NULL, 1, NOW());

-- ------------------------------------------------------------
-- 3. 学生（10 名，学号 20260101 ~ 20260110）
-- ------------------------------------------------------------
INSERT INTO student (id, class_id, student_no, name, password_hash, xp_total, level, status, created_at) VALUES
(1,  1, '20260101', '李小明', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(2,  1, '20260102', '张雨欣', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(3,  1, '20260103', '王浩然', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(4,  1, '20260104', '陈思远', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(5,  1, '20260105', '刘一诺', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(6,  1, '20260106', '赵子涵', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(7,  1, '20260107', '周佳怡', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(8,  1, '20260108', '吴俊杰', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(9,  1, '20260109', '郑雅文', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW()),
(10, 1, '20260110', '孙铭泽', '$2b$12$1//BMgPXB0fP.YWCDiXz7.XdEE9YF2gokB0WQV6cNGPi3HuKp55la', 0, 1, 1, NOW());

-- ------------------------------------------------------------
-- 4. QQ 绑定（演示现场走「绑定码」流程，此处留空）
-- ------------------------------------------------------------
-- 现场流程：学生个人中心生成 8 位绑定码 → 群内 @机器人 发送「绑定 <码>」
-- INSERT INTO qq_binding (id, class_id, student_id, qq_openid, status, bound_at, created_at) VALUES ...;

-- ------------------------------------------------------------
-- 5. 成长配置：行为开关与基础经验值
-- ------------------------------------------------------------
INSERT INTO xp_config (code, name, base_xp, enabled) VALUES
('daily_login', '每日首次登录',          10, 1),
('homework',    '完成作业',              20, 1),
('exam',        '参加考试',              50, 1),
('practice',    '刷题（逐题×难度系数）',   1, 1),
('wrong_redo',  '错题重做（错→对）',        6, 1),
('streak',      '连击（每 5 连对）',        5, 1);

-- 难度系数：未分类为基础值 2，高于简单题 1
INSERT INTO difficulty_factor (code, name, factor) VALUES
('easy',    '简单',   1),
('medium',  '中等',   2),
('hard',    '困难',   3),
('unknown', '未分类', 2);

-- 签到连乘规则（第 N 天 = 10 + 5×(N-1)，第 5 天封顶 30）
INSERT INTO login_streak_rule (streak_day, xp) VALUES
(1, 10), (2, 15), (3, 20), (4, 25), (5, 30);
-- 第 6 天及以后按封顶 30 处理；断签重置为第 1 天

-- 防刷与封顶配置
INSERT INTO xp_limit_config (code, value, unit, remark) VALUES
('practice_daily_cap', 200, 'xp/day', '刷题每日经验封顶'),
('streak_daily_cap',    30, 'xp/day', '连击每日经验封顶'),
('min_answer_seconds',   5, 'second', '单题作答低于该时长不计经验'),
('login_daily_once',     1, 'times',  '每日首次登录只计一次');

-- ------------------------------------------------------------
-- 6. 等级头衔表（10 级）
-- ------------------------------------------------------------
INSERT INTO level_def (level, title, min_xp) VALUES
(1,  '见习学者',    0),
(2,  '求知者',    100),
(3,  '探索者',    250),
(4,  '精进者',    450),
(5,  '笃行者',    700),
(6,  '博闻者',   1000),
(7,  '明辨者',   1400),
(8,  '学霸',     1900),
(9,  '学闳',     2500),
(10, '学神',     3200);

-- ------------------------------------------------------------
-- 7. 判分配置（M2 使用；阈值固定写库，不做可调 UI）
-- ------------------------------------------------------------
INSERT INTO grading_config (code, value, remark) VALUES
('confidence_threshold',         '0.60', '合成置信度低于该值进人工复核队列'),
('fill_ai_equivalence_threshold','0.85', '填空 AI 等价档判定阈值'),
('judge_mode_default',           'smart', '默认判题严格度：strict/smart/ai-equivalent'),
('jev_model',                    'typesafe/jev-1.14', 'OpenRouter 判分模型'),
('judge_text_model',             'deepseek-chat', '讲评文本生成模型');

-- 完成。执行后：教师 demo.teacher@school.edu.cn 登录 → 查看邀请码 CLASS6；
-- 学生用 班级编号 C26A79 + 学号 20260101 + Demo@123 登录。
