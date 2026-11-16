// 作答接口（契约 §2.7）：恢复、自动保存、提问、提交、结果、复核。
import { api } from './client'
import type {
  AnswerSaveResult,
  AttemptDetail,
  AttemptPaper,
  AttemptQuestion,
  AttemptResume,
  AttemptResult,
  MyAttemptItem,
  Paged,
  ReviewItemPayload,
} from './contract'

/** GET /attempts/{id} 后端返回嵌套结构，前端在 API 层统一拉平。 */
interface AttemptResumeEnvelope {
  attempt: Omit<AttemptDetail, 'paper' | 'questions' | 'server_now' | 'remaining_seconds'>
  paper: AttemptPaper
  questions: AttemptQuestion[]
  answers: Record<string, unknown>
  server_now: string
  remaining_seconds: number | null
}

export interface AskSproutHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AskSproutSource {
  doc_id: number
  doc_name: string
}

export interface AskSproutPayload {
  question_id: number
  selected_text: string
  message: string
  history: AskSproutHistoryMessage[]
}

export interface AskSproutResult {
  answer: string
  sources: AskSproutSource[]
}

export const attemptsApi = {
  resume(attemptId: number): Promise<AttemptResume> {
    return api
      .get<AttemptResumeEnvelope>(`/attempts/${attemptId}`, { skipGlobalError: true })
      .then((data) => ({
        ...data.attempt,
        paper: { ...data.paper },
        questions: data.questions,
        answers: data.answers ?? {},
        server_now: data.server_now,
        remaining_seconds: data.remaining_seconds,
      }))
  },

  saveAnswer(attemptId: number, questionId: number, answer: unknown): Promise<AnswerSaveResult> {
    return api.put<AnswerSaveResult>(
      `/attempts/${attemptId}/answers/${questionId}`,
      { answer },
      { skipGlobalError: true },
    )
  },

  ask(attemptId: number, payload: AskSproutPayload): Promise<AskSproutResult> {
    return api.post<AskSproutResult>(`/attempts/${attemptId}/ask`, payload, {
      skipGlobalError: true,
    })
  },

  submit(attemptId: number): Promise<AttemptResult> {
    return api.post<AttemptResult>(`/attempts/${attemptId}/submit`, undefined, {
      timeout: 120000,
      skipGlobalError: true,
    })
  },

  result(attemptId: number): Promise<AttemptResult> {
    return api.get<AttemptResult>(`/attempts/${attemptId}/result`, { skipGlobalError: true })
  },

  review(attemptId: number, item: ReviewItemPayload): Promise<AttemptResult> {
    return api.post<AttemptResult>(`/attempts/${attemptId}/reviews`, item, {
      skipGlobalError: true,
    })
  },

  mine(query: { page?: number; page_size?: number } = {}): Promise<Paged<MyAttemptItem>> {
    return api.get<Paged<MyAttemptItem>>('/attempts/mine', {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 20 },
    })
  },
}
