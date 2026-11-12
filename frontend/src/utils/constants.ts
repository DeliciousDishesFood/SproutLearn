// 前端常量：环境变量统一在此解析，禁止在组件里写业务魔法数字或字符串。
import type {
  BlankMode,
  AttemptStatus,
  PaperKind,
  PaperMode,
  PaperStatus,
  QuestionDifficulty,
  QuestionStatus,
  QuestionType,
} from '@/api/types'
import type { DocStatusValue, Role } from '@/types'

const env = import.meta.env

function toPositiveInt(raw: string | undefined, fallback: number): number {
  const value = Number(raw)
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback
}

/** 本地开发为 http://127.0.0.1:8000，生产为 /api（nginx 同源反代）。 */
export const API_ROOT = (env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '')

/** 统一 API 前缀，所有请求都走 /api/v1。 */
export const API_BASE_URL = API_ROOT.endsWith('/api')
  ? `${API_ROOT}/v1`
  : `${API_ROOT}/api/v1`

export const ROLE = {
  TEACHER: 'teacher',
  STUDENT: 'student',
} as const satisfies Record<string, Role>

export const STORAGE_KEYS = {
  token: 'sproutlearn.auth.token',
  user: 'sproutlearn.auth.user',
} as const

/** 会话失效时派发到 window 的事件名，供 main.ts 统一跳转登录页。 */
export const SESSION_EXPIRED_EVENT = 'sproutlearn:session-expired'

export const PAGE_SIZE = 10
export const PAGE_SIZE_MAX = 50
export const PAGE_SIZE_OPTIONS = [10, 20, 50]
export const DASHBOARD_PAGE_SIZE = 50
export const CHUNK_PREVIEW_CHARS = 400
export const TOAST_DURATION_MS = 4000
export const BIND_COUNTDOWN_TICK_MS = 1000

const rawAllowedExt: string = env.VITE_UPLOAD_ALLOWED_EXT || 'pdf,doc,docx,ppt,pptx,md,txt'

const allowedExt: string[] = rawAllowedExt
  .split(',')
  .map((item) => item.trim().toLowerCase())
  .filter(Boolean)

/** 上传白名单（扩展名不含点）。 */
export const UPLOAD_ALLOWED_EXT = allowedExt
/** input[accept] / 拖拽提示文案。 */
export const UPLOAD_ACCEPT = allowedExt.map((ext) => `.${ext}`).join(',')

export const UPLOAD_MAX_MB = toPositiveInt(env.VITE_UPLOAD_MAX_MB, 50)
export const MAX_TOTAL_UPLOAD_MB = toPositiveInt(env.VITE_MAX_TOTAL_UPLOAD_MB, 100)
export const MAX_FILES_PER_REQUEST = toPositiveInt(env.VITE_MAX_FILES_PER_REQUEST, 20)
export const MAX_CLASSES_PER_TEACHER = toPositiveInt(env.VITE_MAX_CLASSES_PER_TEACHER, 10)
export const TEXT_FIELD_MAX_LEN = toPositiveInt(env.VITE_TEXT_FIELD_MAX_LEN, 80)
export const BIND_CODE_LENGTH = toPositiveInt(env.VITE_BIND_CODE_LENGTH, 8)
export const BIND_CODE_FALLBACK_TTL_SECONDS = 600

