// 全局 UI 状态：toast、当前班级、未读数、移动端导航开合。
import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  message: string
  type: ToastType
}

const CURRENT_CLASS_KEY = 'sprout.v3.currentClassId'

function readClassId(): number | null {
  const raw = localStorage.getItem(CURRENT_CLASS_KEY)
  if (!raw) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<ToastItem[]>([])
  const currentClassId = ref<number | null>(readClassId())
  const unreadCount = ref(0)
  const mobileNavOpen = ref(false)
  let seq = 0

  function toast(message: string, type: ToastType = 'info', duration = 2800): void {
    const id = ++seq
    toasts.value = [...toasts.value, { id, message, type }]
    window.setTimeout(() => dismiss(id), duration)
  }

  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }

  function setCurrentClassId(classId: number | null): void {
    currentClassId.value = classId
    if (classId) localStorage.setItem(CURRENT_CLASS_KEY, String(classId))
    else localStorage.removeItem(CURRENT_CLASS_KEY)
  }

  function setUnreadCount(count: number): void {
    unreadCount.value = Math.max(0, count)
  }

  return {
    toasts,
    currentClassId,
    unreadCount,
    mobileNavOpen,
    toast,
    dismiss,
    setCurrentClassId,
    setUnreadCount,
  }
})
