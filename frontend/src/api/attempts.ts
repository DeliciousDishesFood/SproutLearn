// 作答接口（M2-C/M2-D）：恢复、自动保存、提交、结果、教师复核、我的成绩。
import { api } from '@/api/client'
import type {
  AnswerSaveResult,
  AttemptResume,
  AttemptResult,
  MyAttemptItem,
  Paged,
  ReviewItemPayload,
} from '@/api/types'

export const attemptsApi = {
  /** GET /attempts/{id}：恢复已存答案与服务端时钟；学生本人/同班教师，跨班 40302。 */
  resume(attemptId: number): Promise<AttemptResume> {
    return api.get<AttemptResume>(`/attempts/${attemptId}`, { skipGlobalError: true })
  },

  /** 后端请求体为单字段 answer（M2B 契约）。 */
  saveAnswer(attemptId: number, questionId: number, answer: unknown): Promise<AnswerSaveResult> {
    return api.put<AnswerSaveResult>(
      `/attempts/${attemptId}/answers/${questionId}`,
      { answer },
      { skipGlobalError: true },
    )
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

  /** 教师复核：后端为单条平铺字段，直接发送 answer_record_id / new_score / comment。 */
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
