<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  BookOpen,
  ClipboardList,
  FileText,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Moon,
  Settings,
  ShieldCheck,
  Sprout,
  Sun,
  Users,
  X,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { notificationsApi } from '@/api/notifications'
import { classesApi } from '@/api/classes'
import { useToast } from '@/composables/useToast'
import { useTheme } from '@/composables/useTheme'
import { useFocusTrap } from '@/composables/useFocusTrap'

interface NavItem {
  label: string
  to: string
  icon: unknown
  requiresClass?: boolean
  unread?: boolean
}

const auth = useAuthStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { theme, toggle: toggleTheme } = useTheme()
const menuOpen = ref(false)
const drawerPanel = ref<HTMLElement | null>(null)
const themeLabel = computed(() => (theme.value === 'dark' ? '切换到浅色主题' : '切换到深色主题'))

// 移动抽屉：与弹窗共用焦点陷阱（Escape、焦点圈定、关闭恢复、锁定滚动）。
useFocusTrap({
  active: () => menuOpen.value,
  container: drawerPanel,
  onEscape: () => {
    menuOpen.value = false
  },
})

const classId = computed(() => {
  const param = Number(route.params.classId)
  if (Number.isFinite(param) && param > 0) return param
  return ui.currentClassId
})

const teacherTeaching = computed<NavItem[]>(() => [
  { label: '工作台', to: '/teacher', icon: LayoutDashboard },
  { label: '班级', to: '/teacher/classes', icon: Users },
  {
    label: '知识库',
    to: classId.value ? `/teacher/classes/${classId.value}/knowledge` : '/teacher/classes',
    icon: BookOpen,
    requiresClass: true,
  },
  {
    label: '题库',
    to: classId.value ? `/teacher/classes/${classId.value}/banks` : '/teacher/classes',
    icon: ClipboardList,
    requiresClass: true,
  },
  {
    label: '试卷',
    to: classId.value ? `/teacher/classes/${classId.value}/papers` : '/teacher/classes',
    icon: FileText,
    requiresClass: true,
  },
])

const teacherManage = computed<NavItem[]>(() => [
  {
    label: '批改',
    to: classId.value ? `/teacher/classes/${classId.value}/review` : '/teacher/classes',
    icon: ListChecks,
    requiresClass: true,
  },
  { label: '消息', to: '/teacher/notifications', icon: Bell, unread: true },
  {
    label: '设置',
    to: classId.value ? `/teacher/classes/${classId.value}/settings` : '/teacher/classes',
    icon: Settings,
    requiresClass: true,
  },
  { label: '账号', to: '/teacher/settings', icon: ShieldCheck },
  { label: '文档', to: '/teacher/docs', icon: BookOpen },
])

const studentNav = computed<NavItem[]>(() => [
  { label: '学习台', to: '/student', icon: LayoutDashboard },
  { label: '试卷', to: '/student/papers', icon: FileText },
  { label: '成长', to: '/student/growth', icon: Sprout },
  { label: '我的', to: '/student/profile', icon: Users },
  { label: '消息', to: '/student/notifications', icon: Bell, unread: true },
  { label: '文档', to: '/student/docs', icon: BookOpen },
])

const mobileNav = computed<NavItem[]>(() =>
  auth.isTeacher ? [...teacherTeaching.value, ...teacherManage.value] : studentNav.value,
)

const roleLabel = computed(() => (auth.isTeacher ? '教师' : '学生'))
const initial = computed(() => auth.displayName.slice(0, 1).toUpperCase())

