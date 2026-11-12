// 路由表（契约 §10.1）：显式角色约束，页面组件全部懒加载。
import type { RouteRecordRaw } from 'vue-router'
import type { Role } from '@/types'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    roles?: Role[]
    guestOnly?: boolean
    studentShell?: boolean
    description?: string
  }
}

function homeForCurrentUser(): string {
  const auth = useAuthStore()
  if (auth.isTeacher) return '/teacher/dashboard'
  if (auth.isStudent) return '/student/home'
  return '/login'
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'root',
    redirect: () => homeForCurrentUser(),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: '登录', guestOnly: true, description: '教师与学生共用入口' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/TeacherRegisterView.vue'),
    meta: { title: '教师注册', guestOnly: true, description: '创建教师账号' },
  },
  {
    path: '/join',
    name: 'join',
    component: () => import('@/views/auth/StudentJoinView.vue'),
    meta: { title: '加入班级', guestOnly: true, description: '使用邀请码加入班级' },
  },
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { requiresAuth: true, roles: ['teacher'] },
    children: [
      {
        path: '',
        redirect: '/teacher/dashboard',
      },
      {
        path: 'dashboard',
        name: 'teacher-dashboard',
        component: () => import('@/views/teacher/DashboardView.vue'),
        meta: { title: '教学总览', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'classes',
        name: 'teacher-classes',
        component: () => import('@/views/teacher/ClassListView.vue'),
        meta: { title: '我的班级', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'classes/:id',
        name: 'teacher-class-detail',
        component: () => import('@/views/teacher/ClassDetailView.vue'),
        meta: { title: '班级详情', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'knowledge',
        name: 'teacher-knowledge',
        component: () => import('@/views/teacher/KnowledgeView.vue'),
        meta: { title: '知识库', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'knowledge/:docId',
        name: 'teacher-knowledge-detail',
        component: () => import('@/views/teacher/KnowledgeDetailView.vue'),
        meta: { title: '文档详情', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'questions',
        name: 'teacher-questions',
        component: () => import('@/views/teacher/TeacherQuestionsView.vue'),
        meta: { title: '题库', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'papers',
        name: 'teacher-papers',
        component: () => import('@/views/teacher/TeacherPapersView.vue'),
        meta: { title: '试卷', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'papers/new',
        name: 'teacher-paper-create',
        component: () => import('@/views/teacher/TeacherPaperCreateView.vue'),
        meta: { title: '新建试卷', requiresAuth: true, roles: ['teacher'] },
      },
      {
        path: 'papers/:id',
        name: 'teacher-paper-detail',
        component: () => import('@/views/teacher/TeacherPaperDetailView.vue'),
        meta: { title: '试卷详情', requiresAuth: true, roles: ['teacher'] },
      },
    ],
  },
  {
    path: '/student',
    component: () => import('@/layouts/BlankLayout.vue'),
    meta: { requiresAuth: true, roles: ['student'] },
    children: [
      {
        path: '',
        redirect: '/student/home',
      },
      {
        path: 'home',
        name: 'student-home',
        component: () => import('@/views/student/StudentHomeView.vue'),
        meta: {
          title: '学生首页',
          requiresAuth: true,
          roles: ['student'],
          studentShell: true,
        },
      },
      {
        path: 'profile',
        name: 'student-profile',
        component: () => import('@/views/student/StudentProfileView.vue'),
        meta: {
          title: '个人中心',
          requiresAuth: true,
          roles: ['student'],
          studentShell: true,
        },
      },
      {
        path: 'papers',
        name: 'student-papers',
        component: () => import('@/views/student/StudentPapersView.vue'),
        meta: {
          title: '试卷',
          requiresAuth: true,
          roles: ['student'],
          studentShell: true,
        },
      },
      {
        path: 'attempts/:id',
        name: 'student-attempt',
        component: () => import('@/views/student/StudentAttemptView.vue'),
        meta: {
          title: '答题',
          requiresAuth: true,
          roles: ['student'],
          studentShell: true,
        },
      },
      {
        path: 'attempts/:id/result',
        name: 'student-attempt-result',
        component: () => import('@/views/student/StudentResultView.vue'),
        meta: {
          title: '成绩',
          requiresAuth: true,
          roles: ['student'],
          studentShell: true,
        },
      },
    ],
  },
  {
    path: '/docs',
    component: () => import('@/layouts/DocsLayout.vue'),
    meta: { requiresAuth: true, roles: ['teacher', 'student'] },
    children: [
      {
        path: '',
        name: 'docs',
        component: () => import('@/views/docs/DocsView.vue'),
        meta: { title: '文档中心', requiresAuth: true, roles: ['teacher', 'student'] },
      },
      {
        path: ':slug',
        name: 'docs-detail',
        component: () => import('@/views/docs/DocsView.vue'),
        meta: { title: '文档中心', requiresAuth: true, roles: ['teacher', 'student'] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: () => homeForCurrentUser(),
  },
]
