// 前端常量：环境变量、错误码映射、展示元数据统一在此，组件内不写魔法数字。
import type {
  AttemptStatus,
  BlankMode,
  PaperKind,
  PaperMode,
  PaperStatus,
  QuestionDifficulty,
  QuestionStatus,
  QuestionType,
} from '@/api/contract'

const env = import.meta.env

function toPositiveInt(raw: string | undefined, fallback: number): number {
  const value = Number(raw)
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback
}

/**
 * 统一派生 API 前缀：无论 env 是不设、`/api`、`/api/v1`、`http://host`、
 * `http://host/api` 还是 `http://host/api/v1`，一律输出一层 `/api/v1`。
 * HTTP 客户端与 SSE 流都引用本常量，避免双前缀。
 */
function normalizeApiBase(raw: string | undefined): string {
  let root = (raw || '/api').trim().replace(/\/+$/, '')
  if (!root) root = '/api'
  if (/\/v1$/.test(root)) return root
  if (/\/api$/.test(root)) return `${root}/v1`
  return `${root}/api/v1`
}

/** 统一 API 前缀，所有业务请求与 SSE 都走 /api/v1。 */
export const API_BASE_URL = normalizeApiBase(env.VITE_API_BASE_URL)

export const ROLE = {
  TEACHER: 'teacher',
  STUDENT: 'student',
} as const

export type Role = (typeof ROLE)[keyof typeof ROLE]

export const STORAGE_KEYS = {
  token: 'sproutlearn.v3.auth.token',
  user: 'sproutlearn.v3.auth.user',
} as const

/** 会话失效时派发到 window 的事件名，供 main.ts 统一跳转登录页。 */
export const SESSION_EXPIRED_EVENT = 'sproutlearn.v3:session-expired'

/** 后端要求强制改密（40303）时派发；main.ts 统一跳强制改密页，不清会话。 */
export const PASSWORD_CHANGE_REQUIRED_EVENT = 'sproutlearn.v3:password-change-required'

export const PAGE_SIZE = 10
export const PAGE_SIZE_MAX = 50
export const PAGE_SIZE_OPTIONS = [10, 20, 50]
export const TOAST_DURATION_MS = 4000

/** 错误码（契约 §1.5）；前端只做映射，不新增业务码。 */
export const ERROR_CODE = {
  OK: 0,
  VALIDATION: 40001,
  UNAUTHORIZED: 40101,
  SESSION_EXPIRED: 40102,
  BAD_CREDENTIALS: 40103,
  ROLE_FORBIDDEN: 40301,
  CLASS_FORBIDDEN: 40302,
  PASSWORD_CHANGE_REQUIRED: 40303,
  ACCOUNT_DISABLED: 40304,
  CLASS_ARCHIVED: 40305,
  NOT_FOUND: 40401,
  STUDENT_NO_EXISTS: 40901,
  INVITE_INVALID: 40902,
  QQ_ALREADY_BOUND: 40903,
  ACCOUNT_EXISTS: 40904,
  BIND_CODE_INVALID: 40905,
  DOC_DUPLICATE: 40906,
  CLASS_LIMIT: 40907,
  QUESTION_BANK_EMPTY: 40908,
  PAPER_PUBLISHED_FORBIDDEN: 40909,
  ATTEMPT_SUBMITTED: 40910,
  PAPER_STATE_CONFLICT: 40911,
  QUESTION_BANK_NOT_EMPTY: 40912,
  QUESTION_BANK_NAME_EXISTS: 40913,
  FILE_TOO_LARGE: 41301,
  IMPORT_TOO_LARGE: 41302,
  UNSUPPORTED_FORMAT: 41501,
  NO_TEXT_LAYER: 42201,
  PARSE_FAILED: 42202,
  IMPORT_FORMAT_ERROR: 42203,
  RATE_LIMITED: 42901,
  INTERNAL_ERROR: 50001,
  DEPENDENCY_UNAVAILABLE: 50301,
} as const

