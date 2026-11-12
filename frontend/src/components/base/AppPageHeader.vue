<!-- 页面头：统一 eyebrow、标题、说明与右侧主动作，页面不再各自拼 hero。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    eyebrow?: string
    description?: string
    compact?: boolean
  }>(),
  {
    eyebrow: '',
    description: '',
    compact: false,
  },
)
</script>

<template>
  <header class="app-page-header" :class="{ 'app-page-header--compact': compact }">
    <div class="app-page-header__text">
      <p v-if="eyebrow" class="app-page-header__eyebrow">{{ eyebrow }}</p>
      <h1 class="app-page-header__title">{{ title }}</h1>
      <p v-if="description" class="app-page-header__desc">{{ description }}</p>
      <div v-if="$slots.meta" class="app-page-header__meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="app-page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.app-page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-5);
  margin-bottom: var(--sp-5);
}

.app-page-header--compact {
  margin-bottom: var(--sp-4);
}

.app-page-header__text {
  min-width: 0;
}

.app-page-header__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.app-page-header__eyebrow::before {
  content: '';
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: var(--color-accent);
}

.app-page-header__title {
  color: var(--color-text);
  font-size: var(--fs-2xl);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.015em;
}

.app-page-header__desc {
  max-width: 720px;
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.app-page-header__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-3);
  margin-top: var(--sp-3);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.app-page-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--sp-2);
  flex-shrink: 0;
}

@media (max-width: 720px) {
  .app-page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .app-page-header__actions {
    justify-content: flex-start;
  }
}
</style>
