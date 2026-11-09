// 登录态 store：token 与用户信息的唯一读写入口，持久化到 localStorage。
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import type { AuthResult, AuthUser, TeacherRegisterPayload } from '@/api/types'
import { ROLE } from '@/utils/constants'
import { STORAGE_KEYS } from '@/utils/constants'

function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEYS.user)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    localStorage.removeItem(STORAGE_KEYS.user)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(STORAGE_KEYS.token))
  const user = ref<AuthUser | null>(readStoredUser())

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const role = computed(() => user.value?.role ?? null)
  const isTeacher = computed(() => role.value === ROLE.TEACHER)
  const isStudent = computed(() => role.value === ROLE.STUDENT)
  const displayName = computed(() => user.value?.name ?? '')
  const account = computed(() => {
    if (!user.value) return ''
    return user.value.role === 'teacher' ? user.value.account : user.value.student_no
  })
  const classCode = computed(() => (user.value?.role === 'student' ? user.value.class_code : ''))
  const qqBound = computed(() => (user.value?.role === 'student' ? user.value.qq_bound === true : false))

  function persist(): void {
    if (token.value) {
      localStorage.setItem(STORAGE_KEYS.token, token.value)
    } else {
      localStorage.removeItem(STORAGE_KEYS.token)
    }
    if (user.value) {
      localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user.value))
    } else {
      localStorage.removeItem(STORAGE_KEYS.user)
    }
  }

  function setSession(result: AuthResult): void {
    token.value = result.token
    user.value = result.user
    persist()
  }

  function setUser(next: AuthUser): void {
    user.value = next
    persist()
  }

  function setToken(next: string | null): void {
    token.value = next
    if (!next) {
      localStorage.removeItem(STORAGE_KEYS.token)
    } else {
      localStorage.setItem(STORAGE_KEYS.token, next)
    }
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    localStorage.removeItem(STORAGE_KEYS.token)
    localStorage.removeItem(STORAGE_KEYS.user)
  }

  async function loginTeacher(accountValue: string, password: string): Promise<AuthUser> {
    const result = await authApi.login({ role: 'teacher', account: accountValue, password })
    setSession(result)
    return result.user
  }

  async function loginStudent(
    classCodeValue: string,
    studentNo: string,
    password: string,
  ): Promise<AuthUser> {
    const result = await authApi.login({
      role: 'student',
      class_code: classCodeValue,
      student_no: studentNo,
      password,
    })
    setSession(result)
    return result.user
  }

  async function registerTeacher(payload: TeacherRegisterPayload): Promise<AuthUser> {
    const result = await authApi.registerTeacher(payload)
    setSession(result)
    return result.user
  }

  async function fetchMe(): Promise<AuthUser> {
    const result = await authApi.me()
    setUser(result)
    return result
  }

  async function logout(): Promise<void> {
    try {
      if (token.value) await authApi.logout()
    } catch {
      // 登出是幂等操作：网络失败也要清本地会话。
    } finally {
      clearSession()
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    role,
    isTeacher,
    isStudent,
    displayName,
    account,
    classCode,
    qqBound,
    setSession,
    setUser,
    setToken,
    clearSession,
    loginTeacher,
    loginStudent,
    registerTeacher,
    fetchMe,
    logout,
  }
})
