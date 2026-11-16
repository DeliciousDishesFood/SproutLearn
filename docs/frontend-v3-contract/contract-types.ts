// 青芽 SproutLearn 新前端 v1 冻结类型（2026-11-15）。
// 字段名一律 snake_case；禁止在组件内改写为 camelCase。
// 传输层统一信封 {code,message,data,request_id,timestamp}，客户端拦截器 code===0 时解包 data。

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id: string
  timestamp: string
}

export interface Paged<T> {
  total: number
  page: number
  page_size: number
  list: T[]
}

// ---------------- API-01 / API-02 / API-04 账号 ----------------

export interface TeacherUser {
  id: number
  role: 'teacher'
  name: string
  account: string
  created_at?: string
}

export interface StudentUser {
  id: number
  role: 'student'
  name: string
  class_id: number
  class_code: string
  student_no: string
  class_name?: string
  level?: number
  xp_total?: number
  qq_bound?: boolean
}

export type AuthUser = TeacherUser | StudentUser

export interface TeacherRegisterPayload {
  account: string
  name: string
  password: string
  email?: string
  phone?: string
}

export interface TeacherLoginPayload {
  role: 'teacher'
  account: string
  password: string
}

export interface StudentLoginPayload {
  role: 'student'
  class_code: string
  student_no: string
  password: string
}

export type LoginPayload = TeacherLoginPayload | StudentLoginPayload

export interface AuthResult {
  token: string
  user: TeacherUser | StudentUser
}

// ---------------- API-05 ~ API-11 班级 ----------------

export interface ClassBrief {
  id: number
  class_code: string
  class_name: string
  course_name: string
}

export interface ClassCreatePayload {
  class_name: string
  course_name: string
}

export interface ClassCreateResult extends ClassBrief {
  invite_code: string
  invite_expires_at: string | null
  created_at: string
}

export interface ClassListItem {
  id: number
  class_code: string
  class_name: string
  course_name: string
  student_count: number
  doc_count: number
  status: number
  created_at: string
}

export interface ClassDetail {
  id: number
  class_code: string
  class_name: string
  course_name: string
  student_count: number
  doc_count: number
  invite_code: string | null
  created_at: string
}

export interface InviteCodeInfo {
  invite_code: string
  status: number
  expires_at: string | null
  created_at: string
}

export interface ResetInviteCodeResult {
  invite_code: string
  created_at: string
}

export interface StudentJoinPayload {
  invite_code: string
  student_no: string
  name: string
  password: string
}

export interface JoinClassResult {
  token: string
  user: StudentUser
  class: ClassBrief
}

export interface StudentListItem {
  id: number
  student_no: string
  name: string
  level: number
  xp_total: number
  qq_bound: boolean
  created_at: string
  last_login_at: string | null
}

// ---------------- API-12 ~ API-16 知识库 ----------------

export interface KnowledgeDocListItem {
  id: number
  title: string
  file_name: string
  file_ext: string
  file_size: number
  status: number
  chunk_count: number
  page_count: number | null
  error_message: string | null
  created_at: string
}

export interface KnowledgeDocDetail extends KnowledgeDocListItem {
  class_id: number
  course_name: string
  error_code: string | null
}

export interface UploadSuccessItem {
  file_name: string
  doc_id: number
  status: number
  chunk_count: number
  page_count: number | null
}

export interface UploadFailItem {
  file_name: string
  error_code: number
  error_message: string
}

export interface UploadResult {
  total: number
  success_list: UploadSuccessItem[]
  fail_list: UploadFailItem[]
}

export interface KnowledgeChunk {
  id: number
  chunk_index: number
  doc_name: string
  chapter_title: string | null
  page_no: number | null
  char_count: number
  content: string
}

// ---------------- API-17 / API-18 / API-19 QQ 绑定 ----------------

export interface QqBindCode {
  code: string
  expires_in: number
  expires_at: string
}

/**
 * API-18 QQ 绑定回调响应（仅机器人服务端以 X-Bot-Secret 调用）。
 * Web 前端不发起、不消费该接口；此处按契约 §7 与后端实际响应声明，
 * 供机器人/联调侧复用类型，并保证 §7 字段核对完整。
 */
export interface QqBindCallbackResult {
  student_id: number
  student_no: string
  class_id: number
  class_code: string
  bound_at: string
}

