<!-- 基础抽屉：右侧滑入，支持遮罩/ESC 关闭、头部与底部插槽。 -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    description?: string
    width?: string
    closeOnOverlay?: boolean
    preventClose?: boolean
  }>(),
  {
    width: '560px',
    closeOnOverlay: true,
    preventClose: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'close'): void
}>()

const panelRef = ref<HTMLElement | null>(null)
let previousOverflow = ''

function close(): void {
  if (props.preventClose) return
  emit('update:modelValue', false)
  emit('close')
}

function onOverlayClick(): void {
  if (props.closeOnOverlay) close()
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.modelValue) close()
}

watch(
  () => props.modelValue,
  (open: boolean) => {
    if (open) {
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKeydown)
      void nextTick(() => panelRef.value?.focus())
    } else {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeydown)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="modelValue" class="app-drawer" role="presentation" @click.self="onOverlayClick">
        <aside
          ref="panelRef"
          class="app-drawer__panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
          :style="{ width }"
        >
          <header class="app-drawer__head">
            <div>
              <h2 class="app-drawer__title">{{ title }}</h2>
              <p v-if="description" class="app-drawer__desc">{{ description }}</p>
            </div>
            <button class="app-drawer__close" type="button" aria-label="关闭抽屉" @click="close">
              <X :size="18" :stroke-width="1.8" />
            </button>
          </header>

          <div class="app-drawer__body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="app-drawer__foot">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.app-drawer {
  position: fixed;
  inset: 0;
  z-index: 95;
  display: flex;
  justify-content: flex-end;
  background: color-mix(in srgb, var(--color-text) 38%, transparent);
  backdrop-filter: blur(4px);
}

.app-drawer__panel {
  display: flex;
  flex-direction: column;
  max-width: 100vw;
  height: 100vh;
  background: var(--color-surface);
  box-shadow: var(--shadow-2);
  outline: none;
}

.app-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-5) var(--sp-5) var(--sp-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-alt);
}

.app-drawer__title {
  font-size: var(--fs-xl);
}

.app-drawer__desc {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.app-drawer__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.app-drawer__close:hover {
  color: var(--color-text);
  background: var(--color-surface);
}

.app-drawer__body {
  min-height: 0;
  padding: var(--sp-5);
  overflow-y: auto;
  flex: 1;
}

.app-drawer__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-alt);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 180ms ease-out;
}

.drawer-enter-active .app-drawer__panel,
.drawer-leave-active .app-drawer__panel {
  transition: transform 200ms ease-out;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .app-drawer__panel,
.drawer-leave-to .app-drawer__panel {
  transform: translateX(24px);
}

@media (max-width: 720px) {
  .app-drawer__panel {
    width: 100% !important;
  }
}
</style>