function isActive(item: NavItem): boolean {
  const path = route.path
  const name = String(route.name ?? '')
  if (item.label === '工作台' || item.label === '学习台') return name === 'teacher-dashboard' || path === '/student'
  if (item.label === '班级') return name === 'teacher-classes' || name === 'teacher-class-detail'
  if (item.label === '知识库') return path.includes('/knowledge')
  if (item.label === '题库') return path.includes('/banks') || path.includes('/questions')
  if (item.label === '试卷') return (path.includes('/papers') || name === 'student-papers') && !path.includes('/attempts')
  if (item.label === '批改') return path.includes('/review') || path.includes('/attempts') || name === 'teacher-review'
  if (item.label === '消息') return path.includes('/notifications')
  if (item.label === '设置') return /\/teacher\/classes\/\d+\/settings/.test(path)
  if (item.label === '账号') return path === '/teacher/settings'
  if (item.label === '文档') return path.includes('/docs')
  if (item.label === '成长') return path === '/student/growth'
  if (item.label === '我的') return path === '/student/profile'
  return route.path === item.to
}

function navigate(item: NavItem): void {
  menuOpen.value = false
  if (item.requiresClass && !classId.value) {
    toast.info('请先创建或选择班级')
    void router.push('/teacher/classes')
    return
  }
  void router.push(item.to)
}

async function logout(): Promise<void> {
  await auth.logout()
  ui.setCurrentClassId(null)
  void router.push('/login')
}

async function loadUnread(): Promise<void> {
  if (!auth.isLoggedIn) return
  try {
    const result = await notificationsApi.unreadCount()
    ui.setUnreadCount(result.count)
  } catch {
    // 未读数失败不影响导航
  }
}

// 旧班级 ID 可能来自上一套后端：按当前 /classes 列表回落，避免后续请求 404。
async function syncCurrentClass(): Promise<void> {
  if (!auth.isTeacher || !ui.currentClassId) return
  try {
    const result = await classesApi.list({ page: 1, page_size: 50 })
    if (!result.list.some((item) => item.id === ui.currentClassId)) {
      ui.setCurrentClassId(result.list[0]?.id ?? null)
    }
  } catch {
    // 列表失败不阻断导航，页面自身会展示错误
  }
}

watch(() => route.fullPath, () => {
  menuOpen.value = false
  void loadUnread()
})

onMounted(() => {
  void loadUnread()
  void syncCurrentClass()
})
</script>

