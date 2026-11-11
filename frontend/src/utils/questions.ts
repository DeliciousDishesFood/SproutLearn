// 题库展示工具：答案格式化、默认作答结构、判空与分数显示。
import type {
  QuestionOption,
  QuestionType,
} from '@/api/types'

function optionText(key: string, options: QuestionOption[] | null | undefined): string {
  const option = options?.find((item) => item.key === key)
  return option ? `${key}. ${option.text}` : key
}

export function formatAnswer(
  value: unknown,
  type: QuestionType,
  options: QuestionOption[] | null | undefined,
): string {
  if (value === null || value === undefined || value === '') return '未作答'
  if (Array.isArray(value) && value.length === 0) return '未作答'

  if (type === 'single') return optionText(String(value), options)
  if (type === 'multiple') {
    const keys = Array.isArray(value) ? value.map(String) : String(value).split(',')
    const cleaned = keys.map((key) => key.trim()).filter(Boolean)
    return cleaned.length > 0 ? cleaned.map((key) => optionText(key, options)).join('、') : '未作答'
  }
  if (type === 'judge') {
    if (value === true || String(value).toLowerCase() === 'true') return '正确'
    if (value === false || String(value).toLowerCase() === 'false') return '错误'
    return String(value)
  }
  if (Array.isArray(value)) return value.map((item) => String(item)).join('；') || '未作答'
  return String(value)
}

export function defaultAnswerFor(type: QuestionType): unknown {
  if (type === 'multiple') return []
  if (type === 'blank') return ['']
  if (type === 'judge') return null
  return ''
}

export function isAnswerEmpty(type: QuestionType, value: unknown): boolean {
  if (type === 'multiple') return !Array.isArray(value) || value.length === 0
  if (type === 'blank') {
    if (!Array.isArray(value)) return !String(value ?? '').trim()
    return value.every((item) => !String(item ?? '').trim())
  }
  if (type === 'judge') return value === null || value === undefined
  return !String(value ?? '').trim()
}

export function formatScore(value: number | null | undefined): string {
  return String(Number(value ?? 0))
}

/** 取答案里的选项 key 列表，供编辑抽屉回填多选/单选。 */
export function answerKeys(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item))
  if (value === null || value === undefined || value === '') return []
  return [String(value)]
}