// ---------------- M2-C 题库 / 组卷 / 作答 / 成绩 ----------------

export type QuestionType = 'single' | 'multiple' | 'judge' | 'blank'
export type QuestionDifficulty = 'easy' | 'medium' | 'hard'
export type QuestionStatus = 'draft' | 'published'
export type PaperStatus = 'draft' | 'published' | 'closed'
export type PaperMode = 'fixed' | 'random'
/** M3.2 试卷用途：练习 / 作业 / 考试，后端默认 practice。 */
export type PaperKind = 'practice' | 'homework' | 'exam'
export type BlankMode = 'smart' | 'strict'
export type AttemptStatus = 'doing' | 'submitted' | 'graded'

export interface QuestionOption {
  key: string
  text: string
}

export interface QuestionItem {
  id: number
  class_id: number
  /** M3.1 每道题必须归属一个题库。 */
  bank_id: number
  bank_name: string | null
  type: QuestionType
  stem: string
  options: QuestionOption[] | null
  answer: unknown
  analysis: string | null
  knowledge_tag: string
  difficulty: QuestionDifficulty
  status: QuestionStatus
  created_at: string
  updated_at: string
}

export interface QuestionBank {
  id: number
  class_id: number
  name: string
  description: string | null
  question_count: number
  created_at: string
  updated_at: string
}

export interface QuestionBankCreatePayload {
  name: string
  description?: string | null
}

export interface QuestionBankUpdatePayload {
  name?: string
  description?: string | null
}

export interface QuestionListQuery extends PageQuery {
  bank_id?: number
  type?: QuestionType
  /** 后端实际参数名为 tag；knowledge_tag 为契约派工名，两个键保持同值。 */
  knowledge_tag?: string
  difficulty?: QuestionDifficulty
  status?: QuestionStatus
  keyword?: string
}

export interface QuestionImportError {
  index: number
  row: number
  column: string
  message: string
}

/** 导入标准字段（与后端 mapping 目标值一致）。 */
export type ImportStandardField =
  | 'type'
  | 'stem'
  | 'options'
  | 'answer'
  | 'analysis'
  | 'knowledge_tag'
  | 'difficulty'

/** 预览逐行结果：normalized 为映射后的标准字段（校验失败时为 null），errors/warnings 定位到本行。 */
export interface QuestionImportRowIssue {
  index?: number
  row?: number
  column: string
  message: string
}

export interface QuestionImportRow {
  index: number
  normalized: Record<string, unknown> | null
  warnings?: QuestionImportRowIssue[]
  errors?: QuestionImportRowIssue[]
}

export interface QuestionImportStats {
  total: number
  valid: number
  invalid: number
}

export interface QuestionImportPreview {
  token: string
  total: number
  valid_count: number
  error_count: number
  errors: QuestionImportError[]
  preview?: Array<Record<string, unknown>>
  /** M2.5 新增：源列名 → 标准字段；mapping_meta 标记 exact/synonym/fuzzy。 */
  mapping?: Record<string, ImportStandardField | string>
  mapping_meta?: Record<string, string>
  unmapped_columns?: string[]
  rows?: QuestionImportRow[]
  stats?: QuestionImportStats
  /** M3.1：指定导入题库时回显；未指定为 null。 */
  bank_id?: number | null
  bank_name?: string | null
  /** M3.1：未指定题库时用文件名去后缀给出的建议库名。 */
  suggested_bank_name?: string
  /** v1.1 AI 智能识别预览：AI 预览为 'ai'；旧模板预览不返回或返回 'template'。 */
  mode?: 'template' | 'ai'
  engine?: 'llm' | 'template' | string
  /** 实际命中模型；未知为 null。 */
  model?: string | null
  /** 是否发生 provider 降级。 */
  degraded?: boolean
  /** 非阻断提示，前端必须展示。 */
  warnings?: string[]
  source_name?: string
  source_chars?: number
  /** 文本或题数被截断；warnings 必须说明原因。 */
  truncated?: boolean
}

/** 提交入参：只带 token 走服务端预览结果；带 rows 时用前端编辑后的行重新校验。 */
export interface QuestionImportCommitPayload {
  token: string
  rows?: Array<Record<string, unknown>>
  /** M3.1：不传则后端自动建「导入题库-{日期}」。 */
  bank_id?: number | null
}

