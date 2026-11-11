// 答题本地草稿：刷新页面后先回填已作答内容，再与服务端自动保存对齐。
import type { AttemptDetail, AttemptQuestion } from '@/api/types'
import { defaultAnswerFor } from '@/utils/questions'

/** 逐题自动保存防抖：切题/失焦会立即冲刷，不等待这 800ms。 */
export const ATTEMPT_SAVE_DEBOUNCE_MS = 800

const CACHE_VERSION = 1
const CACHE_PREFIX = 'sproutlearn.m2c.attempt'

export interface AttemptDraftCache {
  version: number
  attempt: AttemptDetail
  answers: Record<string, unknown>
  cached_at: number
}

function cacheKey(attemptId: number): string {
  return `${CACHE_PREFIX}.${attemptId}`
}

export function buildInitialAnswers(
  questions: AttemptQuestion[],
): Record<number, unknown> {
  const result: Record<number, unknown> = {}
  for (const question of questions) {
    result[question.id] = defaultAnswerFor(question.type)
  }
  return result
}

export function readAttemptDraft(attemptId: number): AttemptDraftCache | null {
  try {
    const raw = localStorage.getItem(cacheKey(attemptId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as AttemptDraftCache
    if (
      parsed?.version !== CACHE_VERSION ||
      !parsed.attempt ||
      parsed.attempt.id !== attemptId ||
      !Array.isArray(parsed.attempt.questions) ||
      !parsed.answers
    ) {
      localStorage.removeItem(cacheKey(attemptId))
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function writeAttemptDraft(
  attempt: AttemptDetail,
  answers: Record<number, unknown>,
): void {
  try {
    const payload: AttemptDraftCache = {
      version: CACHE_VERSION,
      attempt,
      answers: { ...answers },
      cached_at: Date.now(),
    }
    localStorage.setItem(cacheKey(attempt.id), JSON.stringify(payload))
  } catch {
    // 存储已满或隐私模式禁用 localStorage：不影响在线自动保存。
  }
}

export function clearAttemptDraft(attemptId: number): void {
  try {
    localStorage.removeItem(cacheKey(attemptId))
  } catch {
    // 忽略存储异常
  }
}
