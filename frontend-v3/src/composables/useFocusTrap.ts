// 可复用焦点陷阱：弹窗与移动抽屉共用。
// - 打开时记录触发元素、锁 body 滚动、聚焦首个可交互控件（无则容器）；
// - Tab / Shift+Tab 在容器内循环，Escape 只关闭最上层；
// - 关闭时恢复触发元素焦点（已卸载则跳过）与原始 overflow；
// - 组件卸载清理全部监听。
import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/** 多弹层栈：只有最上层的陷阱响应键盘，避免嵌套确认弹窗一起关闭。 */
let stack: symbol[] = []

export function useFocusTrap(options: {
  active: () => boolean
  container: Ref<HTMLElement | null>
  onEscape?: () => void
  initialFocus?: () => HTMLElement | null | undefined
}) {
  const token = Symbol('focus-trap')
  let restoreEl: HTMLElement | null = null
  let prevOverflow = ''
  let open = false

  function focusables(): HTMLElement[] {
    const root = options.container.value
    if (!root) return []
    return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null && el.getAttribute('aria-hidden') !== 'true',
    )
  }

  function focusInitial(): void {
    const root = options.container.value
    if (!root) return
    const custom = options.initialFocus?.()
    if (custom) {
      custom.focus()
      return
    }
    const first = focusables()[0]
    if (first) {
      first.focus()
      return
    }
    root.setAttribute('tabindex', '-1')
    root.focus()
  }

  function onKeydown(event: KeyboardEvent): void {
    if (!open || stack[stack.length - 1] !== token) return
    // 内部控件（如下拉）已处理并阻止默认行为时，不再关闭外层弹层。
    if (event.defaultPrevented) return
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      options.onEscape?.()
      return
    }
    if (event.key !== 'Tab') return
    const items = focusables()
    if (items.length === 0) {
      event.preventDefault()
      return
    }
    const first = items[0]
    const last = items[items.length - 1]
    const current = document.activeElement as HTMLElement | null
    const inside = current ? options.container.value?.contains(current) ?? false : false
    if (event.shiftKey) {
      if (!inside || current === first) {
        event.preventDefault()
        last.focus()
      }
    } else if (!inside || current === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function activate(): void {
    if (open) return
    open = true
    stack.push(token)
    restoreEl = document.activeElement instanceof HTMLElement ? document.activeElement : null
    prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeydown)
    void nextTick(focusInitial)
  }

  function deactivate(): void {
    if (!open) return
    open = false
    stack = stack.filter((item) => item !== token)
    document.removeEventListener('keydown', onKeydown)
    document.body.style.overflow = prevOverflow
    const target = restoreEl
    restoreEl = null
    // 触发按钮可能随弹窗一起卸载：只在仍然连接时恢复焦点。
    if (target && target.isConnected) void nextTick(() => target.focus())
  }

  watch(options.active, (value) => (value ? activate() : deactivate()), { immediate: true })

  onBeforeUnmount(() => {
    deactivate()
  })
}
