# 派工：题库 AI 智能识别导入（后端 / DeepSeek）

> 执行窗口：DeepSeek 后端窗口。  
> 基线提交：`a77fa55 feat(v3): 新前端 v1 接棒，旧 v2 冻结为 board-ui 参考`  
> 先读：`docs/契约-题库AI导入-v1.1.md`（本任务的唯一契约，不得自行改字段）。  
> 项目根：`E:\ai-dev-projects\SproutLearn`；只改 `backend/`，不碰 `frontend-v3/`、不碰旧 `frontend/`。  
> 不要开子 Agent；不要 commit / push；不要重置数据库；不要新增依赖。

---

## 一、背景

旧导入链路：

- 路由：`backend/app/routers/questions.py`
  - `POST /classes/{class_id}/questions/import/preview`
  - `POST /classes/{class_id}/questions/import/commit`
- 解析：`backend/app/services/question_import.py` 的 `parse_import`
  - 只支持 `.json / .xlsx / .xls / .csv`；
  - 表头/列名不标准就抛「题库文件格式错误，请按模板修正后重试」。
- 用户实际文件 `sql题库.xls` 在旧链路上失败；PDF / Word / PPT / Markdown / TXT
  完全不支持。

目标：新增 **AI 智能识别预览**，把非结构化文件抽成文本，交给现有
`ModelRouter` 归一化为题目行，返回与模板预览同构的 `QuestionImportPreview`；
教师确认后仍走现有 commit / token，不自动入库。

现有能力已够，不需要新依赖：

- `backend/requirements.txt` 已有 `pdfplumber==0.11.4`、`pypdf==5.1.0`、
  `python-docx==1.1.2`、`python-pptx==1.0.2`、`openpyxl==3.1.5`、`xlrd==2.0.1`。
- `backend/app/services/llm/router.py` 有 `ModelRouter.chat()`；
  `backend/app/services/llm/registry.py` 有 `build_chain()`；
  `backend/app/services/llm/base.py` 有 `LLMResult` / `AllProvidersFailed`。
- `backend/app/services/question_import.py` 已有
  `normalize_item` / `store_preview` / `load_preview` / `clear_preview`，
  AI 结果直接复用，不要另写一套入库。

---

## 二、改动文件（建议，不要越界）

新增：

- `backend/app/services/question_import_text.py`：文件文本抽取。
- `backend/app/services/question_ai_import.py`：LLM 结构化 + 归一化 + 预览。
- `backend/tests/test_question_ai_import.py`：AI 导入测试。

修改：

- `backend/app/routers/questions.py`：新增 `ai-preview` 路由。
- `backend/app/services/question_service.py`：新增 `ai_preview_import` 业务入口。
- `backend/app/utils/cache_keys.py`：新增 AI 导入限流 key。
- `docs/契约-题库AI导入-v1.1.md` 已由主窗口写好；如实现中发现必须补字段，
  先停下在 P13 里说明，不得擅自加。

不要改：

- `question_import.py` 的 `parse_import` 旧行为（模板导入必须保持原样）。
- `commit_import` 语义、token TTL、错误码映射。
- 任何 v1 路由的返回字段。
- 前端 `contract.ts`（前端窗口负责镜像；后端只保证响应字段与契约一致）。
- `backend/requirements.txt`（无新依赖）。
- 数据库模型/迁移（AI 预览不落库）。

---

## 三、任务清单

### B1. 文本抽取 `question_import_text.py`

实现 `extract_text(filename: str, content: bytes) -> ExtractResult`：

```python
@dataclass
class ExtractResult:
    text: str
    source_name: str
    warnings: list[str]
    chars: int
    pages_or_sheets: int
```

要求：

1. 扩展名大小写不敏感；只接受契约 §2 的格式；图片/未知返回空文本 + 明确 warning，
   由上层转 `42203`。
2. PDF：
   - 优先 `pdfplumber` 逐页 `extract_text()`；单页异常不阻断，累计 warning。
   - 若整份为空，再用 `pypdf` 兜底一次。
   - 最多 50 页；超出截断并 warning。
   - 无文字层（整份空）warning 写「PDF 无文字层，可能是扫描件」。
3. DOCX：`python-docx` 段落 + 表格逐行；最多 30 张表。
4. PPTX：`python-pptx` 遍历 slides/shapes，取 `shape.text`；表格行也取。
5. XLSX/XLS：
   - 每个 sheet 逐行拼接非空单元格，用 ` | ` 分隔；
   - 行前保留 `sheet名!行号` 便于模型定位；
   - 最多 20 个 sheet / 5000 行。
6. CSV：`utf-8-sig` → `utf-8` → `gb18030` 依次 decode；失败返回 warning。
7. JSON：先 `json.loads`；数组或 `{"questions":[...]}` 直接 `json.dumps(ensure_ascii=False)`；
   失败按纯文本处理。
