<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
    wide?: boolean
    closeOnMask?: boolean
  }>(),
  { description: '', wide: false, closeOnMask: true },
)

const emit = defineEmits<{ (event: 'close'): void }>()

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.open) emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) document.addEventListener('keydown', onKey)
    else document.removeEventListener('keydown', onKey)
    document.body.style.overflow = open ? 'hidden' : ''
  },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
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
      <div class="modal" :class="{ 'modal--wide': wide }" role="dialog" aria-modal="true">
        <header class="modal__head">
          <div>
            <h2>{{ title }}</h2>
            <p v-if="description">{{ description }}</p>
          </div>
          <button class="modal__close" type="button" aria-label="关闭" @click="emit('close')">
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
