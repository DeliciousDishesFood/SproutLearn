<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { TOAST_EVENT } from '@/api/client'
import { useUiStore, type ToastType } from '@/stores/ui'

const ui = useUiStore()

function onToast(event: Event): void {
  const detail = (event as CustomEvent<{ message?: string; type?: ToastType }>).detail
  if (!detail?.message) return
  ui.toast(detail.message, detail.type ?? 'info')
}

onMounted(() => window.addEventListener(TOAST_EVENT, onToast))
onBeforeUnmount(() => window.removeEventListener(TOAST_EVENT, onToast))
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <div v-for="item in ui.toasts" :key="item.id" class="toast" :class="`toast--${item.type}`">
      {{ item.message }}
    </div>
  </div>
</template>
