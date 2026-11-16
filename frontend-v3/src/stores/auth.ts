// 会话状态：token + 当前用户，登录后必须再拉 /auth/me 补全字段。
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import { STORAGE_KEYS } from '@/utils/constants'
import type {
  AuthResult,
  AuthUser,
  LoginPayload,
  StudentJoinPayload,
  StudentUser,
  TeacherRegisterPayload,
  TeacherUser,
} from '@/api/contract'
import { classesApi } from '@/api/classes'

function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEYS.user)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as AuthUser
    if (parsed && typeof parsed === 'object' && (parsed.role === 'teacher' || parsed.role === 'student')) {
      return parsed
    }
  } catch {
    // 损坏的本地缓存直接丢弃
  }
  return null
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(STORAGE_KEYS.token) ?? '')
  const user = ref<AuthUser | null>(readStoredUser())
  /** 本次页面生命周期内是否已用当前后端校验过 /auth/me（不持久化）。 */
  const sessionVerified = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed<'teacher' | 'student' | null>(() => user.value?.role ?? null)
  const isTeacher = computed(() => role.value === 'teacher')
  const isStudent = computed(() => role.value === 'student')
  const teacher = computed<TeacherUser | null>(() =>
    user.value?.role === 'teacher' ? user.value : null,
  )
  const student = computed<StudentUser | null>(() =>
    user.value?.role === 'student' ? user.value : null,
  )
  const displayName = computed(() => user.value?.name ?? '青芽用户')

  function persist(): void {
    if (token.value) localStorage.setItem(STORAGE_KEYS.token, token.value)
    else localStorage.removeItem(STORAGE_KEYS.token)
    if (user.value) localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user.value))
    else localStorage.removeItem(STORAGE_KEYS.user)
  }

  function setSession(result: AuthResult): void {
    token.value = result.token
    user.value = result.user
    sessionVerified.value = false
    persist()
  }

  async function fetchMe(): Promise<AuthUser> {
    const me = await authApi.me()
    user.value = me
    sessionVerified.value = true
    persist()
    return me
  }

  async function login(payload: LoginPayload): Promise<AuthUser> {
    const result = await authApi.login(payload)
    setSession(result)
    return fetchMe()
  }

  async function registerTeacher(payload: TeacherRegisterPayload): Promise<AuthUser> {
    const result = await authApi.registerTeacher(payload)
    setSession(result)
    return fetchMe()
  }

  async function joinClass(payload: StudentJoinPayload): Promise<AuthUser> {
    const result = await classesApi.join(payload)
    token.value = result.token
    user.value = result.user
    sessionVerified.value = false
    persist()
    return fetchMe()
  }

  function clear(): void {
    token.value = ''
    user.value = null
    sessionVerified.value = false
    persist()
  }

  async function logout(): Promise<void> {
    if (token.value) {
      try {
        await authApi.logout()
      } catch {
        // 登出失败也要清本地会话
      }
    }
    clear()
  }

  return {
    token,
    user,
    sessionVerified,
    isLoggedIn,
    role,
    isTeacher,
    isStudent,
    teacher,
    student,
    displayName,
    setSession,
    fetchMe,
    login,
    registerTeacher,
    joinClass,
    clear,
    logout,
  }
})
