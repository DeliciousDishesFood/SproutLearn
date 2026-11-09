<!-- 基础按钮：变体、尺寸、loading 与整行宽度统一由 token 控制。 -->
<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-outline'
    size?: 'sm' | 'md'
    type?: 'button' | 'submit' | 'reset'
    loading?: boolean
    disabled?: boolean
    block?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    type: 'button',
    loading: false,
    disabled: false,
    block: false,
  },
)
</script>

<template>
  <button
    :type="type"
    class="app-button"
    :class="[`app-button--${variant}`, `app-button--${size}`, { 'app-button--block': block }]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <Loader2 v-if="loading" class="app-button__spinner" :size="16" :stroke-width="2" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  min-height: 38px;
  padding: 0 var(--sp-4);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-size: var(--fs-base);
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
  transition: background-color 170ms ease-out, border-color 170ms ease-out,
    color 170ms ease-out, box-shadow 170ms ease-out, transform 170ms ease-out;
}

.app-button:active:not(:disabled) {
  transform: translateY(1px);
}

.app-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.app-button--sm {
  min-height: 32px;
  padding: 0 var(--sp-3);
  font-size: var(--fs-sm);
}

.app-button--block {
  width: 100%;
}

.app-button--primary {
  color: var(--color-text-inverse);
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-1);
}

.app-button--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.app-button--secondary {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-color: color-mix(in srgb, var(--color-primary) 22%, transparent);
}

.app-button--secondary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
  border-color: color-mix(in srgb, var(--color-primary) 36%, transparent);
}

.app-button--ghost {
  color: var(--color-text-muted);
  background: transparent;
  border-color: var(--color-border);
}

.app-button--ghost:hover:not(:disabled) {
  color: var(--color-text);
  background: var(--color-surface-alt);
  border-color: var(--color-border-strong);
}

.app-button--danger {
  color: var(--color-text-inverse);
  background: var(--color-danger);
  border-color: var(--color-danger);
}

.app-button--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-danger) 86%, var(--color-text));
  border-color: color-mix(in srgb, var(--color-danger) 86%, var(--color-text));
}

.app-button--danger-outline {
  color: var(--color-danger);
  background: transparent;
  border-color: color-mix(in srgb, var(--color-danger) 45%, transparent);
}

.app-button--danger-outline:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
  border-color: var(--color-danger);
}

.app-button__spinner {
  animation: button-spin 0.9s linear infinite;
}

@keyframes button-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
