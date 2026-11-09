<!-- 基础弹窗：Teleport 到 body，支持遮罩/ESC 关闭、危险确认与 loading。 -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    description?: string
    width?: string
    confirmText?: string
    cancelText?: string
    confirmVariant?: 'primary' | 'danger'
    confirmLoading?: boolean
    hideFooter?: boolean
    closeOnOverlay?: boolean
  }>(),
  {
    width: '480px',
    confirmText: '确认',
    cancelText: '取消',
    confirmVariant: 'primary',
    confirmLoading: false,
    hideFooter: false,
    closeOnOverlay: true,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'confirm'): void
  (event: 'cancel'): void
  (event: 'close'): void
}>()

const panelRef = ref<HTMLElement | null>(null)
let previousOverflow = ''

function close(): void {
  emit('update:modelValue', false)
  emit('close')
}

function cancel(): void {
  if (props.confirmLoading) return
  emit('cancel')
  close()
}

function confirm(): void {
  emit('confirm')
}

function onOverlayClick(): void {
  if (props.closeOnOverlay) cancel()
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.modelValue) {
    cancel()
  }
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
    <Transition name="modal">
      <div v-if="modelValue" class="app-modal" role="presentation" @click.self="onOverlayClick">
        <section
          ref="panelRef"
          class="app-modal__panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
          :style="{ maxWidth: width }"
        >
          <header class="app-modal__head">
            <div>
              <h2 class="app-modal__title">{{ title }}</h2>
              <p v-if="description" class="app-modal__desc">{{ description }}</p>
            </div>
            <button class="app-modal__close" type="button" aria-label="关闭弹窗" @click="cancel">
              <X :size="18" :stroke-width="1.8" />
            </button>
          </header>

          <div class="app-modal__body">
            <slot />
          </div>

          <footer v-if="!hideFooter" class="app-modal__foot">
            <slot name="footer">
              <AppButton variant="ghost" :disabled="confirmLoading" @click="cancel">{{ cancelText }}</AppButton>
              <AppButton
                :variant="confirmVariant === 'danger' ? 'danger' : 'primary'"
                :loading="confirmLoading"
                @click="confirm"
              >
                {{ confirmText }}
              </AppButton>
            </slot>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.app-modal {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--sp-5);
  background: color-mix(in srgb, var(--color-text) 38%, transparent);
  backdrop-filter: blur(4px);
}

.app-modal__panel {
  width: 100%;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-2);
  outline: none;
}

.app-modal__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-5) var(--sp-5) var(--sp-4);
}

.app-modal__title {
  font-size: var(--fs-xl);
}

.app-modal__desc {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.app-modal__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  flex-shrink: 0;
  transition: background-color 160ms ease-out, color 160ms ease-out;
}

.app-modal__close:hover {
  color: var(--color-text);
  background: var(--color-surface-alt);
}

.app-modal__body {
  padding: 0 var(--sp-5) var(--sp-5);
}

.app-modal__foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-alt);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 180ms ease-out;
}

.modal-enter-active .app-modal__panel,
.modal-leave-active .app-modal__panel {
  transition: transform 180ms ease-out, opacity 180ms ease-out;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .app-modal__panel,
.modal-leave-to .app-modal__panel {
  opacity: 0;
  transform: translateY(6px) scale(0.985);
}

@media (max-width: 720px) {
  .app-modal {
    align-items: flex-end;
    padding: var(--sp-3);
  }

  .app-modal__panel {
    max-height: calc(100vh - 24px);
  }
}
</style>
