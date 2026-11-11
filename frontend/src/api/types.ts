// 接口类型唯一来源：字段名逐项对齐契约 §7（snake_case，禁止 camelCase 改写）。

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
export type BlankMode = 'smart' | 'strict'
export type AttemptStatus = 'doing' | 'submitted' | 'graded'

export interface QuestionOption {
  key: string
  text: string
}

export interface QuestionItem {
  id: number
  class_id: number
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

export interface QuestionListQuery extends PageQuery {
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

export interface QuestionImportPreview {
  token: string
  total: number
  valid_count: number
  error_count: number
  errors: QuestionImportError[]
  preview: Array<Record<string, unknown>>
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

export interface PaperItem {
  id: number
  class_id: number
  title: string
  mode: PaperMode
  blank_mode: BlankMode
  duration_minutes: number
  shuffle: boolean
  question_count: number
  total_score: number
  status: PaperStatus
  published_at: string | null
  created_at: string
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

export interface PaperDetail extends PaperItem {
  questions: PaperQuestion[]
}

export interface PaperCreatePayload {
  title: string
  mode: PaperMode
  question_ids?: number[]
  knowledge_tag?: string | null
  difficulty?: QuestionDifficulty | null
  count?: number
  duration_minutes?: number
  shuffle?: boolean
  blank_mode?: BlankMode
}

export interface PaperUpdatePayload {
  title?: string
  duration_minutes?: number
  blank_mode?: BlankMode
}

export interface AttemptPaper {
  id: number
  class_id: number
  title: string
  mode: PaperMode
  blank_mode: BlankMode
  duration_minutes: number
  status: PaperStatus
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

export interface ReviewItemPayload {
  answer_record_id: number
  new_score: number
  comment?: string
}

/** 派工包请求体为 {items:[...]}；当前后端为单条平铺，client 层已在同一次请求里兼容两种键。 */
export interface ReviewRequestPayload {
  items: ReviewItemPayload[]
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

