// 路由守卫：登录态、角色、访客页反跳与页面标题统一在此处理。
import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { Role } from '@/types'

function homePathFor(role: Role | null): string {
  if (role === 'teacher') return '/teacher/dashboard'
  if (role === 'student') return '/student/home'
  return '/login'
}

function homeForRole(role: Role | null): string {
  return homePathFor(role)
}

export function setupGuards(router: Router): void {
  router.beforeEach((toLocale) => {
    const auth = useAuthStore()
    const role = auth.role
    const roles = toLocale.meta.roles as Role[] | undefined

    if (toLocale.meta.title) {
      document.title = `${toLocale.meta.title} · 青芽 SproutLearn`
    } else {
      document.title = '青芽 SproutLearn'
    }

    if (toLocale.meta.guestOnly && auth.isAuthenticated) {
      return homeForRole(role)
    }

    // 父级 meta 也参与判断，避免子路由漏写导致越权。
    const needsAuth = toLocale.matched.some((record) => record.meta.requiresAuth === true)
    if (needsAuth && !auth.isAuthenticated) {
      return { path: '/login', query: { redirect: toLocale.fullPath } }
    }

    if (roles && roles.length > 0 && (!role || !roles.includes(role))) {
      useUiStore().toast('当前账号无权访问该页面', 'warning')
      return homeForRole(role)
    }

    return true
  })

  router.afterEach((toLocale, from, failure) => {
    if (!failure && (toLocale.path !== from.path || toLocale.query !== from.query)) {
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
  })
}
