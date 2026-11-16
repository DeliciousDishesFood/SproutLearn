## P13 交付报告

### 一、结论

后端 v1.2 演示数据与 QQ 机器人录制链路已交付到“可重复导入、可只读校验、可离线全命令回放、可在线预检”的程度。

- 生成 1 教师 / 1 班 `C26A79` / 10 学生 / 20 题 / 2 份已发布试卷 / 2 份知识文档 / 52 周稀疏活动 / 通知 / bot_config 的 MySQL 与 SQLite SQL。
- SQLite demo 校验 **PASS**：作业 submitted/graded=4、doing=2、未开始=4；近 7/30/90 天均有活动；知识切片可检索；无 secret。
- 离线 QQ smoke **PASS**：教师绑定/帮助/作业/作业情况/催交/作业通知；学生绑定/作业/成绩/解绑；AI 知识上下文+10 秒限流。
- 在线预检（token+gateway）**PASS**：token_ok=true、gateway=true、928ms。
- 全量 pytest **122 passed**；D3/D6 目标测试 **6 passed**；触及文件 ruff 全绿。
- **未执行 MySQL demo 库导入**；只做了 MySQL SQL 静态检查与 SQLite 实测。未做真实 QQ 群消息录制（无 QQ 用户端/群操作权限）。

### 二、改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/demo/seed_qq_demo_v1.2.mysql.sql` | 新增 | 生成物：MySQL 演示数据，事务+IGNORE、固定 ID、无全局 DELETE/TRUNCATE |
| `docs/demo/seed_qq_demo_v1.2.sqlite.sql` | 新增 | 生成物：SQLite 同源演示数据 |
| `backend/scripts/generate_qq_demo_seed.py` | 新增 | 同一 Python 数据源生成两方言；`--build-sqlite` 建独立 demo.db |
| `backend/scripts/verify_qq_demo.py` | 新增 | 只读校验 1 班 10 学生、4/2/4、知识切片、52 周活动、bot_config、XP |
| `backend/scripts/qq_demo_preflight.py` | 新增 | 离线检查 env/DB/Redis/demo class/LLM/deps；`--online` token+gateway；`--sqlite/--fake-redis` 本地模式 |
| `backend/scripts/qq_demo_smoke.py` | 新增 | 临时 SQLite+fakeredis 回放 handler，不调真实 QQ |
| `backend/tests/test_qq_demo.py` | 新增 | 教师/学生命令、AI 上下文/限流、通知幂等 |
| `backend/tests/test_d6_health_logout.py` | 新增 | health 字段/fake redis、无/坏/重复 token 登出 200 |
| `docs/demo/QQ机器人演示数据说明.md` | 新增 | 账号、数据、导入/校验/登录说明 |
| `docs/demo/QQ机器人录制脚本.md` | 新增 | 6–8 分钟主线、逐句预期、失败备用、禁止项 |
| `backend/app/routers/health.py` | 修改 | 按 `db.get_bind().dialect.name` 报告 sqlite/mysql；增加 `db_backend/db_name/app_env/jwt_secret_fingerprint`；fake redis 不再误 503 |
| `backend/app/routers/auth.py` | 修改 | logout 使用可选 token：无/坏/重复 token 均 200；合法 token 仍写黑名单 |
| `backend/app/deps.py` | 修改 | 新增 `get_token_claims_optional` |

未改前端、未加业务 endpoint、未加依赖/迁移、未写入现有业务库。

### 三、验收命令与结果

#### SQL / SQLite / MySQL

| 命令/操作 | 结果 |
|---|---|
| `generate_qq_demo_seed` | 生成 MySQL 83KB、SQLite 79KB；同一数据源 |
| 静态扫描 SQL | 无 `DELETE`/`TRUNCATE`，无 Secret/token；仅 password_hash |
| SQLite build + verify | **PASS**：1 班 10 学生、题库1/题20、2 卷、4/2/4、2 文档/4 chunk、活动20天（last7=5、last30=9、older90=9） |
| SQLite XP | 10 学生 xp_total=400、level=3、daily 合计=400 |
| MySQL demo 库 | **未执行**；只做 SQL 静态检查（硬约束：不启动/操作现有 MySQL） |

#### D2 预检

| 模式 | 结果 |
|---|---|
| 默认（当前 host env） | **FAIL**：host 的 `mysql`/`redis` 主机名不可达（未启动用户服务），不是脚本异常 |
| `--sqlite demo.db --fake-redis` | **PASS**：db/redis/deps/demo class/LLM provider 全绿 |
| `--sqlite demo.db --fake-redis --online` | **PASS**：token_ok=true、gateway=true、928ms；未打印 token |
| 真实 QQ 群 | **未验证**：无 QQ 用户端/群操作权限；不写成在线成功 |

