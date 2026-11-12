// 金句接口（M3.2-07）：后端三级兜底并始终返回 200；前端失败时静默回落本地句池。
import { api } from '@/api/client'
import type { QuoteResult } from '@/api/types'

export const quotesApi = {
  random(type?: string): Promise<QuoteResult> {
    return api.get<QuoteResult>('/quotes/random', {
      params: type ? { type } : undefined,
      timeout: 8000,
      skipGlobalError: true,
    })
  },
}
