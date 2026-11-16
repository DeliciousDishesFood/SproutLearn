// toast 快捷方法：统一走 ui store。
import { useUiStore, type ToastType } from '@/stores/ui'

export function useToast() {
  const ui = useUiStore()
  return {
    toast: (message: string, type: ToastType = 'info', duration?: number) =>
      ui.toast(message, type, duration),
    success: (message: string) => ui.toast(message, 'success'),
    error: (message: string) => ui.toast(message, 'error'),
    info: (message: string) => ui.toast(message, 'info'),
  }
}
