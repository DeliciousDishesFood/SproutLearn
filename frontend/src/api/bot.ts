// M3.3 班级 QQ 机器人配置：读取/保存/凭证连通性测试。
import { api } from '@/api/client'
import type { BotConfig, BotConfigPayload, BotTestResult } from '@/api/types'

export const botApi = {
  get(classId: number): Promise<BotConfig> {
    return api.get<BotConfig>(`/classes/${classId}/bot-config`)
  },

  save(classId: number, payload: BotConfigPayload): Promise<BotConfig> {
    return api.put<BotConfig>(`/classes/${classId}/bot-config`, payload)
  },

  /** 后端最坏等 QQ 8 秒，前端多留 4 秒余量。 */
  test(classId: number): Promise<BotTestResult> {
    return api.post<BotTestResult>(`/classes/${classId}/bot-config/test`, undefined, {
      timeout: 12000,
    })
  },
}
