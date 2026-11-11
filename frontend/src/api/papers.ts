// 试卷接口（M2-C）：组卷、列表、详情、编辑、发布/撤回、开卷、某卷成绩。
import { api } from '@/api/client'
import type {
  AttemptDetail,
  Paged,
  PaperAttemptItem,
  PaperCreatePayload,
  PaperDetail,
  PaperItem,
  PaperUpdatePayload,
} from '@/api/types'

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

  publish(paperId: number): Promise<PaperDetail> {
    return api.post<PaperDetail>(`/papers/${paperId}/publish`, undefined, { skipGlobalError: true })
  },

  withdraw(paperId: number): Promise<PaperDetail> {
    return api.patch<PaperDetail>(`/papers/${paperId}/withdraw`, undefined, { skipGlobalError: true })
  },

  startAttempt(paperId: number): Promise<AttemptDetail> {
    return api.post<AttemptDetail>(`/papers/${paperId}/attempts`, undefined, {
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
}
