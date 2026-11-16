// 鉴权接口（契约 §2.1）。
import { api } from './client'
import type {
  AuthResult,
  AuthUser,
  LoginPayload,
  TeacherRegisterPayload,
} from './contract'

const formConfig = { skipGlobalError: true, skipAuthRedirect: true as const }

export const authApi = {
  registerTeacher(payload: TeacherRegisterPayload): Promise<AuthResult> {
    return api.post<AuthResult>('/auth/teacher/register', payload, formConfig)
  },

  login(payload: LoginPayload): Promise<AuthResult> {
    return api.post<AuthResult>('/auth/login', payload, formConfig)
  },

  logout(): Promise<null> {
    // 登出失败不再触发全局 401 跳转，本地会话由 store 统一清理。
    return api.post<null>('/auth/logout', undefined, {
      skipGlobalError: true,
      skipAuthRedirect: true,
    })
  },

  me(): Promise<AuthUser> {
    return api.get<AuthUser>('/auth/me')
  },
}
