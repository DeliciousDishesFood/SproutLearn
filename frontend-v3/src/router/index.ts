// 路由：按 meta.role 分流，教师/学生互斥；根路径按会话重定向。
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ERROR_CODE } from '@/utils/constants'
import { isApiError } from '@/api/client'
import AppShell from '@/layouts/AppShell.vue'

declare module 'vue-router' {
  interface RouteMeta {
    role?: 'teacher' | 'student' | 'public'
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { role: 'public', title: '登录' },
    },
    {
      path: '/register/teacher',
      name: 'register-teacher',
      component: () => import('@/views/auth/RegisterTeacherView.vue'),
      meta: { role: 'public', title: '教师注册' },
    },
    {
      path: '/join',
      name: 'join',
      component: () => import('@/views/auth/JoinClassView.vue'),
      meta: { role: 'public', title: '加入班级' },
    },
    {
      path: '/',
      name: 'root',
      beforeEnter: () => {
        const auth = useAuthStore()
        if (!auth.isLoggedIn) return { path: '/login' }
        return auth.isTeacher ? { path: '/teacher' } : { path: '/student' }
      },
      component: { template: '<div />' },
      meta: { role: 'public' },
    },
    {
      path: '/teacher',
      component: AppShell,
      meta: { role: 'teacher' },
      children: [
        {
          path: '',
          name: 'teacher-dashboard',
          component: () => import('@/views/teacher/DashboardView.vue'),
          meta: { title: '教师工作台' },
        },
        {
          path: 'classes',
          name: 'teacher-classes',
          component: () => import('@/views/teacher/ClassListView.vue'),
          meta: { title: '班级' },
        },
        {
          path: 'classes/:classId',
          name: 'teacher-class-detail',
          component: () => import('@/views/teacher/ClassDetailView.vue'),
          meta: { title: '班级详情' },
        },
        {
          path: 'classes/:classId/knowledge',
          name: 'teacher-knowledge',
          component: () => import('@/views/teacher/KnowledgeView.vue'),
          meta: { title: '知识库' },
        },
        {
          path: 'classes/:classId/knowledge/:docId',
          name: 'teacher-knowledge-doc',
          component: () => import('@/views/teacher/KnowledgeDocView.vue'),
          meta: { title: '文档详情' },
        },
        {
          path: 'classes/:classId/banks',
          name: 'teacher-banks',
          component: () => import('@/views/teacher/BanksView.vue'),
          meta: { title: '题库' },
        },
        {
          path: 'classes/:classId/questions',
          name: 'teacher-questions',
          component: () => import('@/views/teacher/QuestionsView.vue'),
          meta: { title: '题目' },
        },
        {
          path: 'classes/:classId/papers',
          name: 'teacher-papers',
          component: () => import('@/views/teacher/PapersView.vue'),
          meta: { title: '试卷' },
        },
        {
          path: 'classes/:classId/papers/new',
          name: 'teacher-paper-create',
          component: () => import('@/views/teacher/PaperCreateView.vue'),
          meta: { title: '组卷' },
        },
        {
          path: 'classes/:classId/review',
          name: 'teacher-review-hub',
          component: () => import('@/views/teacher/ReviewHubView.vue'),
          meta: { title: '批改' },
        },
        {
          path: 'papers/:paperId',
          name: 'teacher-paper-detail',
          component: () => import('@/views/teacher/PaperDetailView.vue'),
          meta: { title: '试卷详情' },
        },
        {
          path: 'papers/:paperId/attempts',
          name: 'teacher-paper-attempts',
          component: () => import('@/views/teacher/PaperAttemptsView.vue'),
          meta: { title: '作答列表' },
        },
        {
          path: 'attempts/:attemptId/result',
          name: 'teacher-review',
          component: () => import('@/views/teacher/ReviewView.vue'),
          meta: { title: '批改复核' },
        },
        {
          path: 'notifications',
          name: 'teacher-notifications',
          component: () => import('@/views/teacher/NotificationsView.vue'),
          meta: { title: '通知与公告' },
        },
        {
          path: 'docs',
          name: 'teacher-docs',
          component: () => import('@/views/teacher/DocsView.vue'),
          meta: { title: '文档中心' },
        },
        {
          path: 'classes/:classId/settings',
          name: 'teacher-settings',
          component: () => import('@/views/teacher/ClassSettingsView.vue'),
          meta: { title: '班级设置' },
        },
      ],
    },
    {
      // 作答页独立于工作台外壳，进入聚焦模式（隐藏侧栏与导航）。
      path: '/student/attempts/:attemptId(\\d+)',
      name: 'student-attempt',
      component: () => import('@/views/student/AttemptView.vue'),
      meta: { role: 'student', title: '作答' },
    },
    {
      path: '/student',
      component: AppShell,
      meta: { role: 'student' },
      children: [
        {
          path: '',
          name: 'student-home',
          component: () => import('@/views/student/HomeView.vue'),
          meta: { title: '学习台' },
        },
        {
          path: 'papers',
          name: 'student-papers',
          component: () => import('@/views/student/PapersView.vue'),
          meta: { title: '试卷' },
        },
        {
          path: 'attempts/:attemptId/result',
          name: 'student-result',
          component: () => import('@/views/student/ResultView.vue'),
          meta: { title: '作答结果' },
        },
        {
          path: 'growth',
          name: 'student-growth',
          component: () => import('@/views/student/GrowthView.vue'),
          meta: { title: '成长' },
        },
        {
          path: 'profile',
          name: 'student-profile',
          component: () => import('@/views/student/ProfileView.vue'),
          meta: { title: '我的' },
        },
        {
          path: 'notifications',
          name: 'student-notifications',
          component: () => import('@/views/student/NotificationsView.vue'),
          meta: { title: '通知' },
        },
        {
          path: 'docs',
          name: 'student-docs',
          component: () => import('@/views/student/DocsView.vue'),
          meta: { title: '文档中心' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/shared/NotFoundView.vue'),
      meta: { role: 'public', title: '页面不存在' },
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.role === 'public') return true
  const auth = useAuthStore()
  if (!auth.isLoggedIn) {
    return { path: '/login', query: to.fullPath === '/' ? undefined : { redirect: to.fullPath } }
  }
  // 每次页面生命周期至少校验一次 /auth/me：换后端后不能继续演旧账号。
  if (!auth.sessionVerified) {
    try {
      await auth.fetchMe()
    } catch (error) {
      const authExpired =
        isApiError(error) &&
        (error.code === ERROR_CODE.UNAUTHORIZED || error.code === ERROR_CODE.SESSION_EXPIRED)
      if (authExpired) {
        auth.clear()
        return { path: '/login', query: { redirect: to.fullPath } }
      }
      // 网络或后端异常不清会话，交给页面展示错误与重试。
    }
  }
  if (to.meta.role === 'teacher' && !auth.isTeacher) return { path: '/student' }
  if (to.meta.role === 'student' && !auth.isStudent) return { path: '/teacher' }
  return true
})

router.afterEach((to) => {
  const title = to.meta.title
  document.title = title ? `${title} · 青芽 SproutLearn` : '青芽 SproutLearn'
})

export default router
