// 题库接口（M2-C）：导入预览/提交、筛选列表、编辑、软删除、讲评。
import { api } from '@/api/client'
import type {
  Paged,
  QuestionExplainResult,
  QuestionImportCommit,
  QuestionImportPreview,
  QuestionItem,
  QuestionListQuery,
  QuestionUpdatePayload,
} from '@/api/types'

export const questionsApi = {
  previewImport(classId: number, file: File): Promise<QuestionImportPreview> {
    const formData = new FormData()
    formData.append('file', file, file.name)
    return api.post<QuestionImportPreview>(
      `/classes/${classId}/questions/import/preview`,
      formData,
      { timeout: 0, skipGlobalError: true },
    )
  },

  commitImport(classId: number, token: string): Promise<QuestionImportCommit> {
    return api.post<QuestionImportCommit>(
      `/classes/${classId}/questions/import/commit`,
      { token },
      { timeout: 0, skipGlobalError: true },
    )
  },

  list(classId: number, query: QuestionListQuery = {}): Promise<Paged<QuestionItem>> {
    const tag = query.knowledge_tag?.trim() || undefined
    return api.get<Paged<QuestionItem>>(`/classes/${classId}/questions`, {
      params: {
        type: query.type,
        // 后端实际读取 tag；同时带 knowledge_tag，保持与派工包参数名一致。
        tag,
        knowledge_tag: tag,
        difficulty: query.difficulty,
        status: query.status,
        keyword: query.keyword?.trim() || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 10,
      },
    })
  },

  update(questionId: number, payload: QuestionUpdatePayload): Promise<QuestionItem> {
    return api.patch<QuestionItem>(`/questions/${questionId}`, payload, { skipGlobalError: true })
  },

  remove(questionId: number): Promise<null> {
    return api.delete<null>(`/questions/${questionId}`, { skipGlobalError: true })
  },

  explain(questionId: number, studentAnswer?: unknown): Promise<QuestionExplainResult> {
    return api.post<QuestionExplainResult>(
      `/questions/${questionId}/explain`,
      studentAnswer === undefined ? {} : { student_answer: studentAnswer },
      { timeout: 60000, skipGlobalError: true },
    )
  },
}
