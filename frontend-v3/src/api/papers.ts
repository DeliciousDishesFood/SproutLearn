// 试卷接口（契约 §2.6）。
import { api } from './client'
import type {
  AttemptDetail,
  Paged,
  PaperAttemptItem,
  PaperCreatePayload,
  PaperDetail,
  PaperItem,
  PaperPublishResult,
  PaperUpdatePayload,
} from './contract'

export const papersApi = {
  create(classId: number, payload: PaperCreatePayload): Promise<PaperDetail> {
    return api.post<PaperDetail>(`/classes/${classId}/papers`, payload, { skipGlobalError: true })
  },

  list(classId: number, query: { page?: number; page_size?: number } = {}): Promise<Paged<PaperItem>> {
    return api.get<Paged<PaperItem>>(`/classes/${classId}/papers`, {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 20 },
    })
  },

  detail(paperId: number): Promise<PaperDetail> {
    return api.get<PaperDetail>(`/papers/${paperId}`)
  },

  update(paperId: number, payload: PaperUpdatePayload): Promise<PaperDetail> {
    return api.patch<PaperDetail>(`/papers/${paperId}`, payload, { skipGlobalError: true })
  },

  publish(paperId: number): Promise<PaperPublishResult> {
    return api.post<PaperPublishResult>(`/papers/${paperId}/publish`, undefined, {
      skipGlobalError: true,
    })
  },

  withdraw(paperId: number): Promise<PaperDetail> {
    return api.patch<PaperDetail>(`/papers/${paperId}/withdraw`, undefined, {
      skipGlobalError: true,
    })
  },

  attempts(
    paperId: number,
    query: { page?: number; page_size?: number } = {},
  ): Promise<Paged<PaperAttemptItem>> {
    return api.get<Paged<PaperAttemptItem>>(`/papers/${paperId}/attempts`, {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 20 },
    })
  },

  startAttempt(paperId: number): Promise<AttemptDetail> {
    return api.post<AttemptDetail>(`/papers/${paperId}/attempts`, undefined, {
      skipGlobalError: true,
    })
  },
}
