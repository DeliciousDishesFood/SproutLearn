<!-- 教师端布局：墨绿侧栏 + 暖白工作区 + 顶栏用户信息。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  LibraryBig,
  LogOut,
  Sprout,
  UsersRound,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const navItems = [
  { label: '教学总览', to: '/teacher/dashboard', icon: LayoutDashboard },
  { label: '我的班级', to: '/teacher/classes', icon: UsersRound },
  { label: '知识库', to: '/teacher/knowledge', icon: LibraryBig },
]

const pageTitle = computed(() => (route.meta.title as string | undefined) || '教学工作台')
const initial = computed(() => auth.displayName.trim().slice(0, 1) || '师')

let loggingOut = false
async function handleLogout(): Promise<void> {
  if (loggingOut) return
  loggingOut = true
  try {
    await auth.logout()
    ui.success('已安全退出')
    await router.replace('/login')
  } finally {
    loggingOut = false
  }
}
</script>

<template>
  <div class="teacher-layout">
    <aside class="sidebar">
      <router-link to="/teacher/dashboard" class="brand" aria-label="青芽 SproutLearn 教学总览">
        <span class="brand-mark">
          <Sprout :size="20" :stroke-width="1.9" />
        </span>
        <span class="brand-text">
          <strong>青芽</strong>
          <em>SproutLearn</em>
        </span>
      </router-link>

      <p class="nav-label">教学工作台</p>

      <nav class="nav" aria-label="教师导航">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="nav-item--active"
          :title="item.label"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <span class="sidebar-foot__line" />
        <p>把课程资料整理成<br />一片可生长的知识林。</p>
        <span class="sidebar-foot__tag">M1 · 教学知识库</span>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <span class="breadcrumb">青芽 SproutLearn · 教师端</span>
          <h1>{{ pageTitle }}</h1>
        </div>
        <div class="topbar-actions">
          <div class="user-chip">
            <span class="avatar" aria-hidden="true">{{ initial }}</span>
            <span class="user-meta">
              <strong>{{ auth.displayName || '教师' }}</strong>
              <small>{{ auth.account }}</small>
            </span>
          </div>
          <button class="icon-btn" type="button" title="退出登录" aria-label="退出登录" @click="handleLogout">
            <LogOut :size="18" :stroke-width="1.8" />
          </button>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="view" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.teacher-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-w);
  height: 100vh;
  padding: var(--sp-5) var(--sp-3);
  color: var(--color-text-inverse);
  background:
    linear-gradient(
      180deg,
      var(--color-primary) 0%,
      color-mix(in srgb, var(--color-primary-hover) 88%, var(--color-text)) 100%);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: 0 var(--sp-2) var(--sp-5);
  color: var(--color-text-inverse);
}

.brand:hover {
  color: var(--color-text-inverse);
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid color-mix(in srgb, var(--color-accent) 55%, transparent);
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  background: color-mix(in srgb, var(--color-text-inverse) 7%, transparent);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-text strong {
  font-size: var(--fs-lg);
  letter-spacing: 0.08em;
}

.brand-text em {
  margin-top: 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-style: normal;
  letter-spacing: 0.14em;
  color: color-mix(in srgb, var(--color-text-inverse) 62%, transparent);
}

.nav-label {
  padding: 0 var(--sp-3);
  margin-bottom: var(--sp-2);
  font-size: var(--fs-xs);
  letter-spacing: 0.12em;
  color: color-mix(in srgb, var(--color-text-inverse) 48%, transparent);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  height: 42px;
  padding: 0 var(--sp-3);
  border-radius: var(--radius-sm);
  color: color-mix(in srgb, var(--color-text-inverse) 74%, transparent);
  font-weight: 500;
  transition: color 160ms ease-out, background-color 160ms ease-out;
}

.nav-item:hover {
  color: var(--color-text-inverse);
  background: color-mix(in srgb, var(--color-text-inverse) 8%, transparent);
}

.nav-item--active {
  color: var(--color-text-inverse);
  background: color-mix(in srgb, var(--color-text-inverse) 13%, transparent);
}

.nav-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 11px;
  bottom: 11px;
  width: 2px;
  border-radius: 999px;
  background: var(--color-accent);
}

.sidebar-foot {
  margin-top: auto;
  padding: var(--sp-4) var(--sp-3) var(--sp-2);
  font-size: var(--fs-xs);
  line-height: 1.7;
  color: color-mix(in srgb, var(--color-text-inverse) 55%, transparent);
}

.sidebar-foot__line {
  display: block;
  width: 24px;
  height: 2px;
  margin-bottom: var(--sp-2);
  background: var(--color-accent);
}

.sidebar-foot__tag {
  display: inline-block;
  margin-top: var(--sp-3);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  color: color-mix(in srgb, var(--color-text-inverse) 42%, transparent);
}

.workspace {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  min-height: var(--topbar-h);
  padding: var(--sp-2) var(--sp-6);
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-surface) 88%, transparent);
  backdrop-filter: blur(12px);
}

.topbar-title {
  display: flex;
  flex-direction: column;
}

.breadcrumb {
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
}

.topbar-title h1 {
  font-size: var(--fs-lg);
  margin-top: 1px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-2);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  font-weight: 600;
  color: var(--color-text-inverse);
  background: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.user-meta strong {
  font-size: var(--fs-sm);
}

.user-meta small {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
}

.content {
  min-width: 0;
  flex: 1;
}

.view-enter-active,
.view-leave-active {
  transition: opacity 180ms ease-out, transform 180ms ease-out;
}

.view-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.view-leave-to {
  opacity: 0;
}

@media (max-width: 1279px) {
  .sidebar {
    width: 208px;
  }
}

@media (max-width: 1023px) {
  .sidebar {
    width: 76px;
    padding: var(--sp-5) var(--sp-2);
  }

  .brand {
    justify-content: center;
    padding: 0 0 var(--sp-5);
  }

  .brand-text,
  .nav-label,
  .nav-item span,
  .sidebar-foot {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0;
  }

  .nav-item--active::before {
    left: -1px;
  }

  .topbar {
    padding: var(--sp-2) var(--sp-5);
  }

  .topbar-title {
    display: none;
  }
}

@media (max-width: 720px) {
  .topbar {
    padding: var(--sp-2) var(--sp-4);
  }

  .user-meta {
    display: none;
  }
}
</style>
