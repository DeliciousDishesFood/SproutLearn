<!-- 文档中心布局：教师与学生共用的轻量顶栏，返回各自工作台。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft, Sprout } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const homePath = computed(() => (auth.isTeacher ? '/teacher/dashboard' : '/student/home'))
const homeLabel = computed(() => (auth.isTeacher ? '返回教学工作台' : '返回学习台'))
const initial = computed(() => auth.displayName.trim().slice(0, 1) || '青')
</script>

<template>
  <div class="docs-layout">
    <header class="docs-topbar">
      <router-link :to="homePath" class="docs-brand" aria-label="青芽 SproutLearn 文档中心">
        <span class="docs-brand__mark">
          <Sprout :size="18" :stroke-width="2" />
        </span>
        <span class="docs-brand__text">青芽 <em>Docs</em></span>
      </router-link>

      <div class="docs-topbar__right">
        <nav class="docs-nav" aria-label="文档导航">
          <router-link to="/docs" class="docs-nav__link" active-class="docs-nav__link--active">
            文档中心
          </router-link>
        </nav>
        <span class="docs-user">
          <span class="docs-avatar" aria-hidden="true">{{ initial }}</span>
          <span class="docs-user__name">{{ auth.displayName || '用户' }}</span>
        </span>
        <router-link :to="homePath" class="docs-back">
          <ArrowLeft :size="14" :stroke-width="1.8" />
          {{ homeLabel }}
        </router-link>
      </div>
    </header>

    <main class="docs-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.docs-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

.docs-topbar {
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

.docs-brand {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-text);
}

.docs-brand:hover {
  color: var(--color-text);
}

.docs-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  background: var(--color-primary);
}

.docs-brand__text {
  font-size: var(--fs-base);
  font-weight: 600;
  letter-spacing: 0.08em;
}

.docs-brand__text em {
  margin-left: 4px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-style: normal;
  font-weight: 400;
  letter-spacing: 0.06em;
}

.docs-topbar__right {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.docs-nav {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}

.docs-nav__link {
  padding: 6px var(--sp-3);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.docs-nav__link:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.docs-nav__link--active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: 600;
}

.docs-user {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.docs-avatar {
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

.docs-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.docs-back:hover {
  color: var(--color-primary);
}

.docs-main {
  flex: 1;
  min-width: 0;
}

@media (max-width: 720px) {
  .docs-topbar {
    padding: 0 var(--sp-4);
  }

  .docs-brand__text em,
  .docs-user__name {
    display: none;
  }

  .docs-back {
    font-size: var(--fs-xs);
  }
}
</style>
