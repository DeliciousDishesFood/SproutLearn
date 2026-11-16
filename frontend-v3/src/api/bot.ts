// 机器人 / 文档中心接口（契约 §2.9）。
import { api } from './client'
import type {
  BotConfig,
  BotConfigPayload,
  BotTestResult,
  DocDetail,
  DocListItem,
  GroupBindCode,
} from './contract'

export const botApi = {
  get(classId: number): Promise<BotConfig> {
    return api.get<BotConfig>(`/classes/${classId}/bot-config`)
  },

  save(classId: number, payload: BotConfigPayload): Promise<BotConfig> {
    return api.put<BotConfig>(`/classes/${classId}/bot-config`, payload, {
      skipGlobalError: true,
    })
  },

  test(classId: number): Promise<BotTestResult> {
    return api.post<BotTestResult>(`/classes/${classId}/bot-config/test`, undefined, {
      timeout: 12000,
      skipGlobalError: true,
    })
  },

  generateGroupCode(classId: number): Promise<GroupBindCode> {
    return api.post<GroupBindCode>(`/classes/${classId}/bot-config/group-code`, undefined, {
      skipGlobalError: true,
    })
  },

  generateGroupBindCode(classId: number): Promise<GroupBindCode> {
    return api.post<GroupBindCode>(`/classes/${classId}/bot-config/group-bind-code`, undefined, {
      skipGlobalError: true,
    })
  },
}

export const docsApi = {
  list(): Promise<DocListItem[]> {
    return api.get<DocListItem[]>('/docs')
  },

  detail(slug: string): Promise<DocDetail> {
    return api.get<DocDetail>(`/docs/${encodeURIComponent(slug)}`)
  },
}
