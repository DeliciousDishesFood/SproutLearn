# QQ 机器人演示数据说明（v1.2）

> 本目录 SQL 只针对**独立演示库**（建议 `sproutlearn_demo` / `demo.db`），不会写入当前 `contract.db`，也不是旧 `seed_data.sql` 的全局删除脚本。

## 一、固定演示凭证

| 角色 | 账号 | 密码 |
|---|---|---|
| 教师 | `demo.teacher@school.edu.cn` | `Demo@123` |
| 班级 | `C26A79` / `计算机网络演示班` | 课程：计算机网络 |
| 学生 | `20260101`–`20260110`（10 人） | `Demo@123` |

学生姓名：李小明、张雨欣、王浩然、陈思远、刘一诺、赵子涵、周佳怡、吴俊杰、郑雅文、孙铭泽。

## 二、数据内容

- 1 个教师、1 个班级、10 个学生、1 个题库、20 道 TCP/IP / OSI / UDP / 三次握手 / 封装题。
- 2 份已发布试卷：
  - `计算机网络基础·第一次作业`（homework，截止为执行时 +90 分钟）；
  - `TCP/IP 随堂练习`（practice，无截止）。
- 作业分布：4 人 submitted/graded、2 人 doing、4 人未开始；教师 `作业` 应显示 `4/10`，未交 6 人。
- 2 份知识文档 + 4 条切片（TCP/UDP、三次握手、OSI、封装），`status=2` 可检索。
- 52 周稀疏活动：20 个离散日期/学生，覆盖近 7 天、近 30 天和 90 天以上；同时写 `answer_record.updated_at` 与 `student_daily_xp`，并配 `xp_ledger`。
- 通知：新作业 + 批改结果。
- `class_bot_config`：`app_id='env'` 占位，群/教师 openid 留空，`last_check_status='never'`；真实 AppID/Secret 只从环境变量读取。
- `qq_binding` 默认不写，现场绑定 1–2 个学生。

## 三、生成与导入

### 1. 生成 SQL（同一数据源）

```powershell
cd E:\ai-dev-projects\SproutLearn\backend
& "C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe" -m scripts.generate_qq_demo_seed
```

生成：

- `docs/demo/seed_qq_demo_v1.2.mysql.sql`
- `docs/demo/seed_qq_demo_v1.2.sqlite.sql`

### 2. 独立 MySQL demo 库

```powershell
# 先只创建空库，不改当前业务库
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS sproutlearn_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
cd E:\ai-dev-projects\SproutLearn\backend
$env:MYSQL_DATABASE="sproutlearn_demo"
& "C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe" -m alembic upgrade head
# 再用 mysql 客户端导入（命令由执行人确认目标库）
mysql -uroot -p sproutlearn_demo < E:\ai-dev-projects\SproutLearn\docs\demo\seed_qq_demo_v1.2.mysql.sql
```

- SQL 使用事务、固定 ID 和 `INSERT IGNORE`，重复执行不会清空/重置非 demo 数据。
- 不 `TRUNCATE`、不全局 `DELETE`、不写真实 openid/secret。
- **本脚本只生成 SQL，不代执行到用户现有库**；是否执行由现场负责人确认目标库。

### 3. SQLite demo（验证用）

```powershell
& "C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe" -m scripts.generate_qq_demo_seed --build-sqlite E:\temporary-work\智能助学平台\demo.db
```

该命令只创建独立 demo.db，不会碰 `contract.db`。

### 4. 只读校验

```powershell
& "C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe" -m scripts.verify_qq_demo --sqlite E:\temporary-work\智能助学平台\demo.db
```

预期断言：1 班 10 学生；作业 4/2/4；知识切片可检索；近 7 天/30 天/90 天以上均有活动；bot_config 开关正确。

## 四、执行前检查

1. 先 `alembic upgrade head`，确认目标库是 `sproutlearn_demo`，不是当前 `sproutlearn`/`contract.db`。
2. 导入后运行 `verify_qq_demo`，PASS 后再登录。
3. 现场首次登录教师和学生，确认 `Demo@123` 可用。
4. 群/教师 openid 现场通过绑定码生成，不写死。
5. 如果本轮未执行 MySQL，只在 SQLite 验证，P13 必须写“仅 SQLite 验证”，不能写“MySQL 已验证”。

## 五、边界

- 不新增依赖、不迁移、不改前端。
- 不写真实 QQ openid、AppSecret、token、密码到 SQL/文档/日志。
- 不把 demo 数据导入现有业务库；重复执行只作用于固定 demo ID。
