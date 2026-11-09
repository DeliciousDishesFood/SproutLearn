<!-- 轻量状态标签：圆角 6，仅使用 token 派生色。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: 'neutral' | 'primary' | 'accent' | 'success' | 'warning' | 'danger'
    dot?: boolean
  }>(),
  {
    tone: 'neutral',
    dot: false,
  },
)
</script>

<template>
  <span class="app-tag" :class="`app-tag--${tone}`">
    <span v-if="dot" class="app-tag__dot" aria-hidden="true" />
    <slot />
  </span>
</template>

<style scoped>
.app-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
}

.app-tag__dot {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: currentColor;
}

.app-tag--neutral {
  color: var(--color-text-muted);
  background: var(--color-surface-alt);
  border-color: var(--color-border);
}

.app-tag--primary {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-color: color-mix(in srgb, var(--color-primary) 18%, transparent);
}

.app-tag--accent {
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
  background: color-mix(in srgb, var(--color-accent) 13%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-accent) 26%, transparent);
}

.app-tag--success {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-success) 22%, transparent);
}

.app-tag--warning {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-warning) 22%, transparent);
}

.app-tag--danger {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 9%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-danger) 22%, transparent);
}
</style>
