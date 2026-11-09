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