#### D3 离线命令

| 命令 | 结果 |
|---|---|
| `python -m scripts.qq_demo_smoke` | **RESULT: PASS**：教师 6 命令、学生 4 命令、AI 上下文/限流 |
| `pytest -q tests/test_qq_demo.py` | **4 passed** |
| `pytest -q tests/test_d6_health_logout.py` | **2 passed** |
| `pytest -q` | **122 passed** |
| `ruff check`（触及文件） | All checks passed |
| D6 health | `db_backend=sqlite`（测试库）、`jwt_secret_fingerprint` 非 secret；fake redis 200 |
| D6 logout | 无 token/坏 token/重复 200/code0；合法 token 后 `/auth/me` 401 |

#### 真实 QQ + LLM（D4）

- **在线预检 token+gateway 通过**；未执行真实 QQ 群消息录制。
- 真实 LLM provider 配置齐全（amd/zhipu/deepseek），但本轮未在真实群录制。
- 离线 smoke 使用 fake LLM；两者分开记录，未把离线当在线。

### 四、未做项

- **未执行 MySQL demo 库导入**；SQL 只生成/静态检查，SQLite 实测通过。
- **未完成真实 QQ 群完整录制**（教师绑定、学生绑定、作业/成绩、催交、作业通知、AI 问答）；无 QQ 用户端/群权限，不能伪造在线。
- **未做真实群通知 40034105 截图**；已有代码/单测记录 failed，未现场录屏。
- **未做 20MB/120k 大文件实测**；AI 导入不是本任务主线。
- 未改前端；未做真实浏览器 1440/1280/375 截图。
- 未做 52 周每一天填满；按要求稀疏 20 天/学生，覆盖近7/30/90+。

### 五、风险

1. **MySQL SQL 未实跑**：方言/字段问题只能在目标 demo 库导入时暴露；P13 不称“MySQL 已验证”。
2. **真实 QQ 未验证**：群权限、真实 openid、主动消息 40034105、@ 能力都可能与离线 smoke 不同。
3. **演示时间依赖**：due_at 用导入时 +90 分钟；录制拖到 90 分钟后会变成已截止，需重新导入或重新发布。
4. **活动稀疏**：20 天/学生是演示形态，不是 52 周完整数据；热力图不会被 364 天填满。
5. **D2 默认预检依赖 host 能解析 `mysql`/`redis`**；本机未启动服务时默认 FAIL 是真实结果，不应改写成 PASS。
6. **Secret/隐私**：SQL 无真实 secret/openid；录制时不得展示 token、完整 openid、密码。
7. **健康检查**：测试库为 sqlite；MySQL 生产健康仍取决于实际连接。fingerprint 只是 secret 哈希前缀，不是 secret。
8. **通知兜底**：主动消息失败仍只记录 failed；现场必须用 `作业通知` 被动补发，不显示“群发成功”。

### 六、证据路径

- P13 文件：`E:\ai-dev-projects\SproutLearn\docs\demo\QQ机器人演示-P13.md`
- MySQL SQL：`E:\ai-dev-projects\SproutLearn\docs\demo\seed_qq_demo_v1.2.mysql.sql`
- SQLite SQL：`E:\ai-dev-projects\SproutLearn\docs\demo\seed_qq_demo_v1.2.sqlite.sql`
- 数据说明：`E:\ai-dev-projects\SproutLearn\docs\demo\QQ机器人演示数据说明.md`
- 录制脚本：`E:\ai-dev-projects\SproutLearn\docs\demo\QQ机器人录制脚本.md`
- 生成器：`E:\ai-dev-projects\SproutLearn\backend\scripts\generate_qq_demo_seed.py`
- 校验器：`E:\ai-dev-projects\SproutLearn\backend\scripts\verify_qq_demo.py`
- 预检器：`E:\ai-dev-projects\SproutLearn\backend\scripts\qq_demo_preflight.py`
- 离线 smoke：`E:\ai-dev-projects\SproutLearn\backend\scripts\qq_demo_smoke.py`
- SQLite verify 输出：`E:\temporary-work\智能助学平台\logs\qq-demo-verify.log`
- 离线 smoke 输出：`E:\temporary-work\智能助学平台\logs\qq-demo-smoke.log`
- 预检输出（SQLite/fake）：`E:\temporary-work\智能助学平台\logs\qq-preflight.log`
- 在线预检输出：`E:\temporary-work\智能助学平台\logs\qq-preflight-online.log`
- D3/D6 测试：`E:\temporary-work\智能助学平台\logs\qq-demo-pytest.log`
- 全量测试：`E:\temporary-work\智能助学平台\logs\demo-full-pytest.log`
- 演示 DB：`E:\temporary-work\智能助学平台\demo_v12.db`