/** 错误码唯一清单（契约 §4.2）。 */
export const ERROR_CODE = {
  OK: 0,
  VALIDATION: 40001,
  UNAUTHORIZED: 40101,
  SESSION_EXPIRED: 40102,
  BAD_CREDENTIALS: 40103,
  ROLE_FORBIDDEN: 40301,
  CLASS_FORBIDDEN: 40302,
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

/** 面向用户的错误文案：动词开头、可操作，界面不出现内部错误码。 */
export const ERROR_MESSAGES: Record<number, string> = {
  [ERROR_CODE.VALIDATION]: '请检查填写内容，部分字段不符合要求',
  [ERROR_CODE.UNAUTHORIZED]: '请先登录后再继续',
  [ERROR_CODE.SESSION_EXPIRED]: '登录已过期，请重新登录',
  [ERROR_CODE.BAD_CREDENTIALS]: '账号或密码错误，请检查后重试',
  [ERROR_CODE.ROLE_FORBIDDEN]: '当前账号无权执行此操作',
  [ERROR_CODE.CLASS_FORBIDDEN]: '无权访问该班级资源，请确认班级归属',
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
  [ERROR_CODE.FILE_TOO_LARGE]: `文件超过 ${UPLOAD_MAX_MB}MB 上限，请压缩后重试`,
  [ERROR_CODE.IMPORT_TOO_LARGE]: '单次导入题目过多，请分批导入',
  [ERROR_CODE.UNSUPPORTED_FORMAT]: '文件类型不支持，请上传 PDF、Word、PPT、Markdown 或 TXT',
  [ERROR_CODE.NO_TEXT_LAYER]: '未检测到文字层，请上传可复制文字的 PDF',
  [ERROR_CODE.PARSE_FAILED]: '文档解析失败，请检查文件后重试',
  [ERROR_CODE.IMPORT_FORMAT_ERROR]: '题库文件格式错误，请按模板修正后重试',
  [ERROR_CODE.RATE_LIMITED]: '操作过于频繁，请稍后再试',
  [ERROR_CODE.INTERNAL_ERROR]: '服务器开小差了，请稍后重试',
  [ERROR_CODE.DEPENDENCY_UNAVAILABLE]: '服务暂时不可用，请稍后重试',
}

/** 错误落位：表单字段错误展示在输入框下方，列表错误展示在失败清单行。 */
export const ERROR_FIELD_MAP = {
  [ERROR_CODE.CLASS_LIMIT]: 'create_class_form',
  [ERROR_CODE.INVITE_INVALID]: 'invite_code',
  [ERROR_CODE.STUDENT_NO_EXISTS]: 'student_no',
  [ERROR_CODE.BAD_CREDENTIALS]: 'login_form',
  [ERROR_CODE.UNSUPPORTED_FORMAT]: 'fail_list',
  [ERROR_CODE.FILE_TOO_LARGE]: 'fail_list',
  [ERROR_CODE.DOC_DUPLICATE]: 'fail_list',
  [ERROR_CODE.NO_TEXT_LAYER]: 'fail_list',
  [ERROR_CODE.PARSE_FAILED]: 'fail_list',
} as const

export const DOC_STATUS_META: Record<
  DocStatusValue,
  { label: string; tone: 'neutral' | 'warning' | 'success' | 'danger' }
> = {
  0: { label: '待处理', tone: 'neutral' },
  1: { label: '解析中', tone: 'warning' },
  2: { label: '可预览', tone: 'success' },
  3: { label: '解析失败', tone: 'danger' },
}

export const ROLE_LABEL: Record<Role, string> = {
  teacher: '教师',
  student: '学生',
}

export type TagTone = 'neutral' | 'primary' | 'accent' | 'success' | 'warning' | 'danger'

export const QUESTION_TYPE_META: Record<
  QuestionType,
  { label: string; short: string; tone: TagTone }
> = {
  single: { label: '单选题', short: '单选', tone: 'primary' },
  multiple: { label: '多选题', short: '多选', tone: 'accent' },
  judge: { label: '判断题', short: '判断', tone: 'success' },
  blank: { label: '填空题', short: '填空', tone: 'warning' },
}

export const DIFFICULTY_META: Record<
  QuestionDifficulty,
  { label: string; tone: TagTone }
> = {
  easy: { label: '简单', tone: 'success' },
  medium: { label: '中等', tone: 'neutral' },
  hard: { label: '困难', tone: 'danger' },
}

export const QUESTION_STATUS_META: Record<
  QuestionStatus,
  { label: string; tone: TagTone }
> = {
  draft: { label: '草稿', tone: 'neutral' },
  published: { label: '已入卷', tone: 'primary' },
}

export const PAPER_STATUS_META: Record<PaperStatus, { label: string; tone: TagTone }> = {
  draft: { label: '草稿', tone: 'neutral' },
  published: { label: '已发布', tone: 'success' },
  closed: { label: '已撤回', tone: 'warning' },
}

export const PAPER_MODE_LABEL: Record<PaperMode, string> = {
  fixed: '固定选题',
  random: '随机组卷',
}

/** M3.2 试卷用途：练习 / 作业 / 考试。 */
export const PAPER_KIND_META: Record<PaperKind, { label: string; tone: TagTone }> = {
  practice: { label: '练习', tone: 'primary' },
  homework: { label: '作业', tone: 'accent' },
  exam: { label: '考试', tone: 'warning' },
}

export const BLANK_MODE_META: Record<
  BlankMode,
  { label: string; short: string; description: string }
> = {
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

export const ATTEMPT_STATUS_META: Record<
  AttemptStatus,
  { label: string; tone: TagTone }
> = {
  doing: { label: '作答中', tone: 'warning' },
  submitted: { label: '待复核', tone: 'accent' },
  graded: { label: '已复核', tone: 'success' },
}

/** 题库导入接受 JSON / XLSX / XLS / CSV（表头可由后端同义词识别）。 */
export const QUESTION_IMPORT_ACCEPT = '.json,.xlsx,.xls,.csv'
export const QUESTION_IMPORT_MAX_MB = 10

