// 全局 UI 状态：仅放跨页面 toast，不承载业务数据。
import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ToastKind } from '@/types'
import { TOAST_DURATION_MS } from '@/utils/constants'

export interface ToastItem {
  id: number
  message: string
  kind: ToastKind
}

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<ToastItem[]>([])
  let nextId = 1

  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }

  function toast(message: string, kind: ToastKind = 'info', duration = TOAST_DURATION_MS): number {
    if (!message) return 0
    const id = nextId++
    toasts.value = [...toasts.value.slice(-3), { id, message, kind }]
    window.setTimeout(() => dismiss(id), duration)
    return id
  }

  function success(message: string): number {
    return toast(message, 'success')
  }

  function error(message: string): number {
    return toast(message, 'error')
  }

  function warning(message: string): number {
    return toast(message, 'warning')
  }

  return { toasts, toast, dismiss, success, error, warning }
})
