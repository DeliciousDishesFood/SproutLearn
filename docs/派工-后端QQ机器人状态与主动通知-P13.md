## P13 交付报告

### 一、结论

QQ 主动通知状态细分、失败重试、权限诊断、AI 输出预算与预检增强已完成，核心链路离线测试和真实 LLM 验证通过。

- `group_notice` 保持 `sent/failed/skipped`；新增 `group_notice_detail`，区分权限、频控、超时、网络、配置/绑定/开关等原因。
- 新增教师显式重试接口；失败通知可重试，`attempt_count` 递增，不重复创建 BotNotice，不重新发布试卷。
- 机器人配置测试/预检增加群绑定、最近通知、主动消息权限提示；token/gateway 正常不再等同于主动消息可用。
- QQ AI 输出硬上限 300 字、LLM 等待 6 秒；真实 free/600 配置实测 3.997 秒返回 256 字。
- 目标测试 **4 passed**，全量 **134 passed**，`ruff check app tests scripts` 全绿。
- **真实 QQ 主动消息发送未执行**；未取得群主手机端主动发言权限证据。MySQL 迁移未执行。

### 二、文件与迁移

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/alembic/versions/0012_qq_notice_detail.py` | 新增 | `bot_notice` 增加 `reason`、`error_code`、`error_message`、`attempt_count`、`last_attempt_at` |
| `backend/app/models/bot_notice.py` | 修改 | 同步结构化字段 |
| `backend/app/services/qq_bot/notifier.py` | 修改 | 细分 skipped/failed 原因；持久化详情；`attempt_count`；失败重试；错误码映射；旧 `send_assignment_published` 兼容 |
| `backend/app/services/paper_service.py` | 修改 | 发布返回 `group_notice_detail`；新增 `retry_group_notice` |
| `backend/app/routers/papers.py` | 修改 | 新增 `POST /papers/{paper_id}/group-notice/retry` |
| `backend/app/services/bot_service.py` | 修改 | 配置测试增加 `group_bound/group_openid_tail/active_message_status/active_message_hint/last_notice` |
| `backend/app/services/bot_chat_service.py` | 修改 | 300 字硬上限、6 秒超时、max_tokens 收敛、超时友好文案 |
| `backend/app/config.py` | 修改 | `qq_bot_reply_max_chars=300`、`qq_bot_llm_timeout_seconds=6`、`qq_bot_llm_max_tokens=700` |
| `backend/scripts/qq_demo_preflight.py` | 修改 | 输出 bot_config/最近通知诊断；`--active-send` 需显式 `--online` + `QQ_ACTIVE_SEND_CONFIRM=YES`，默认只读 |
| `backend/tests/test_qq_notice_detail.py` | 新增 | 失败详情、重试、skip、诊断、AI 长度/超时 4 组 |
| `docs/frontend-v3-contract/00-接口契约-v1.md` | 修改 | 追加 v1.5 状态、重试、诊断、AI 预算 |
| `docs/frontend-v3-contract/contract-types.ts` + `frontend-v3/src/api/contract.ts` | 修改 | `GroupNoticeDetail`、`PaperGroupNoticeRetryResult`、`BotTestResult` 可选字段；SHA256 相同 |
| `deploy/db/schema.sql` | 修改 | `bot_notice` 同步新字段 |

未新增依赖、未新建 MQ、未改前端 UI、未提交。

### 三、验收命令与结果

#### 离线测试

| 命令/操作 | 结果 |
|---|---|
| `pytest -q tests/test_qq_notice_detail.py` | **4 passed** |
| `pytest -q` | **134 passed** |
| `ruff check app tests scripts` | **All checks passed** |
| 40034105 发布失败 | `group_notice=failed`，reason=`qq_permission_denied`，error_code=`40034105`，attempt=1，message 含“群主” |
| 显式重试 | 200；`group_notice=sent`，attempt=2，BotNotice 仍 1 条，message_id 写入 |
| notify_assignment 关闭 | `skipped`，reason=`notify_assignment_disabled` |
| 配置测试 | 返回群绑定、末 4 位、active_message_status、权限提示、最近通知；未声称已授权 |
| 旧测试兼容 | `group_notice` 字符串、发布不回滚、due 幂等均保留 |

#### 迁移

| 操作 | 结果 |
|---|---|
| 0012 临时 SQLite | **PASS**；新列存在，旧行保留 `failed`，新字段为默认空/0 |
| MySQL | **未执行**；只做 SQL 静态检查 |

#### 真实 LLM（非 QQ）

| 操作 | 结果 |
|---|---|
| demo DB，`free` + `bot_chat_max_chars=600` | **3.997s / 256 字**，未超 300；未修改数据库配置 |
| 超时假 provider | 返回“缩短问题”提示，不抛栈 |
| 单元测试 QQ 发送 | 全部 fake，不真实发群 |

#### 真实预检

| 模式 | 结果 |
|---|---|
| `qq_demo_preflight --sqlite demo_v15.db --fake-redis` | **PASS**；demo class/config/LLM/deps 全绿 |
| `qq_demo_preflight --online`（host env） | token_ok=true、gateway=true、807ms；**db FAIL**：host 无法用现有凭据连接容器 MySQL |
| `--active-send` | **未执行**；需真实群主权限与显式 `QQ_ACTIVE_SEND_CONFIRM=YES`，本轮不伪造 |

### 四、未做项

- **真实 QQ 主动群消息未验证**；未执行 `--active-send`，无“群主手机端已开启主动发言”的实拍/截图。
- **MySQL 迁移 0012 未执行**；staging/prod 的 `bot_notice` 新列需要先 `alembic upgrade head`。
- 未在真实群重试发布通知；重试接口仅 fake `send_group_message` 验证。
- 未改前端 UI：发布详情展示、失败重试按钮、诊断文案由前端窗口接入。
- 未做告警/自动重试队列；重试是教师显式动作。
- 未对历史 `bot_notice` 批量回填 reason；旧行新字段为空，符合“不批量重发历史通知”。

### 五、风险

1. **主动消息权限仍可能失败**：40034105 是 QQ 平台/群主授权问题，代码只能准确记录并提示，不能绕过；真实演示前必须由群主在手机 QQ 群设置中开启“机器人主动在群聊内发言”。
2. **token/gateway 正常不等于主动消息可用**：预检已明确区分，但现场仍可能 READY 后发布失败。
3. **重试频率**：当前重试为教师显式点击，未加额外冷却；连续点击可能多次请求 QQ，建议前端禁用按钮并观察 `attempt_count`。
4. **旧数据**：迁移前已有 BotNotice 的 `reason/error_code` 为空；前端需兼容 null。
5. **AI 300 字上限**：复杂知识问题可能被截断；比超时失败更适合群聊，但完整性下降。`free` 模式仍可能不基于班级资料。
6. **LLM 6 秒**：网络慢时更早返回友好失败；用户可缩短问题重试。
7. **MySQL 迁移未实测**：字段/索引在 MySQL 的兼容性需在目标库执行后复核。
8. **预检 host 连接**：脚本默认按 `.env` 连接，容器内主机名在 host 不可解析；验收应在 API 容器/正确网络内运行。

### 六、证据路径

- P13 文件：`E:\ai-dev-projects\SproutLearn\docs\派工-后端QQ机器人状态与主动通知-P13.md`
- 目标测试：`E:\temporary-work\智能助学平台\logs\qq-notice-pytest.log`
- 全量测试：`E:\temporary-work\智能助学平台\logs\qq-notice-full-pytest.log`
- 迁移 SQLite：`E:\temporary-work\智能助学平台\logs\v15-migration-sqlite.log`
- 真实 LLM 预算：`E:\temporary-work\智能助学平台\logs\v15-ai-real.log`
- 预检 SQLite：`E:\temporary-work\智能助学平台\logs\v15-preflight-sqlite.log`
- 预检真实 host/online：`E:\temporary-work\智能助学平台\logs\v15-preflight-real-db.log`
- 通知服务：`E:\ai-dev-projects\SproutLearn\backend\app\services\qq_bot\notifier.py`
- 发布/重试：`E:\ai-dev-projects\SproutLearn\backend\app\services\paper_service.py`
- 路由：`E:\ai-dev-projects\SproutLearn\backend\app\routers\papers.py`
- 诊断：`E:\ai-dev-projects\SproutLearn\backend\app\services\bot_service.py`
- AI：`E:\ai-dev-projects\SproutLearn\backend\app\services\bot_chat_service.py`
- 预检：`E:\ai-dev-projects\SproutLearn\backend\scripts\qq_demo_preflight.py`
- 迁移：`E:\ai-dev-projects\SproutLearn\backend\alembic\versions\0012_qq_notice_detail.py`
- 测试：`E:\ai-dev-projects\SproutLearn\backend\tests\test_qq_notice_detail.py`
- 契约：`E:\ai-dev-projects\SproutLearn\docs\frontend-v3-contract\00-接口契约-v1.md`
