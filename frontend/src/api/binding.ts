// QQ 绑定接口（API-17 / API-19；API-18 仅供机器人服务端调用，前端不封装）。
import { api } from '@/api/client'
import type { QqBindCode } from '@/api/types'

export const bindingApi = {
  generateCode(): Promise<QqBindCode> {
    return api.post<QqBindCode>('/binding/qq-code', undefined, { skipGlobalError: true })
  },

  unbind(): Promise<null> {
    return api.delete<null>('/binding/qq', { skipGlobalError: true })
  },
}