/** 面向用户的错误文案；后端 message 优先，缺省回退本表。 */
export const ERROR_MESSAGES: Record<number, string> = {
  [ERROR_CODE.VALIDATION]: '请检查填写内容，部分字段不符合要求',
  [ERROR_CODE.UNAUTHORIZED]: '请先登录后再继续',
  [ERROR_CODE.SESSION_EXPIRED]: '登录已过期，请重新登录',
  [ERROR_CODE.BAD_CREDENTIALS]: '账号或密码错误，请检查后重试',
  [ERROR_CODE.ROLE_FORBIDDEN]: '当前账号无权执行此操作',
  [ERROR_CODE.CLASS_FORBIDDEN]: '无权访问该班级资源，请确认班级归属',
  [ERROR_CODE.PASSWORD_CHANGE_REQUIRED]: '请先修改临时密码后再继续',
  [ERROR_CODE.ACCOUNT_DISABLED]: '账号已停用，请联系老师处理',
  [ERROR_CODE.CLASS_ARCHIVED]: '班级已归档，仅可查看历史数据',
  [ERROR_CODE.NOT_FOUND]: '资源不存在或已被删除',
  [ERROR_CODE.STUDENT_NO_EXISTS]: '该学号已在本班使用，请更换学号或直接登录',
  [ERROR_CODE.INVITE_INVALID]: '邀请码无效或已失效，请向老师确认后重新输入',
  [ERROR_CODE.QQ_ALREADY_BOUND]: '该 QQ 已绑定其他学号，无法重复绑定',
  [ERROR_CODE.ACCOUNT_EXISTS]: '该账号已注册，请直接登录',
  [ERROR_CODE.BIND_CODE_INVALID]: '绑定码无效或已过期，请重新生成',
  [ERROR_CODE.DOC_DUPLICATE]: '文档已存在，请勿重复上传',
  [ERROR_CODE.CLASS_LIMIT]: '班级数量已达上限，请归档旧班后再创建',
  [ERROR_CODE.QUESTION_BANK_EMPTY]: '题库没有可用题目，请先导入题目或调整组卷条件',
  [ERROR_CODE.PAPER_PUBLISHED_FORBIDDEN]: '试卷已发布，当前内容不可修改',
  [ERROR_CODE.ATTEMPT_SUBMITTED]: '本次作答已提交，不能再修改答案',
  [ERROR_CODE.PAPER_STATE_CONFLICT]: '试卷当前状态不允许该操作',
  [ERROR_CODE.QUESTION_BANK_NOT_EMPTY]: '题库内仍有题目，请先移出或删除题目后再删库',
  [ERROR_CODE.QUESTION_BANK_NAME_EXISTS]: '题库名称已存在，请换一个名称',
  [ERROR_CODE.FILE_TOO_LARGE]: '文件超过大小上限，请压缩后重试',
  [ERROR_CODE.IMPORT_TOO_LARGE]: '单次导入题目过多，请分批导入',
  [ERROR_CODE.UNSUPPORTED_FORMAT]: '文件类型不支持，请上传 PDF、Word、PPT、Markdown 或 TXT',
  [ERROR_CODE.NO_TEXT_LAYER]: '未检测到文字层，请上传可复制文字的 PDF',
  [ERROR_CODE.PARSE_FAILED]: '文档解析失败，请检查文件后重试',
  [ERROR_CODE.IMPORT_FORMAT_ERROR]: '题库文件格式错误，请按模板修正后重试',
  [ERROR_CODE.RATE_LIMITED]: '操作过于频繁，请稍后再试',
  [ERROR_CODE.INTERNAL_ERROR]: '服务器开小差了，请稍后重试',
  [ERROR_CODE.DEPENDENCY_UNAVAILABLE]: '服务暂时不可用，请稍后重试',
}

export type TagTone = 'neutral' | 'primary' | 'accent' | 'success' | 'warning' | 'danger'

export const DOC_STATUS_META: Record<
  number,
  { label: string; tone: TagTone }
> = {
  0: { label: '待处理', tone: 'neutral' },
  1: { label: '解析中', tone: 'warning' },
  2: { label: '可预览', tone: 'success' },
  3: { label: '解析失败', tone: 'danger' },
}

export const QUESTION_TYPE_META: Record<QuestionType, { label: string; short: string; tone: TagTone }> = {
  single: { label: '单选题', short: '单选', tone: 'primary' },
  multiple: { label: '多选题', short: '多选', tone: 'accent' },
  judge: { label: '判断题', short: '判断', tone: 'success' },
  blank: { label: '填空题', short: '填空', tone: 'warning' },
}

export const DIFFICULTY_META: Record<QuestionDifficulty, { label: string; tone: TagTone }> = {
  easy: { label: '简单', tone: 'success' },
  medium: { label: '中等', tone: 'neutral' },
  hard: { label: '困难', tone: 'danger' },
}

export const QUESTION_STATUS_META: Record<QuestionStatus, { label: string; tone: TagTone }> = {
  draft: { label: '草稿', tone: 'neutral' },
  published: { label: '已入卷', tone: 'primary' },
}

/** 题目待复核状态统一文案（契约要求）。 */
export const QUESTION_PENDING_REVIEW_LABEL = '待复核题目'

export const PAPER_STATUS_META: Record<PaperStatus, { label: string; tone: TagTone }> = {
  draft: { label: '草稿', tone: 'neutral' },
  published: { label: '已发布', tone: 'success' },
  closed: { label: '已撤回', tone: 'warning' },
}

export const PAPER_MODE_LABEL: Record<PaperMode, string> = {
  fixed: '固定选题',
  random: '随机组卷',
}

export const PAPER_KIND_META: Record<PaperKind, { label: string; tone: TagTone }> = {
  practice: { label: '练习', tone: 'primary' },
  homework: { label: '作业', tone: 'accent' },
  exam: { label: '考试', tone: 'warning' },
}

export const BLANK_MODE_META: Record<BlankMode, { label: string; short: string; description: string }> = {
  smart: {
    label: '智能判分',
    short: '智能',
    description: '填空题语义相近也得分；低置信答案交由教师复核。',
  },
  strict: {
    label: '严格判分',
    short: '严格',
    description: '填空题仅与标准答案完全一致时得分，不调用语义模型。',
  },
}

export const ATTEMPT_STATUS_META: Record<AttemptStatus, { label: string; tone: TagTone }> = {
  doing: { label: '作答中', tone: 'warning' },
  submitted: { label: '待复核', tone: 'accent' },
  graded: { label: '已复核', tone: 'success' },
}

export const QUESTION_IMPORT_ACCEPT = '.json,.xlsx,.xls,.csv'
export const QUESTION_IMPORT_MAX_MB = 10
export const UPLOAD_ACCEPT = '.pdf,.doc,.docx,.ppt,.pptx,.md,.txt'
export const UPLOAD_MAX_MB = toPositiveInt(env.VITE_UPLOAD_MAX_MB, 50)
