## P13 交付报告

### 一、结论

题库 AI 智能识别导入后端已完成：新增 `POST /api/v1/classes/{class_id}/questions/import/ai-preview`，支持 PDF/Word/PPT/Excel/CSV/JSON/TXT/MD 文本抽取 → 现有 `ModelRouter` 结构化 → `normalize_item` 校验 → 复用旧 `store_preview` token；不自动入库，教师确认后仍走原 commit。

- 真栈 `.txt` AI 预览成功：`valid_count=2`、`model=self-dploy/DeepSeek-V4-Flash`、token 可 commit，`inserted=2`。
- `.png` 返回 422 / 42203“图片识别暂未开放…”。
- 全量 `pytest -q` **116 passed**；目标 `test_question_ai_import.py` **6 passed**；触及文件 ruff 全绿。
- 未新增依赖、迁移、前端改动；旧 `preview` / `commit` 行为未改。

### 二、谁做了什么 / 改动文件

**后端窗口（DeepSeek）**

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/services/question_import_text.py` | 新增 | PDF（pdfplumber→pypdf 兜底、50 页）、DOCX（段落+30 表）、PPTX、XLSX/XLS（20 sheet/5000 行）、CSV（UTF-8/GB18030）、JSON、TXT/MD；120k 字符截断；图片/未知格式 warning；不写正文日志 |
| `backend/app/services/question_ai_import.py` | 新增 | 文本分块（≤3×6000）、LLM JSON 解析、`normalize_item`、去重、错误行、token、AI 预览字段、3 次/分钟 + 30 次/天限流 |
| `backend/tests/test_question_ai_import.py` | 新增 | 成功/commit、图片、空文本、LLM 不可用、非 JSON、部分非法、去重、权限、max_questions、限流 |
| `backend/app/routers/questions.py` | 修改 | 新增 `ai-preview` 路由；20MB 路由层拦截；`require_teacher` |
| `backend/app/services/question_service.py` | 修改 | `ai_preview_import` 薄封装，`asyncio.to_thread` 执行同步解析/LLM |
| `backend/app/utils/cache_keys.py` | 修改 | AI 导入分钟/日限流 key |

未改：`question_import.py` 的 `parse_import`、`commit_import` 语义、token TTL、旧 preview 字段、前端、依赖、数据库模型/迁移。

### 三、验收命令与结果

| 命令/操作 | 结果 |
|---|---|
| `pytest -q tests/test_question_ai_import.py` | **6 passed** |
| `pytest -q` | **116 passed** |
| `ruff check`（触及 5 文件） | All checks passed |
| 真栈 `.txt` ai-preview | 200；`mode=ai`、`engine=llm`、`valid_count=2`、`model=self-dploy/DeepSeek-V4-Flash` |
| 真栈 commit token | 200；`inserted=2` |
| 真栈 `.png` | 422 / 42203；“图片识别暂未开放…” |
| 旧 `.xlsx/.xls/.csv/.json` preview | 全量旧测试通过，行为未改 |
| 旧 commit 不传 rows | 全量旧测试通过 |
| 预览阶段写题 | 测试断言 `Question` 表为 0；commit 后才 2 |
| 20MB | 路由层拦截，`VALIDATION_ERROR`；目标测试未构造 20MB 文件 |
| 限流 | fake Redis 第 4 次/分钟 42901；单测通过 |

### 四、未做项

- PDF / Word / PPT / XLSX / XLS / CSV / JSON 的**真实样本**未逐个手工验收；已实现解析器，但目标测试主要覆盖 `.txt` 与图片/空文本。建议运营用真实 `sql题库.xls` 补一次手工。
- 图片 OCR/视觉识别未做（契约明确 v1.1 不做）。
- 前端 AI 导入 UI 未做（前端窗口负责）。
- 20MB 文件与 120k 文本截断未在真栈构造大文件验证；代码路径已实现。
- 未做 daemon/后台异步任务；请求内最多 3 次 LLM 调用。
- 真实 LLM 只验证 1 个 `.txt` 样本（2 题），未覆盖复杂表格/多题型真实文件。

### 五、风险

1. **LLM JSON 不稳定**：模型可能返回非 JSON、少字段或超长；已按块 warning/42203 处理，但复杂题库可能需要重试或切模板导入。
2. **单请求耗时**：最多 3 块 × LLM，可能接近网关超时；当前同步等待，无任务队列。
3. **提示注入**：系统提示把文档当数据，但模型仍可能执行文档内指令；结构化结果会经 `normalize_item` 兜底，不能完全防注入。
4. **截断**：PDF 50 页、120k 字符、3 块、max_questions 任一截断会置 `truncated=true` 并写 warning，前端必须展示。
5. **去重口径**：重复题干只保留第一条并 warning，不单独计入 errors；`error_count` 按 attempted-valid，可能大于 errors 数组长度。
6. **限流**：3 次/分钟内第 4 次 42901；Redis 故障放行，可能短时超限。
7. **解析器**：扫描 PDF 无文字层、复杂表格/合并单元格可能丢结构；图片明确 42203，不做 OCR。
8. **错误码**：20MB 路由层用 HTTP400/40001；`max_questions` 越界由 FastAPI 校验返回 40001；前端按统一信封处理。

### 六、证据路径

- P13 文件：`E:\ai-dev-projects\SproutLearn\docs\派工-题库AI导入-后端-P13.md`
- 目标测试日志：`E:\temporary-work\智能助学平台\logs\question-ai-pytest.log`
- 全量测试日志：`E:\temporary-work\智能助学平台\logs\question-ai-full-pytest.log`
- 真栈日志：`E:\temporary-work\智能助学平台\logs\question-ai-smoke.log`
- 真栈脚本：`E:\temporary-work\智能助学平台\smoke_question_ai.py`
- 文本抽取：`E:\ai-dev-projects\SproutLearn\backend\app\services\question_import_text.py`
- AI 结构化：`E:\ai-dev-projects\SproutLearn\backend\app\services\question_ai_import.py`
- 路由：`E:\ai-dev-projects\SproutLearn\backend\app\routers\questions.py`
- 业务入口：`E:\ai-dev-projects\SproutLearn\backend\app\services\question_service.py`
- 测试：`E:\ai-dev-projects\SproutLearn\backend\tests\test_question_ai_import.py`
- 契约：`E:\ai-dev-projects\SproutLearn\docs\契约-题库AI导入-v1.1.md`
