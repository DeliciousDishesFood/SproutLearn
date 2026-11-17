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
- 账号安全闭环：统一密码规则、自助改密、一次性临时密码、强制改密、全会话撤销、学生停用与班级归档。
- QQ 主动通知记录 `sent/failed/skipped` 及结构化原因，支持教师显式重试接口；前端通知详情与重试按钮尚未接入。

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

当前检查点实测：后端 **134 passed**；新前端 typecheck/build 通过；明暗主题对比度 **42/42**；v1.5 自包含浏览器夹具 **33/33 PASS**。这些数据不等于真实 QQ 主动群通知已验收。

## Docker Compose

```powershell
Copy-Item .env.example .env
# 填写数据库、Redis、JWT、LLM、QQ 等密钥
docker compose -f deploy/docker-compose.yml run --rm api alembic upgrade head
docker compose -f deploy/docker-compose.yml up -d --build
```

`web` 服务由 `frontend-v3/Dockerfile` 构建，旧 `frontend/` 不再部署。服务包含 MySQL、Redis、Qdrant、API、QQ worker 和新前端 Nginx。

## 当前版本与演示边界

- 当前主线为 v1.5：`frontend-v3` 演示视觉与「问问小芽」打磨，以及 QQ 通知结构化状态、AI 群聊输出预算与显式重试后端。
- 当前 Docker/目标 MySQL 必须先执行 `alembic upgrade head`，使 `0012_qq_notice_detail` 生效。
- 普通 `@机器人` 的“帮助、作业、成绩”是被动回复，可作为稳定演示主线；balanced + 200 字的 AI 知识问答已有真实 LLM 验证。
- 主动作业通知与普通 @ 回复使用不同权限。群主需在最新版手机 QQ 中开启“机器人主动在群聊内发言”，教师发布作业后系统才能自动同步到班级群。
- 真实主动群通知必须在彩排时验收；若现场失败，展示系统返回的真实权限原因并改用 `@机器人 作业` 继续，不伪造群消息。

## 团队信息

参赛团队：青芽 SproutLearn 项目组。项目分工覆盖产品与交互、前端工程、后端与 AI 链路、测试与演示；参赛成员及指导教师以大赛官网报名材料为准，公开仓库不重复展示个人敏感信息。

## 比赛材料

- 提交清单：`docs/比赛/提交清单.md`
- 5–8 分钟逐秒演讲稿：`docs/比赛/演讲稿.md`
- 技术文档源稿与 11 页 PDF：`docs/比赛/技术文档.md`、`docs/比赛/SproutLearn技术文档.pdf`
- v1.5 实测与未验收边界：`docs/v1.5-演示与QQ检查点验收.md`

## 提交与安全

- `main` 保持可运行；大版本形成一个检查点提交，使用 Conventional Commits。
- 不提交 `.env`、AppSecret、数据库密码、token、真实 openid、上传文件或构建产物。
- 新功能必须带目标测试；涉及契约时同步后端 schema 与 `frontend-v3/src/api/contract.ts` 镜像。
- P13 必须区分已实测、离线验证、在线预检和未做项，不把 mock 写成真实外部成功。