export interface QuestionImportCommit {
  inserted: number
  question_ids: number[]
}

export interface QuestionUpdatePayload {
  type?: QuestionType
  stem?: string
  options?: QuestionOption[] | null
  answer?: unknown
  analysis?: string | null
  knowledge_tag?: string
  difficulty?: QuestionDifficulty
}

/**
 * 讲评响应：派工包写的是 {engine, content}，M2-C 后端实际返回 explanation；
 * 两个字段都声明为可选，界面统一回退，避免任一侧改名时白屏。
 */
export interface QuestionExplainResult {
  engine: 'llm' | 'template' | string
  explanation?: string
  content?: string
  degraded?: boolean
}

/** 工作台/待办用的精简试卷：无 class_id/blank_mode/shuffle。 */
export interface PaperBrief {
  id: number
  title: string
  mode: PaperMode
  kind: PaperKind
  status: PaperStatus
  question_count: number
  total_score: number
  duration_minutes: number
  published_at: string | null
  /** 后端 P0 补丁后下发；补丁前可能缺失，UI 统一按 null 处理。 */
  due_at?: string | null
  created_at: string
}

export interface PaperItem extends PaperBrief {
  class_id: number
  blank_mode: BlankMode
  shuffle: boolean
  /** 后端当前已下发；新前端必须按 string | null 处理。 */
  due_at: string | null
  my_attempt_status?: AttemptStatus | null
}

export interface PaperQuestion {
  id: number
  seq: number
  score: number
  type: QuestionType
  stem: string
  options: QuestionOption[] | null
  answer: unknown
  analysis: string | null
  knowledge_tag: string
  difficulty: QuestionDifficulty
}

export interface PaperBankRef {
  id: number
  name: string
}

export interface PaperDetail extends PaperItem {
  questions: PaperQuestion[]
  /** M3.1：试卷题目涉及的来源题库。 */
  banks: PaperBankRef[]
}

/** 发布响应：在试卷详情上附带班级群通知结果。 */
export interface PaperPublishResult extends PaperDetail {
  group_notice?: GroupNoticeStatus
}

export interface PaperCreatePayload {
  title: string
  mode: PaperMode
  /** M3.2 用途，缺省由后端按 practice 处理。 */
  kind?: PaperKind
  question_ids?: number[]
  /** M3.1：固定组卷与 question_ids 二选一；随机组卷作为抽题范围。 */
  bank_ids?: number[]
  knowledge_tag?: string | null
  difficulty?: QuestionDifficulty | null
  count?: number
  duration_minutes?: number
  shuffle?: boolean
  blank_mode?: BlankMode
  /** 截止时间，ISO 字符串或 null；后端接受 datetime。 */
  due_at?: string | null
}

export interface PaperUpdatePayload {
  title?: string
  duration_minutes?: number
  blank_mode?: BlankMode
  kind?: PaperKind
  /** 传 null 表示清除截止时间；字段可省略表示不修改。 */
  due_at?: string | null
}

/** `GET /attempts/{id}` 只回精简 paper（id/title/duration_minutes/blank_mode），其余字段可选。 */
export interface AttemptPaper {
  id: number
  class_id?: number
  title: string
  mode?: PaperMode
  /** M3.2 试卷用途；resume 响应已稳定下发，按 practice 兜底仅用于旧数据。 */
  kind: PaperKind
  blank_mode: BlankMode
  duration_minutes: number
  status?: PaperStatus
}

export interface AttemptQuestion {
  id: number
  seq: number
  score: number
  type: QuestionType
  stem: string
  options: QuestionOption[] | null
  knowledge_tag: string
  difficulty: QuestionDifficulty
}

export interface AttemptDetail {
  id: number
  paper_id: number
  class_id: number
  student_id: number
  started_at: string
  deadline_at: string | null
  submitted_at: string | null
  status: AttemptStatus
  total_score: number
  full_score: number
  paper: AttemptPaper
  questions: AttemptQuestion[]
  /** M2D：服务端当前时间与剩余秒数，开卷响应同步下发；无时限卷 remaining_seconds 为 null。 */
  server_now?: string
  remaining_seconds?: number | null
}

