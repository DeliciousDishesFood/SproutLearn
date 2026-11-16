# 青芽 SproutLearn

面向班级教学闭环的智能助学平台：教师资料形成知识库，围绕题库、组卷、作答、AI 讲评、成长反馈与 QQ 机器人提醒串联教学过程。

## 当前主线

- **前端唯一主线：`frontend-v3/`**，Vue 3 + TypeScript + Vite，青柠亮绿与低饱和中性色。
- `frontend/` 已冻结为旧 UI v2 / 原型参考，不再作为开发或生产入口。
- 后端：`backend/`，FastAPI + SQLAlchemy + MySQL/SQLite + Redis。
- QQ：自有 `app.qq_bot_worker`，包含群/学生绑定、作业与成绩查询、催交、通知和知识问答。

## 已交付能力

- 教师注册、学生邀请码入班、班级隔离与 Redis 会话。
- 班级、题库、AI/模板导题、固定/随机组卷、试卷发布与撤回。
- 作答草稿自动保存、客观题判分、主观题复核、AI 讲评与失败重试。
- 知识库上传、切片、检索、“问问小芽”、成长 XP/等级/52 周热力。
- 教师/学生工作台、通知、文档中心与响应式移动端。
- QQ worker 预检、离线全命令 smoke、独立演示 SQL 与录制 runbook。

## 目录

```text
SproutLearn/
├── frontend-v3/        # 新前端主线（5174）
├── frontend/           # 旧前端，冻结参考，不再部署
├── backend/            # FastAPI、QQ worker、Alembic、pytest
├── deploy/             # Docker Compose、MySQL schema、Nginx
├── docs/
│   ├── demo/           # 演示 SQL、数据说明、QQ 录制脚本
│   ├── frontend-v3-contract/
│   └── 派工-*.md
├── PRODUCT.md
└── README.md
```

## 本地开发

### 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

QQ worker（需要真实 `QQ_BOT_APP_ID` / `QQ_BOT_APP_SECRET`，不得写进 SQL 或仓库）：

```powershell
cd backend
.venv\Scripts\python -m app.qq_bot_worker
```

### 新前端

```powershell
cd frontend-v3
npm ci
npm run dev
```

访问 `http://127.0.0.1:5174`。Vite 默认代理到 `http://127.0.0.1:8000`，可用 `VITE_API_TARGET` 覆盖。

## 演示数据

v1.2 演示 SQL 使用独立数据库，包含 1 教师、1 班、10 学生、20 题、2 份试卷、知识文档和稀疏活动：

- `docs/demo/seed_qq_demo_v1.2.mysql.sql`
- `docs/demo/seed_qq_demo_v1.2.sqlite.sql`
- `docs/demo/QQ机器人演示数据说明.md`
- `docs/demo/QQ机器人录制脚本.md`

演示账号：

| 角色 | 账号 | 密码 |
|---|---|---|
| 教师 | `demo.teacher@school.edu.cn` | `Demo@123` |
| 学生 | 班级 `C26A79` + 学号 `20260101–20260110` | `Demo@123` |

先执行 `alembic upgrade head`，再导入到独立 demo 库；不要对现有业务库执行全表清理。SQLite 校验已通过；MySQL SQL 已生成并静态检查，尚未在目标 MySQL demo 库实跑。真实 QQ 群消息也尚未录制，在线预检通过不等于群链路已通过。

## 验证

```powershell
cd backend
.venv\Scripts\pytest -q

cd ..\frontend-v3
npm run typecheck
npm run build
node scripts/contrast-check.mjs
```

当前检查点实测：后端 **122 passed**；新前端 typecheck/build 通过；明暗主题对比度 **42/42 通过**。浏览器验收证据见 `frontend-v3/shots/v1.2/` 与 `frontend-v3/shots/v1.3-growth-track/`。

## Docker Compose

```powershell
Copy-Item .env.example .env
# 填写数据库、Redis、JWT、LLM、QQ 等密钥
docker compose -f deploy/docker-compose.yml run --rm api alembic upgrade head
docker compose -f deploy/docker-compose.yml up -d --build
```

`web` 服务由 `frontend-v3/Dockerfile` 构建，旧 `frontend/` 不再部署。服务包含 MySQL、Redis、Qdrant、API、QQ worker 和新前端 Nginx。

## 下一阶段边界

“账号与班级基础管理”作为独立小版本：先补密码规则、学生改密、教师一次性重置、强制改密、全会话撤销与文档角色过滤，再补教师改密、学生停用/恢复、班级归档/恢复。暂不引入邮箱找回、设备管理、审计中心、超级管理员或家长账号。

## 提交与安全

- `main` 保持可运行；大版本形成一个检查点提交，使用 Conventional Commits。
- 不提交 `.env`、AppSecret、数据库密码、token、真实 openid、上传文件或构建产物。
- 新功能必须带目标测试；涉及契约时同步后端 schema 与 `frontend-v3/src/api/contract.ts` 镜像。
- P13 必须区分已实测、离线验证、在线预检和未做项，不把 mock 写成真实外部成功。
