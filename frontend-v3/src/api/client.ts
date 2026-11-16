// 统一 HTTP 客户端：注入 Bearer、解包 {code,message,data}、401 清会话、ApiError 保留业务码。
// 契约 §1.2：code === 0 自动解包 data；code !== 0 抛 ApiError。
import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import type { ApiEnvelope } from './contract'
import {
  API_BASE_URL,
  ERROR_CODE,
  ERROR_MESSAGES,
  SESSION_EXPIRED_EVENT,
  STORAGE_KEYS,
} from '@/utils/constants'

export { SESSION_EXPIRED_EVENT }
/** 全局 toast 事件：{ message, type: 'error' | 'success' | 'info' | 'warning' }。 */
export const TOAST_EVENT = 'sproutlearn.v3:toast'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 表单页自己接管错误提示，不弹全局 toast。 */
    skipGlobalError?: boolean
    /** 登录/注册/加入页：401 时不广播会话失效，保持当前页。 */
    skipAuthRedirect?: boolean
  }
}

export class ApiError extends Error {
  readonly code: number
  readonly data: unknown
  readonly request_id: string
  readonly http_status: number

  constructor(options: {
    code: number
    message: string
    data?: unknown
    request_id?: string
    http_status?: number
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.code = options.code
    this.data = options.data ?? null
    this.request_id = options.request_id ?? ''
    this.http_status = options.http_status ?? 0
  }

  get friendlyMessage(): string {
    return ERROR_MESSAGES[this.code] ?? this.message ?? '请求未能完成，请重试'
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

function notifyToast(message: string, type: 'error' | 'success' | 'info' | 'warning' = 'error'): void {
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: { message, type } }))
}

/** 会话失效/全局 toast 的统一出口：HTTP 错误与 200 信封错误都走这里。 */
function handleApiError(apiError: ApiError, config?: AxiosRequestConfig): void {
  const skipGlobalError = config?.skipGlobalError === true
  const skipAuthRedirect = config?.skipAuthRedirect === true
  if (isSessionCode(apiError.code) && !skipAuthRedirect) {
    clearSession()
    notifySessionExpired(apiError.friendlyMessage)
  } else if (!skipGlobalError) {
    notifyToast(apiError.friendlyMessage, 'error')
  }
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
        request_id: body.request_id,
        http_status: status,
      })
    }
    if (status > 0) {
      return new ApiError({ code: -1, message: `请求失败（HTTP ${status}）`, http_status: status })
    }
    return new ApiError({ code: -1, message: '网络异常，请检查后端是否启动' })
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
      const apiError = new ApiError({
        code: body.code,
        message: body.message,
        data: body.data,
        request_id: body.request_id,
        http_status: response.status,
      })
      handleApiError(apiError, response.config)
      return Promise.reject(apiError)
    }
    return response.data
  },
  (error: unknown) => {
    const apiError = normalizeError(error)
    const config = axios.isAxiosError(error) ? error.config : undefined
    handleApiError(apiError, config)
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
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return http.patch(url, data, config) as unknown as Promise<T>
  },
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return http.delete(url, config) as unknown as Promise<T>
  },
}

export { http }