/** `GET /attempts/{id}` 恢复作答：已存答案 + 服务端时钟，题目不含标准答案。 */
export interface AttemptResume extends AttemptDetail {
  answers: Record<string, unknown>
  server_now: string
  remaining_seconds: number | null
}

export interface AnswerSaveResult {
  attempt_id: number
  question_id: number
  answer: unknown
  updated_at: string
}

export interface AttemptAnswer {
  id: number | null
  answer_record_id: number | null
  question_id: number
  seq: number
  type: QuestionType
  stem: string
  options: QuestionOption[] | null
  standard_answer: unknown
  analysis: string | null
  knowledge_tag: string
  difficulty: QuestionDifficulty
  full_score: number
  raw_answer: unknown
  score: number
  is_correct: boolean
  engine: string
  confidence: number
  needs_review: boolean
  detail: Record<string, unknown>
}

export interface AttemptReview {
  id: number
  answer_record_id: number
  old_score: number
  new_score: number
  comment: string | null
  created_at: string
}

export interface AttemptResult {
  attempt: {
    id: number
    paper_id: number
    class_id: number
    student_id: number
    started_at: string
    deadline_at: string | null
    submitted_at: string | null
    status: AttemptStatus
    total_score: number
    full_score: number
    late: boolean
    needs_review: boolean
  }
  paper: AttemptPaper
  answers: AttemptAnswer[]
  reviews: AttemptReview[]
  grading_ms: number | null
}

/** 复核请求体：后端为单条平铺字段（`answer_record_id` / `new_score` / `comment`）。 */
export interface ReviewItemPayload {
  answer_record_id: number
  new_score: number
  comment?: string
}

export interface PaperAttemptItem {
  id: number
  attempt_id: number
  student_id: number
  student_no: string | null
  student_name: string | null
  status: AttemptStatus
  total_score: number
  full_score: number
  needs_review_count: number
  started_at: string
  submitted_at: string | null
}

export interface MyAttemptItem {
  id: number
  attempt_id: number
  paper_id: number
  paper_title: string | null
  total_score: number
  full_score: number
  status: AttemptStatus
  started_at: string
  submitted_at: string | null
  deadline_at: string | null
}

// ---------------- 查询参数 ----------------

export interface PageQuery {
  page?: number
  page_size?: number
}

export interface ClassListQuery extends PageQuery {
  status?: number
}

export interface StudentListQuery extends PageQuery {
  keyword?: string
}

export interface DocumentListQuery extends PageQuery {
  class_id: number
  status?: number
}

// ---------------- M3.2 工作台 / 成长 / 金句 ----------------

/** 每日活跃：answers 为当日答题数；xp 学生端为经验，教师端另有 active_students。 */
export interface ActivityDay {
  date: string
  answers: number
  xp?: number
  active_students?: number
}

/** /me/activity 与 /classes/{id}/activity 同时下发 items 与 activity 两个同值别名。 */
export interface ActivitySummary {
  weeks: number
  items: ActivityDay[]
  activity: ActivityDay[]
}

/** 等级进度：后端按 level_def 计算，progress_pct 直接用于经验条。 */
export interface LevelInfo {
  level: number
  title: string
  min_xp: number
  next_level: number | null
  next_min_xp: number | null
  xp_to_next: number | null
  progress_pct: number
}

export interface StudentTodayXp {
  login_xp: number
  practice_xp: number
  streak_xp: number
  submission_xp: number
  total_xp: number
  /** 练习经验日封顶，由后端读 xp_config。 */
  cap: number
}

/** 学生待办试卷：与 TeacherWorkbench.recent_papers 共用 PaperBrief。 */
export type StudentPendingPaper = PaperBrief

export interface StudentRecentAttempt {
  attempt_id: number
  paper_id: number
  paper_title: string
  kind: PaperKind
  total_score: number
  full_score: number
  status: AttemptStatus
  needs_review: boolean
  submitted_at: string | null
}

export interface StudentWorkbench {
  student: {
    id: number
    name: string
    class_id: number
    xp_total: number
    streak_days: number
  }
  level: LevelInfo
  xp_total: number
  streak_days: number
  today_xp: number
  today: StudentTodayXp
  /** 后端同时下发 pending / pending_papers 与 recent / recent_scores 两组别名。 */
  pending: StudentPendingPaper[]
  pending_papers: StudentPendingPaper[]
  recent: StudentRecentAttempt[]
  recent_scores: StudentRecentAttempt[]
  activity: ActivityDay[]
}

