// M3.3 文档中心：清单与 Markdown 原文，正文由后端 content/docs 维护。
import { api } from '@/api/client'
import type { DocDetail, DocListItem } from '@/api/types'

export const docsApi = {
  list(): Promise<DocListItem[]> {
    return api.get<DocListItem[]>('/docs', { skipGlobalError: true })
  },

  detail(slug: string): Promise<DocDetail> {
    return api.get<DocDetail>(`/docs/${encodeURIComponent(slug)}`, { skipGlobalError: true })
  },
}