8. TXT/MD：直接 decode（同上编码顺序）。
9. 统一清洗：去 NUL、去首尾空白、连续空行压成 1 个、保留题号/选项换行。
10. 硬上限：20 MB 文件在路由层先挡；文本最多 120,000 字符，超出截断并 warning。
11. 所有解析在 `asyncio.to_thread` 或同步 service 中执行；不要阻塞事件循环。
12. 不写日志正文；只允许记录扩展名、字符数、耗时、页数。

### B2. AI 结构化 `question_ai_import.py`

实现 `ai_preview(db, current, *, class_id, content, filename, bank_id, max_questions)`：

1. `require_owned_class`；`bank_id` 存在时用
   `question_bank_service.resolve_bank`，与旧 preview 同口径。
2. `extract_text`；空文本 / 图片 / 未知格式 → `AppException(IMPORT_FORMAT_ERROR, ...)`。
3. 文本分块：
   - 按段落/换行切，单块约 6,000 字符；
   - 最多 3 块；
   - 每块要求模型返回最多 20 道题；
   - 总量不超过 `max_questions`（默认 50，1–100）。
4. 调 LLM：
   - `router = build_router(get_settings())`（若已有 `build_router` 缓存/工厂，按现有写法）；
   - `messages` 按契约 §5；
   - `temperature=0.1`、`max_tokens=4096`；
   - `AllProvidersFailed` / 超时 → `AppException(DEPENDENCY_UNAVAILABLE, "AI 识别暂不可用，请稍后重试或改用模板导入")`；
   - 单块失败：若已有前一块成功，保留成功块并 warning；全失败才 50301。
