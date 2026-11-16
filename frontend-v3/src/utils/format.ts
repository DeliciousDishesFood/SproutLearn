// 展示格式化：时间、答案、状态文案与数值。字段名保持契约 snake_case。
import type {
  AttemptStatus,
  PaperKind,
  PaperStatus,
  QuestionDifficulty,
  QuestionType,
} from '@/api/contract'

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const raw = value.trim()
  if (!raw) return '—'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  const pad = (n: number): string => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number): string => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function formatAnswer(value: unknown, type?: QuestionType): string {
  if (value === null || value === undefined || value === '') {
    return type === 'blank' ? '（空）' : '未作答'
  }
  if (type === 'judge' && typeof value === 'boolean') return value ? '正确' : '错误'
  if (Array.isArray(value)) return value.length ? value.map((item) => String(item)).join('、') : '未作答'
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    if (typeof record.text === 'string') return record.text
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

export function formatFileSize(size: number | null | undefined): string {
  if (!size || size <= 0) return '—'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

export function formatPercent(rate: number | null | undefined, digits = 0): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return '—'
  return `${(rate * 100).toFixed(digits)}%`
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return '0'
  return Number.isInteger(score) ? String(score) : score.toFixed(2)
}

export const PAPER_STATUS_LABEL: Record<PaperStatus, string> = {
  draft: '草稿',
  published: '已发布',
  closed: '已撤回',
}

export const ATTEMPT_STATUS_LABEL: Record<AttemptStatus, string> = {
  doing: '作答中',
  submitted: '待复核',
  graded: '已复核',
}

export const PAPER_KIND_LABEL: Record<PaperKind, string> = {
  practice: '练习',
  homework: '作业',
  exam: '考试',
}

export const QUESTION_TYPE_LABEL: Record<QuestionType, string> = {
  single: '单选',
  multiple: '多选',
  judge: '判断',
  blank: '填空',
}

export const DIFFICULTY_LABEL: Record<QuestionDifficulty, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

export const DOC_STATUS_LABEL: Record<number, string> = {
  0: '待处理',
  1: '解析中',
  2: '可预览',
  3: '解析失败',
}

export function docStatusTone(status: number): 'lime' | 'amber' | 'danger' | 'plain' {
  if (status === 2) return 'lime'
  if (status === 3) return 'danger'
  if (status === 1) return 'amber'
  return 'plain'
}

export function paperStatusTone(status: PaperStatus): 'lime' | 'amber' | 'plain' {
  if (status === 'published') return 'lime'
  if (status === 'draft') return 'amber'
  return 'plain'
}

export function attemptStatusTone(status: AttemptStatus): 'lime' | 'amber' | 'plain' {
  if (status === 'graded') return 'lime'
  if (status === 'submitted') return 'amber'
  return 'plain'
}

export function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

export function todayLabel(): string {
  const now = new Date()
  const week = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][now.getDay()]
  return `${week} · ${now.getMonth() + 1} 月 ${now.getDate()} 日`
}
