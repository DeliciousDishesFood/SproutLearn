<!-- 统计卡：数值、标签、提示与图标槽，工作台四卡统一尺寸与基线。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    tone?: 'default' | 'primary' | 'accent' | 'success' | 'warning'
  }>(),
  {
    hint: '',
    tone: 'default',
  },
)
</script>

<template>
  <div class="app-stat" :class="`app-stat--${tone}`">
    <div v-if="$slots.icon" class="app-stat__icon" aria-hidden="true">
      <slot name="icon" />
    </div>
    <div class="app-stat__body">
      <p class="app-stat__label">{{ label }}</p>
      <p class="app-stat__value tabular">{{ value }}</p>
      <p v-if="hint" class="app-stat__hint">{{ hint }}</p>
    </div>
    <div v-if="$slots.footer" class="app-stat__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.app-stat {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  min-height: 108px;
  padding: var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
  overflow: hidden;
}

.app-stat::before {
  content: '';
  position: absolute;
  top: var(--sp-4);
  bottom: var(--sp-4);
  left: 0;
  width: 3px;
  border-radius: 0 999px 999px 0;
  background: var(--color-border-strong);
}

.app-stat--primary::before {
  background: var(--color-primary);
}

.app-stat--accent::before {
  background: var(--color-accent);
}

.app-stat--success::before {
  background: var(--color-success);
}

.app-stat--warning::before {
  background: var(--color-warning);
}

.app-stat__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.app-stat--primary .app-stat__icon {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.app-stat--accent .app-stat__icon {
  background: color-mix(in srgb, var(--color-accent) 12%, var(--color-surface));
  color: color-mix(in srgb, var(--color-accent) 78%, var(--color-text));
}

.app-stat--success .app-stat__icon {
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
  color: var(--color-success);
}

.app-stat--warning .app-stat__icon {
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-surface));
  color: var(--color-warning);
}

.app-stat__body {
  min-width: 0;
  flex: 1;
}

.app-stat__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.app-stat__value {
  margin-top: 2px;
  color: var(--color-text);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.app-stat--primary .app-stat__value {
  color: var(--color-primary);
}

.app-stat--accent .app-stat__value {
  color: color-mix(in srgb, var(--color-accent) 78%, var(--color-text));
}

.app-stat__hint {
  margin-top: 4px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-stat__footer {
  align-self: flex-end;
  flex-shrink: 0;
}
</style>
