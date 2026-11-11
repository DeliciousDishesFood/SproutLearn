// 作答接口（M2-C）：自动保存、提交、结果、教师复核、我的成绩。
import { api } from '@/api/client'
import type {
  AnswerSaveResult,
  AttemptResult,
  MyAttemptItem,
  Paged,
  ReviewItemPayload,
} from '@/api/types'

export const attemptsApi = {
  /** 派工包字段为 raw_answer，当前后端为 answer；两个键同值发送，兼容两侧。 */
  saveAnswer(attemptId: number, questionId: number, rawAnswer: unknown): Promise<AnswerSaveResult> {
    return api.put<AnswerSaveResult>(
      `/attempts/${attemptId}/answers/${questionId}`,
      { raw_answer: rawAnswer, answer: rawAnswer },
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

  /**
   * 派工包为 {items:[...]} 批量复核，当前 M2-C 后端为单条平铺。
   * 一次请求同时携带单条字段与单元素 items，两种后端都能落库。
   */
  review(attemptId: number, item: ReviewItemPayload): Promise<AttemptResult> {
    const payload: ReviewItemPayload & { items: ReviewItemPayload[] } = {
      answer_record_id: item.answer_record_id,
      new_score: item.new_score,
      comment: item.comment,
      items: [item],
    }
    return api.post<AttemptResult>(`/attempts/${attemptId}/reviews`, payload, {
      skipGlobalError: true,
    })
  },

  mine(query: { page?: number; page_size?: number } = {}): Promise<Paged<MyAttemptItem>> {
    return api.get<Paged<MyAttemptItem>>('/attempts/mine', {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 20 },
    })
  },
}
