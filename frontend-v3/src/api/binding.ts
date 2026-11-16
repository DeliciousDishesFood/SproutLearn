// QQ 绑定接口（契约 §2.11）：Web 前端只生成绑定码与解绑，回调由机器人服务端调用。
import { api } from './client'
import type { QqBindCode } from './contract'

export const bindingApi = {
  createCode(): Promise<QqBindCode> {
    return api.post<QqBindCode>('/binding/qq-code', undefined, { skipGlobalError: true })
  },

  unbind(): Promise<null> {
    return api.delete<null>('/binding/qq', { skipGlobalError: true })
  },
}
