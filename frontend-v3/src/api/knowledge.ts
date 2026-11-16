// 知识库接口（契约 §2.3）：上传 multipart，部分失败仍 code=0。
import { api } from './client'
import type {
  DocumentListQuery,
  KnowledgeChunk,
  KnowledgeDocDetail,
  KnowledgeDocListItem,
  Paged,
  UploadResult,
} from './contract'

interface UploadDocumentsParams {
  class_id: number
  course_name?: string
  files: File[]
}

export const knowledgeApi = {
  upload(
    params: UploadDocumentsParams,
    onUploadProgress?: (percent: number) => void,
  ): Promise<UploadResult> {
    const formData = new FormData()
    formData.append('class_id', String(params.class_id))
    if (params.course_name) formData.append('course_name', params.course_name)
    params.files.forEach((file) => formData.append('files', file, file.name))

    return api.post<UploadResult>('/knowledge/documents', formData, {
      timeout: 0,
      skipGlobalError: true,
      onUploadProgress: (event) => {
        if (!onUploadProgress || !event.total) return
        onUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
      },
    })
  },

  listDocuments(query: DocumentListQuery): Promise<Paged<KnowledgeDocListItem>> {
    return api.get<Paged<KnowledgeDocListItem>>('/knowledge/documents', {
      params: {
        class_id: query.class_id,
        status: query.status,
        page: query.page ?? 1,
        page_size: query.page_size ?? 10,
      },
    })
  },

  detail(docId: number): Promise<KnowledgeDocDetail> {
    return api.get<KnowledgeDocDetail>(`/knowledge/documents/${docId}`)
  },

  chunks(
    docId: number,
    query: { page?: number; page_size?: number } = {},
  ): Promise<Paged<KnowledgeChunk>> {
    return api.get<Paged<KnowledgeChunk>>(`/knowledge/documents/${docId}/chunks`, {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 10 },
    })
  },

  remove(docId: number): Promise<null> {
    return api.delete<null>(`/knowledge/documents/${docId}`, { skipGlobalError: true })
  },
}
