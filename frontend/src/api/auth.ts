// 鉴权接口（API-01 ~ API-04）。
import { api } from '@/api/client'
import type {
  AuthResult,
  AuthUser,
  LoginPayload,
  TeacherRegisterPayload,
} from '@/api/types'

const formConfig = { skipGlobalError: true, skipSessionRedirect: true as const }

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
