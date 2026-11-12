<!-- 区块容器：标题、说明、右侧动作与内容四件套，统一 panel 外观与内边距。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    description?: string
    panel?: boolean
    padded?: boolean
  }>(),
  {
    title: '',
    description: '',
    panel: true,
    padded: true,
  },
)
</script>

<template>
  <section class="app-section" :class="{ 'app-section--panel': panel }">
    <header v-if="title || $slots.actions" class="app-section__head">
      <div class="app-section__text">
        <h2 v-if="title" class="app-section__title">{{ title }}</h2>
        <p v-if="description" class="app-section__desc">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="app-section__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="app-section__body" :class="{ 'app-section__body--padded': padded }">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.app-section {
  min-width: 0;
}

.app-section--panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.app-section__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
  border-bottom: 1px solid var(--color-border);
}

.app-section__text {
  min-width: 0;
}

.app-section__title {
  color: var(--color-text);
  font-size: var(--fs-lg);
  font-weight: 600;
  line-height: 1.35;
}

.app-section__desc {
  max-width: 680px;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.app-section__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-2);
  flex-shrink: 0;
}

.app-section__body {
  min-width: 0;
}

.app-section__body--padded {
  padding: var(--sp-5);
}

@media (max-width: 720px) {
  .app-section__head {
    flex-direction: column;
  }
}
</style>
