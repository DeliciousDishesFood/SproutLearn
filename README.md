# 青芽 SproutLearn

班级级教学辅助系统 M1 后端与部署工程：教师注册/登录、班级与邀请码、学生加入/登录、
知识库批量上传与切片预览、QQ 绑定接口。目标是把“可运行、可验收、可继续开发”的工程骨架
先落地，M2～M5 的题库、判分、检索与机器人业务不在本期实现。

## M1 范围

### 已完成

- FastAPI 工程骨架：Settings、日志、统一响应体、全局异常、`X-Request-Id`、CORS、健康检查。
- 13 张业务表：`deploy/db/schema.sql` + Alembic 初始迁移。
- 鉴权：JWT（HS256）+ Redis 会话（滑动过期）+ 教师/学生角色依赖。
- 班级：创建（`class_code` + 首个 `invite_code` 同事务）、列表、详情、学生列表。
- 邀请码：查询、重置（`class` 表行锁，旧码立即失效）。
- 学生：邀请码加入、班级编号 + 学号 + 密码登录。
- 知识库：多文件上传、逐文件独立事务、白名单/大小/去重/扫描件拦截、切片落库与预览。
- QQ：8 位一次性绑定码、机器人回调绑定、改绑、解绑。
- pytest 冒烟测试与部署文件（prod/dev compose、nginx）。

### 明确未做（M2～M5）

题库导入、考试发布、判分、jev 接入、问答检索、机器人消息处理、经验值计算、学情看板。
`app/services/retrieval`、`grading`、`bot` 仅为空包 + README；`VECTOR_INDEX_ENABLED=false`。

## 技术栈

- Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / PyMySQL
- MySQL 8.0 / Redis 7 / Qdrant v1.12.4（M1 不写向量）
- pytest + fakeredis（测试默认 SQLite，无需外部服务）

## 环境要求

- Docker Desktop（含 Docker Compose v2）
- Python 3.11（仅本地跑测试/调试时需要）
- Node 18+（前端窗口使用，本仓库后端不依赖）

## 一键启动（生产 compose）

```bash
# 1. 复制环境变量并填写 SECRET_KEY / MYSQL_PASSWORD / MYSQL_ROOT_PASSWORD / REDIS_PASSWORD / BOT_SHARED_SECRET
cp .env.example .env

# 2. 建库迁移
docker compose -f deploy/docker-compose.yml run --rm api alembic upgrade head

# 3. 启动
docker compose -f deploy/docker-compose.yml up -d --build

# 4. 验证
curl http://127.0.0.1/health
```

> 前端镜像由 `frontend/Dockerfile` 提供；若前端窗口尚未交付，可先只启动 api/mysql/redis/qdrant
> （`docker compose -f deploy/docker-compose.yml up -d mysql redis qdrant api`）。
>
> 说明：Compose 的项目目录默认是 `deploy/`，因此服务密钥统一通过 `env_file: ../.env`
> 注入，而不是用 `${MYSQL_PASSWORD}` 插值（否则从仓库根执行时插值为空）。
> `MYSQL_ROOT_PASSWORD` 与 `MYSQL_PASSWORD` 建议填写相同值。

## 开发启动（必须双 `-f`）

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml up -d
cd frontend && npm run dev
```

- 后端在 `api` 容器内运行并开启 `--reload`，**宿主不要再起 uvicorn**（会端口冲突）。
- 端口：API `127.0.0.1:8000`、MySQL `127.0.0.1:13306`、Redis `127.0.0.1:16379`、
  Qdrant `127.0.0.1:6333/6334`、前端 `127.0.0.1:5173`。
- `docker-compose.dev.yml` 顶部已注明“覆盖补丁，必须双 `-f`”。

## API 文档

启动后访问：

- Swagger UI：`http://127.0.0.1:8000/docs`
- OpenAPI JSON：`http://127.0.0.1:8000/openapi.json`
- 健康检查：`http://127.0.0.1:8000/health`（派工词别名 `/api/v1/health` 同样可用，不进入 OpenAPI）

20 个接口严格对齐契约 §7；字段统一 `snake_case`，响应统一为：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "8f3c1a2b-...",
  "timestamp": "2026-11-07 18:40:00"
}
```

## 测试

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

- 默认使用 SQLite + fakeredis，无需先启动 Docker；覆盖 8 个契约用例：
  注册、建班、加入、重置旧码失效、混合上传、切片 `doc_name`、改绑、越权 403。
- 真实 MySQL 表结构用 `deploy/db/schema.sql` 或 `alembic upgrade head` 验证。
- 测试环境变量在 `backend/tests/conftest.py` 中集中设置，不读取生产 `.env`。

## 演示数据

M1 不内置演示数据初始化功能。执行顺序：

1. `deploy/db/schema.sql` 或 `alembic upgrade head`
2. `E:\ai-dev-projects\智能助学平台\docs\demo\seed_data.sql`

说明脚本：`backend/app/scripts/seed_demo.py`（只打印路径，不执行数据写入）。

## 常见问题

| 问题 | 处理 |
|---|---|
| 13306 / 16379 / 8000 / 5173 端口占用 | 关闭占用进程，或调整 `docker-compose.dev.yml` 端口映射 |
| 上传目录权限 | 确认 `uploads_data` 卷或 `../uploads` 目录可写；`UPLOAD_DIR` 默认 `/data/uploads` |
| Qdrant 首次启动慢 | M1 `VECTOR_INDEX_ENABLED=false`，Qdrant 未就绪不影响 `/health` 的 mysql/redis 判定 |
| 双 `-f` 只传一个 | dev 文件是覆盖补丁，单独执行会因 mysql/redis/qdrant 缺 `image` 报错 |
| 前端未构建 | `web` 服务依赖 `frontend/Dockerfile`；可先只启动后端四服务 |

## 目录结构

```text
SproutLearn/
├── backend/                 # FastAPI 后端（本窗口）
│   ├── app/                 # 路由/服务/仓储/模型/策略
│   ├── alembic/             # 初始迁移
│   ├── tests/               # pytest 冒烟
│   ├── Dockerfile
│   └── requirements.txt
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── db/schema.sql
│   └── nginx/
├── .env.example
├── .gitignore
└── README.md
```

## 安全与约束

- 不提交 `.env`、真实密钥、上传文件、截图、构建产物。
- 业务阈值/时长/条数/长度全部走 `.env`；代码中只保留流程常量。
- 所有仓储查询带 `class_id` 作用域；越权返回 `40302`，不泄露跨班数据。
- M1 不引入 MinIO / OSS / K8s / 消息队列 / Celery，不做管理员角色、多学校入驻。
- 验收清单：`E:\ai-dev-projects\智能助学平台\dev-docs\智能助学平台M1落地需求文档（V1.0）.md` 第 11 章。
