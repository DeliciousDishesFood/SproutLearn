<!-- 骨架屏：text/title/card/table/avatar/stat 六种形态，避免布局跳动。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'text' | 'title' | 'card' | 'table' | 'avatar' | 'stat'
    rows?: number
    width?: string
    height?: string
  }>(),
  {
    variant: 'text',
    rows: 1,
    width: '100%',
    height: '',
  },
)
</script>

<template>
  <div
    class="app-skeleton"
    :class="`app-skeleton--${variant}`"
    :style="{ width }"
    role="status"
    aria-label="加载中"
  >
    <template v-if="variant === 'table'">
      <div v-for="rowIndex in rows" :key="rowIndex" class="app-skeleton__row">
        <span v-for="cellIndex in 4" :key="cellIndex" class="app-skeleton__bar" />
      </div>
    </template>
    <template v-else-if="variant === 'card'">
      <span class="app-skeleton__bar app-skeleton__bar--avatar" />
      <span class="app-skeleton__bar app-skeleton__bar--lg" />
      <span class="app-skeleton__bar" />
      <span class="app-skeleton__bar app-skeleton__bar--short" />
    </template>
    <template v-else-if="variant === 'stat'">
      <span class="app-skeleton__bar app-skeleton__bar--xs" />
      <span class="app-skeleton__bar app-skeleton__bar--xl" />
      <span class="app-skeleton__bar app-skeleton__bar--short" />
    </template>
    <template v-else-if="variant === 'avatar'">
      <span class="app-skeleton__bar app-skeleton__bar--avatar" />
    </template>
    <template v-else>
      <span
        v-for="rowIndex in rows"
        :key="rowIndex"
        class="app-skeleton__bar"
        :class="variant === 'title' ? 'app-skeleton__bar--title' : ''"
        :style="height ? { height } : undefined"
      />
    </template>
  </div>
</template>

<style scoped>
.app-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  width: 100%;
}

.app-skeleton__bar,
.app-skeleton__row span {
  position: relative;
  display: block;
  height: 12px;
  overflow: hidden;
  border-radius: var(--radius-xs);
  background: color-mix(in srgb, var(--color-border) 58%, var(--color-surface));
}

.app-skeleton__bar::after,
.app-skeleton__row span::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--color-surface) 72%, transparent),
    transparent
  );
  animation: skeleton-shimmer 1.35s ease-out infinite;
}

.app-skeleton__bar--title {
  height: 18px;
}

.app-skeleton__bar--lg {
  height: 18px;
  width: 68%;
}

.app-skeleton__bar--xs {
  height: 9px;
  width: 38%;
}

.app-skeleton__bar--xl {
  height: 26px;
  width: 54%;
}

.app-skeleton__bar--short {
  width: 48%;
}

.app-skeleton__bar--avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
}

.app-skeleton--card {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.app-skeleton__row {
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr 0.8fr;
  gap: var(--sp-4);
  padding: var(--sp-2) 0;
}

@keyframes skeleton-shimmer {
  to {
    transform: translateX(100%);
  }
}
</style>
