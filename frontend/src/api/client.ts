// Axios 客户端：注入 token、拆统一响应体、按错误码映射文案并处理会话失效。
import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { useUiStore } from '@/stores/ui'
import {
  API_BASE_URL,
  ERROR_CODE,
  ERROR_MESSAGES,
  SESSION_EXPIRED_EVENT,
  STORAGE_KEYS,
} from '@/utils/constants'
import type { ApiEnvelope } from '@/api/types'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 表单内自行展示错误时关闭全局 toast。 */
    skipGlobalError?: boolean
    /** 登录/加入页失败时保持当前页面，避免会话监听重复跳转。 */
    skipSessionRedirect?: boolean
  }
}

export class ApiError extends Error {
  readonly code: number
  readonly data: unknown
  readonly requestId: string
  readonly httpStatus: number

  constructor(options: {
    code: number
    message: string
    data?: unknown
    requestId?: string
    httpStatus?: number
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.code = options.code
    this.data = options.data ?? null
    this.requestId = options.requestId ?? ''
    this.httpStatus = options.httpStatus ?? 0
  }

  get friendlyMessage(): string {
    return ERROR_MESSAGES[this.code] || this.message || '请求未能完成，请重试'
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function toUserMessage(error: unknown): string {
  if (isApiError(error)) return error.friendlyMessage
  if (error instanceof Error && error.message) return error.message
  return '请求未能完成，请重试'
}

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: { Accept: 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEYS.token)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function isSessionCode(code: number): boolean {
  return code === ERROR_CODE.UNAUTHORIZED || code === ERROR_CODE.SESSION_EXPIRED
}

function clearSession(): void {
  localStorage.removeItem(STORAGE_KEYS.token)
  localStorage.removeItem(STORAGE_KEYS.user)
}

function notifySessionExpired(message: string): void {
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT, { detail: { message } }))
}

function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiEnvelope<unknown>>
    const body = axiosError.response?.data
    const status = axiosError.response?.status ?? 0
    if (body && typeof body === 'object' && typeof body.code === 'number') {
      return new ApiError({
        code: body.code,
        message: body.message,
        data: body.data,
        requestId: body.request_id,
        httpStatus: status,
      })
    }
    if (status > 0) {
      return new ApiError({ code: -1, message: `请求失败（${status}）`, httpStatus: status })
    }
    return new ApiError({ code: -1, message: '网络连接失败，请检查网络后重试' })
  }
  if (error instanceof Error) {
    return new ApiError({ code: -1, message: error.message })
  }
  return new ApiError({ code: -1, message: '请求未能完成，请重试' })
}

http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiEnvelope<unknown>
    if (body && typeof body === 'object' && typeof body.code === 'number') {
      if (body.code === 0) return body.data
      throw new ApiError({
        code: body.code,
        message: body.message,
        data: body.data,
        requestId: body.request_id,
        httpStatus: response.status,
      })
    }
    return response.data
  },
  (error: unknown) => {
    const apiError = normalizeError(error)
    const config = axios.isAxiosError(error) ? error.config : undefined
    const skipGlobalError = config?.skipGlobalError === true
    const skipSessionRedirect = config?.skipSessionRedirect === true

    if (isSessionCode(apiError.code) && !skipSessionRedirect) {
      clearSession()
      notifySessionExpired(apiError.friendlyMessage)
    } else if (!skipGlobalError) {
      useUiStore().toast(apiError.friendlyMessage, 'error')
    }
    return Promise.reject(apiError)
  },
)

export const api = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return http.get(url, config) as unknown as Promise<T>
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return http.post(url, data, config) as unknown as Promise<T>
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return http.put(url, data, config) as unknown as Promise<T>
  },
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return http.delete(url, config) as unknown as Promise<T>
  },
}

export { http }