<template>
  <div class="app">
    <aside class="sidebar">
      <RouterLink class="side-brand" to="/">
        <span class="side-brand__mark" aria-hidden="true"><Sprout :size="16" /></span>
        <span class="side-brand__name">青芽<em>SproutLearn</em></span>
      </RouterLink>

      <nav class="side-nav" aria-label="主导航">
        <template v-if="auth.isTeacher">
          <p class="side-nav__label">教学</p>
          <button
            v-for="item in teacherTeaching"
            :key="item.to + item.label"
            type="button"
            class="side-nav__item"
            :class="{ 'is-active': isActive(item) }"
            @click="navigate(item)"
          >
            <component :is="item.icon" :size="16" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
          <p class="side-nav__label">管理</p>
          <button
            v-for="item in teacherManage"
            :key="item.to + item.label"
            type="button"
            class="side-nav__item"
            :class="{ 'is-active': isActive(item) }"
            @click="navigate(item)"
          >
            <component :is="item.icon" :size="16" aria-hidden="true" />
            <span>{{ item.label }}</span>
            <span v-if="item.unread && ui.unreadCount > 0" class="side-nav__count">
              {{ ui.unreadCount > 99 ? '99+' : ui.unreadCount }}
            </span>
          </button>
        </template>
        <template v-else>
          <button
            v-for="item in studentNav"
            :key="item.to + item.label"
            type="button"
            class="side-nav__item"
            :class="{ 'is-active': isActive(item) }"
            @click="navigate(item)"
          >
            <component :is="item.icon" :size="16" aria-hidden="true" />
            <span>{{ item.label }}</span>
            <span v-if="item.unread && ui.unreadCount > 0" class="side-nav__count">
              {{ ui.unreadCount > 99 ? '99+' : ui.unreadCount }}
            </span>
          </button>
        </template>
      </nav>

      <div class="side-user">
        <span class="avatar" :title="auth.displayName">{{ initial }}</span>
        <span class="side-user__meta">
          <strong>{{ auth.displayName }}</strong>
          <em>{{ roleLabel }}</em>
        </span>
        <button class="side-user__out" type="button" :aria-label="themeLabel" :title="themeLabel" @click="toggleTheme">
          <Sun v-if="theme === 'dark'" :size="15" />
          <Moon v-else :size="15" />
        </button>
        <button class="side-user__out" type="button" aria-label="退出登录" @click="logout">
          <LogOut :size="15" />
        </button>
      </div>
    </aside>

    <div class="mobile-bar">
      <RouterLink class="side-brand" to="/">
        <span class="side-brand__mark" aria-hidden="true"><Sprout :size="16" /></span>
        <span class="side-brand__name">青芽<em>SproutLearn</em></span>
      </RouterLink>
      <div class="row">
        <button class="icon-btn" type="button" :aria-label="themeLabel" @click="toggleTheme">
          <Sun v-if="theme === 'dark'" :size="16" />
          <Moon v-else :size="16" />
        </button>
        <span class="avatar">{{ initial }}</span>
        <button
          class="icon-btn"
          type="button"
          :aria-label="menuOpen ? '关闭导航' : '打开导航'"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <X v-if="menuOpen" :size="16" />
          <Menu v-else :size="16" />
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="menuOpen" class="mobile-drawer">
        <div class="mobile-drawer__backdrop" @click="menuOpen = false" />
        <div ref="drawerPanel" class="mobile-drawer__panel" role="dialog" aria-modal="true" aria-label="主导航">
          <header class="mobile-drawer__head">
            <RouterLink class="side-brand" to="/" @click="menuOpen = false">
              <span class="side-brand__mark" aria-hidden="true"><Sprout :size="16" /></span>
              <span class="side-brand__name">青芽<em>SproutLearn</em></span>
            </RouterLink>
            <button class="icon-btn" type="button" aria-label="关闭导航" @click="menuOpen = false">
              <X :size="16" />
            </button>
          </header>

          <nav class="mobile-drawer__nav">
            <button
              v-for="item in mobileNav"
              :key="`m-${item.to}-${item.label}`"
              type="button"
              class="side-nav__item"
              :class="{ 'is-active': isActive(item) }"
              @click="navigate(item)"
            >
              <component :is="item.icon" :size="16" aria-hidden="true" />
              <span>{{ item.label }}</span>
              <span v-if="item.unread && ui.unreadCount > 0" class="side-nav__count">
                {{ ui.unreadCount > 99 ? '99+' : ui.unreadCount }}
              </span>
            </button>
          </nav>

          <footer class="mobile-drawer__foot">
            <button class="btn" type="button" @click="toggleTheme">
              <Sun v-if="theme === 'dark'" :size="15" />
              <Moon v-else :size="15" />
              {{ theme === 'dark' ? '浅色主题' : '深色主题' }}
            </button>
            <button class="btn" type="button" @click="logout">
              <LogOut :size="15" />
              退出登录
            </button>
          </footer>
        </div>
      </div>
    </Teleport>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/* 移动端导航：浮层抽屉（不插入文档流，不挤压页面内容）。 */
.mobile-drawer {
  position: fixed;
  inset: 0;
  z-index: var(--z-drawer);
}

.mobile-drawer__backdrop {
  position: absolute;
  inset: 0;
  background: var(--overlay);
  animation: drawer-fade 160ms ease-out;
}

.mobile-drawer__panel {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: min(78dvh, 560px);
  padding: 12px;
  padding-bottom: max(12px, env(safe-area-inset-bottom));
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--sheet-shadow);
  animation: drawer-up 200ms cubic-bezier(0.22, 1, 0.36, 1);
}

.mobile-drawer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mobile-drawer__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  min-height: 0;
  padding: 2px 0;
}

.mobile-drawer__nav .side-nav__item {
  min-height: 42px;
}

.mobile-drawer__foot {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--line-soft);
}

@keyframes drawer-up {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes drawer-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
