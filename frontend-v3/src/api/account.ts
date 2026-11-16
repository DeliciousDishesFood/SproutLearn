// 账号安全接口（契约 §9.1）：自助改密、教师重置学生密码、学生停用/恢复。
import { api } from './client'
import type {
  PasswordChangePayload,
  PasswordResetResult,
  StudentStatusResult,
} from './contract'

export const accountApi = {
  changePassword(payload: PasswordChangePayload): Promise<null> {
    return api.post<null>('/auth/password/change', payload, { skipGlobalError: true })
  },

  /** 一次性临时密码只从本响应返回，前端不得缓存或再次查询。 */
  resetStudentPassword(classId: number, studentId: number): Promise<PasswordResetResult> {
    return api.post<PasswordResetResult>(
      `/classes/${classId}/students/${studentId}/password-reset`,
      undefined,
      { skipGlobalError: true },
    )
  },

  setStudentStatus(
    classId: number,
    studentId: number,
    status: 0 | 1,
  ): Promise<StudentStatusResult> {
    return api.put<StudentStatusResult>(
      `/classes/${classId}/students/${studentId}/status`,
      { status },
      { skipGlobalError: true },
    )
  },
}
