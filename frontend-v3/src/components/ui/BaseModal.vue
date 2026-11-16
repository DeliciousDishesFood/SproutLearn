<script setup lang="ts">
import { ref, useId } from 'vue'
import { useFocusTrap } from '@/composables/useFocusTrap'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
    wide?: boolean
    closeOnMask?: boolean
    /** 一次性敏感信息弹窗：隐藏右上角关闭，只允许页脚显式关闭。 */
    hideClose?: boolean
  }>(),
  { description: '', wide: false, closeOnMask: true, hideClose: false },
)

const emit = defineEmits<{ (event: 'close'): void }>()

const panel = ref<HTMLElement | null>(null)
const titleId = `modal-title-${useId()}`
const descriptionId = `modal-desc-${useId()}`

// 焦点圈定、Escape、body overflow 与焦点恢复都由同一个 composable 负责。
useFocusTrap({
  active: () => props.open,
  container: panel,
  onEscape: () => {
    if (!props.closeOnMask) return
    emit('close')
  },
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-mask"
      role="presentation"
      @mousedown.self="closeOnMask && emit('close')"
    >
      <div
        ref="panel"
        class="modal"
        :class="{ 'modal--wide': wide }"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="description ? descriptionId : undefined"
      >
        <header class="modal__head">
          <div>
            <h2 :id="titleId">{{ title }}</h2>
            <p v-if="description" :id="descriptionId">{{ description }}</p>
          </div>
          <button
            v-if="!hideClose"
            class="modal__close"
            type="button"
            aria-label="关闭"
            @click="emit('close')"
          >
            ×
          </button>
        </header>
        <slot />
        <footer v-if="$slots.footer" class="modal__foot">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>
