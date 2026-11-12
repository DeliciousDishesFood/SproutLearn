<!-- 空白布局：登录/注册/加入全屏；学生页附轻量顶栏。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const showStudentShell = computed(() => route.meta.studentShell === true)
const initial = computed(() => auth.displayName.trim().slice(0, 1) || '学')

async function handleLogout(): Promise<void> {
  await auth.logout()
  ui.success('已安全退出')
  await router.replace('/login')
}
</script>

<template>
  <div class="blank-layout" :class="{ 'blank-layout--student': showStudentShell }">
    <header v-if="showStudentShell" class="student-topbar">
      <router-link to="/student/home" class="student-brand" aria-label="青芽 SproutLearn 学生首页">
        <span class="student-brand__mark">
          <Sprout :size="18" :stroke-width="2" />
        </span>
        <span class="student-brand__text">青芽 <em>SproutLearn</em></span>
      </router-link>

      <div class="student-topbar__right">
        <nav class="student-nav" aria-label="学生导航">
          <router-link to="/student/home" class="student-nav__link" active-class="student-nav__link--active">
            学习台
          </router-link>
          <router-link to="/student/papers" class="student-nav__link" active-class="student-nav__link--active">
            练习
          </router-link>
          <router-link to="/student/profile" class="student-nav__link" active-class="student-nav__link--active">
            我的
          </router-link>
          <router-link to="/docs" class="student-nav__link" active-class="student-nav__link--active">
            文档
          </router-link>
        </nav>
        <span class="student-user">
          <span class="student-avatar">{{ initial }}</span>
          <span class="student-user__name">{{ auth.displayName }}</span>
        </span>
        <button class="logout-link" type="button" @click="handleLogout">退出</button>
      </div>
    </header>

    <main class="blank-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.blank-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.blank-main {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.student-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  height: var(--topbar-h);
  padding: 0 var(--sp-6);
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-surface) 88%, transparent);
  backdrop-filter: blur(12px);
}

.student-brand {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-text);
}

.student-brand:hover {
  color: var(--color-text);
}

.student-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  background: var(--color-primary);
}

.student-brand__text {
  font-size: var(--fs-base);
  font-weight: 600;
  letter-spacing: 0.08em;
}

.student-brand__text em {
  margin-left: 4px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-style: normal;
  font-weight: 400;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
}

.student-topbar__right {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}

.student-nav {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}

.student-nav__link {
  padding: 6px var(--sp-3);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  transition: color 160ms ease-out, background-color 160ms ease-out;
}

.student-nav__link:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.student-nav__link--active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: 600;
}

.student-user {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.student-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  color: var(--color-text-inverse);
  background: var(--color-primary);
  font-size: var(--fs-xs);
}

.logout-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.logout-link:hover {
  color: var(--color-danger);
}

@media (max-width: 720px) {
  .student-topbar {
    padding: 0 var(--sp-4);
  }

  .student-brand__text em,
  .student-user__name {
    display: none;
  }

  .student-topbar__right {
    gap: var(--sp-2);
  }
}
</style>