export interface GrowthLedgerItem {
  id: number
  source: string
  ref_type?: string
  ref_id?: number
  xp: number
  note: string | null
  created_at: string
}

export interface GrowthSummary {
  xp_total: number
  level: LevelInfo
  ledger: GrowthLedgerItem[]
  activity: ActivityDay[]
  /** 后端同时下发 activity / heatmap 同值别名。 */
  heatmap?: ActivityDay[]
}

export interface ClassRankItem {
  student_id: number
  student_no: string
  name: string
  xp_total: number
  level: number
  title: string
}

export interface TeacherWorkbench {
  class_id: number
  pending_review: number
  today_submissions: number
  active_students: number
  average_score: number
  /** 平均得分率 0~1，教师工作台第四卡使用。 */
  average_score_rate: number
  recent_papers: PaperBrief[]
  top_students: ClassRankItem[]
  /** 后端同时下发 top_students / top5 两个同值别名。 */
  top5: ClassRankItem[]
  activity: ActivityDay[]
}

/** GET /quotes/random：任何情况都返回 200，source 标注 shiora|hitokoto|local。 */
export interface QuoteResult {
  text: string
  from: string
  source: 'shiora' | 'hitokoto' | 'local' | string
}

// ---------------- M3.3 QQ 机器人 / 文档中心 ----------------

/** 机器人配置：AppSecret 只由服务端 .env 托管，接口不下发。 */
export type BotChatMode = 'strict' | 'balanced' | 'free'
export type GroupNoticeStatus = 'sent' | 'failed' | 'skipped'

export interface BotConfig {
  class_id: number
  app_id: string | null
  callback_url: string | null
  enabled: boolean
  group_openid: string | null
  teacher_openid: string | null
  teacher_bound_at: string | null
  binding_enabled: boolean
  notify_assignment: boolean
  notify_due_soon: boolean
  mention_missing: boolean
  allow_query_assignments: boolean
  allow_query_scores: boolean
  bot_chat_mode: BotChatMode
  bot_chat_enabled: boolean
  bot_chat_max_chars: number
  last_check_at: string | null
  last_check_status: 'ok' | 'failed' | 'never' | string
  secret_managed_by_env: boolean
}

export interface BotConfigPayload {
  app_id: string
  callback_url?: string | null
  enabled: boolean
  binding_enabled?: boolean
  notify_assignment?: boolean
  notify_due_soon?: boolean
  mention_missing?: boolean
  allow_query_assignments?: boolean
  allow_query_scores?: boolean
  bot_chat_mode?: BotChatMode
  bot_chat_enabled?: boolean
  bot_chat_max_chars?: number
}

export interface BotTestResult {
  ok: boolean
  message: string
  expires_in: number | null
  last_check_at: string | null
  last_check_status: string
}

export interface GroupBindCode {
  code: string
  expires_in: number
  expires_at: string
}

// ---------------- M3.4 通知中心 ----------------

export interface NotificationItem {
  id: number
  recipient_role: string
  recipient_id: number
  class_id: number
  type: string
  title: string
  body: string
  target_path: string | null
  payload: Record<string, unknown> | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface NotificationListResult extends Paged<NotificationItem> {
  items: NotificationItem[]
  unread_count: number
}

export interface UnreadCountResult {
  count: number
}

export interface AnnouncementPayload {
  title: string
  body: string
}

export interface AnnouncementResult {
  recipient_count: number
}

// ---------------- 成长规则开关 ----------------

export interface XpConfigItem {
  code: string
  name: string
  base_xp: number
  enabled: boolean
  overridden: boolean
}

export interface XpConfigUpdatePayload {
  items: Array<{ code: string; enabled: boolean }>
}

export interface XpConfigResponse {
  class_id: number
  items: XpConfigItem[]
  /** 后端同时下发 items / list 同值别名。 */
  list: XpConfigItem[]
}

export interface DocListItem {
  slug: string
  title: string
  summary: string
  updated_at: string | null
}

export interface DocDetail extends DocListItem {
  content: string
  markdown: string
}

