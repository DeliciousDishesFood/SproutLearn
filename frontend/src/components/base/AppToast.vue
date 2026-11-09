<!-- 全局 toast：固定右下角，读屏可感知，最多同时保留 4 条。 -->
<script setup lang="ts">
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <div class="toast-stack" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast">
      <div
        v-for="item in ui.toasts"
        :key="item.id"
        class="app-toast"
        :class="`app-toast--${item.kind}`"
        role="status"
      >
        <span class="app-toast__icon" aria-hidden="true">
          <CheckCircle2 v-if="item.kind === 'success'" :size="18" :stroke-width="1.9" />
          <AlertTriangle v-else-if="item.kind === 'warning'" :size="18" :stroke-width="1.9" />
          <AlertCircle v-else-if="item.kind === 'error'" :size="18" :stroke-width="1.9" />
          <Info v-else :size="18" :stroke-width="1.9" />
        </span>
        <p class="app-toast__message">{{ item.message }}</p>
        <button class="app-toast__close" type="button" aria-label="关闭提示" @click="ui.dismiss(item.id)">
          <X :size="14" :stroke-width="2" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: var(--sp-5);
  bottom: var(--sp-5);
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  width: min(360px, calc(100vw - 32px));
  pointer-events: none;
}

.app-toast {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-3);
  border: 1px solid var(--color-border);
  border-left-width: 3px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: var(--shadow-2);
  pointer-events: auto;
}

.app-toast--success {
  border-left-color: var(--color-success);
}

.app-toast--warning {
  border-left-color: var(--color-warning);
}

.app-toast--error {
  border-left-color: var(--color-danger);
}

.app-toast--info {
  border-left-color: var(--color-primary);
}

.app-toast__icon {
  margin-top: 1px;
  flex-shrink: 0;
}

.app-toast--success .app-toast__icon {
  color: var(--color-success);
}

.app-toast--warning .app-toast__icon {
  color: var(--color-warning);
}

.app-toast--error .app-toast__icon {
  color: var(--color-danger);
}

.app-toast--info .app-toast__icon {
  color: var(--color-primary);
}

.app-toast__message {
  flex: 1;
  font-size: var(--fs-sm);
  line-height: 1.55;
  color: var(--color-text);
}

.app-toast__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.app-toast__close:hover {
  color: var(--color-text);
  background: var(--color-surface-alt);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 180ms ease-out, transform 180ms ease-out;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.toast-move {
  transition: transform 180ms ease-out;
}
</style>
