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
    return api.post<null>('/auth/logout', undefined, { skipGlobalError: true })
  },

  me(): Promise<AuthUser> {
    return api.get<AuthUser>('/auth/me')
  },
}