5. 解析模型 JSON：
   - 去 ```json fence；取第一个 `{` 到最后一个 `}`；
   - `json.loads` 失败 → 该块记 warning；全部块失败 → `IMPORT_FORMAT_ERROR`；
   - 只接受 `questions` 数组；忽略模型多余字段。
6. 每道题：
   - 用现有 `normalize_item(raw, index, row=index+1)` 校验；
   - `valid` 进 `items`；失败进 `errors`，`message` 用中文；
   - 去重：题干 `strip().casefold()` 相同只保留第一条，后续记 warning；
   - 题型映射按 `normalize_item` 的 `single/multiple/judge/blank`；
   - `confidence` 不落库，只放进 preview 的 `confidence`（可选）。
7. 组装 `parsed`：
```python
{
  "items": items,
  "errors": errors,
  "total": attempted_count,
  "mapping": {},
  "unmapped_columns": [],
  "stats": {"total": attempted_count, "valid": len(items), "invalid": len(errors)},
}
```
8. `token = store_preview(class_id=..., teacher_id=..., parsed=parsed, bank_id=bank.id if bank else None)`。
9. 返回 `QuestionImportPreview`：
   - 现有字段 + `mode="ai"`、`engine="llm"`、`model`、`degraded`、`warnings`、
     `source_name`、`source_chars`、`truncated`；
   - `rows=items`、`preview=items[:20]`；
   - `suggested_bank_name=question_bank_service.suggested_bank_name(filename)`；
   - `bank_id/bank_name` 同旧 preview。
10. 不 commit、不写 `Question` 表。

### B3. 业务入口 `question_service.ai_preview_import`

- 薄封装，调用 `question_ai_import.ai_preview`；
- 保持现有 `preview_import` 不动；
- 统一返回 dict，路由只做 `success(...)`。

### B4. 路由 `routers/questions.py`

新增：

```python
@router.post("/classes/{class_id}/questions/import/ai-preview")
async def ai_preview_import(
    class_id: int,
    file: UploadFile = File(...),
    bank_id: int | None = Form(default=None),
    max_questions: int = Form(default=50, ge=1, le=100),
    current: CurrentUser = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    content = await file.read()
    await file.close()
    if len(content) > 20 * 1024 * 1024:
        raise AppException(ErrorCode.VALIDATION_ERROR, "文件超过 20MB，请拆分后重试")
    return success(question_service.ai_preview_import(...))
```

- 限流：`RATE_AI_IMPORT = "rate:ai_import:{teacher_id}:{date}"`；
  `3 次/分钟`、`30 次/天`；超限 `42901`。
- 仅 `require_teacher`；不要 `get_current_user` 放行学生。
- 路由不要写业务逻辑，全部在 service。

### B5. 测试 `tests/test_question_ai_import.py`

至少覆盖：

1. **成功链路**：`.txt` 含 2 道题；fake LLM 返回合法 JSON；断言
   `code=0`、`mode="ai"`、`valid_count=2`、`rows` 2 条、`token` 非空；
   再用 token 调 `commit_import`，断言 `inserted=2`。
2. **不支持图片**：`.png` → HTTP 422 / code 42203。
3. **空文本**：空 `.txt` → 42203。
4. **LLM 不可用**：monkeypatch router 为无 provider / 抛 `AllProvidersFailed`
   → HTTP 503 / 50301。
5. **模型返回非 JSON**：fake 返回 `"不是 JSON"` → 42203。
6. **部分题非法**：2 道里 1 道缺答案 → `valid_count=1`、`error_count=1`，
   不整体失败。
7. **角色/班级**：学生调用 → 40301；教师非本班 → 40302。
8. **max_questions**：传 0/101 → 40001（或 FastAPI 422 + 40001，按现有异常风格）。
9. **去重**：同一题干两条只留 1 条。
10. **限流**（若实现）：fakeredis 下第 4 次/分钟 → 42901。

测试不要打真实网络；用 fake provider / monkeypatch。可参考
`backend/tests/test_m36_ask_sprout.py` 的 fake LLM 写法。

### B6. 真实 LLM 冒烟（可选，不阻断）

- 若本机 `.env` 有任一 provider key，用一个 `.txt` 题库走真实 `ai-preview`，
  记录：provider/model、耗时、valid_count、warnings。
- 若没有 key：P13 写「真实 LLM 未验证；fake provider 通过」，不要伪装。

### B7. 文档与 P13

- 不改契约字段；实现与契约不一致时，以契约为准或先在 P13 说明。
- P13 写到 `docs/派工-题库AI导入-后端-P13.md`，六段格式：
  1. 结论
  2. 谁做了什么 / 改动文件
  3. 验收命令与结果
  4. 未做项
  5. 风险
  6. 证据路径
- 必须列出：`pytest` 目标测试、全量测试、ruff 触及文件、真实 LLM 是否验证。

---

## 四、验收标准

### 必须通过

```powershell
cd E:\ai-dev-projects\SproutLearn\backend
# 使用项目 venv
C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe -m pytest -q tests/test_question_ai_import.py
C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe -m pytest -q
```

- 目标测试全部通过；
- 全量测试不比基线差（基线 110 passed；若新增导致失败，必须修）；
- `ruff check` 只对本次触及文件通过（仓库历史 221 处基线不在本任务范围，不要顺手改全仓）：
```powershell
C:\Users\OMEN\venvs\sproutlearn-backend\Scripts\python.exe -m ruff check `
  app/services/question_ai_import.py `
  app/services/question_import_text.py `
  app/routers/questions.py `
  app/services/question_service.py `
  tests/test_question_ai_import.py
```

### 手工断言

- `POST .../ai-preview` 用 `.txt` 返回 `code=0`，`mode=ai`，`token` 可 commit；
- `.png` 返回 42203，文案明确「图片识别暂未开放」；
- 没有 LLM key 时返回 50301，不 500；
- 旧 `POST .../preview` 对 `.xlsx/.xls/.csv/.json` 行为不变；
- 旧 `commit` 不传 `rows` 仍能按 token 落库；
- 不新增依赖、不新增迁移、不写题目表（预览阶段）。

---

## 五、边界与禁止

- 不 commit / push；不改 `frontend-v3`、旧 `frontend`、`deploy`。
- 不新增 endpoint（本任务只加 `ai-preview` 这 1 条）。
- 不改旧 `parse_import` 支持列表；不把 AI 逻辑塞进 `question_import.py`。
- 不把文件正文写日志；不落盘上传文件；不返回 provider key。
- 不引入 `pandas`、`numpy`、`tika`、`ocr` 等新依赖。
- 不重置数据库；不修改种子；不跑生产 MySQL。
- 不做前端页面；前端由 Trae 窗口按 `docs/派工-新前端v1.1-UI打磨.md` 执行。

---

## 六、可直接复制给 DeepSeek 的短指令

```text
你是青芽 SproutLearn 的后端窗口。基线 commit a77fa55。
先完整阅读 E:\ai-dev-projects\SproutLearn\docs\契约-题库AI导入-v1.1.md
和 E:\ai-dev-projects\SproutLearn\docs\派工-题库AI导入-后端.md，再动手。
只改 backend/，实现 POST /classes/{class_id}/questions/import/ai-preview：
PDF/Word/PPT/Excel/CSV/JSON/TXT/MD 文本抽取 → 现有 ModelRouter 结构化 →
复用 normalize_item/store_preview 生成 token；不自动入库，复用现有 commit。
不新增依赖、不新增迁移、不改旧 preview/commit 行为、不 commit/push。
按派工文档跑目标测试、全量 pytest、触及文件 ruff，P13 写六段格式。
```
