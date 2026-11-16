// 题干/选项选区触发“问问小芽”：忽略表单控件与编辑区，2–300 字才显示浮动按钮。
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

interface SelectionState {
  text: string
  x: number
  y: number
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    tag === 'SELECT' ||
    target.isContentEditable ||
    Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
  )
}

export function useAskSproutSelection(container: Ref<HTMLElement | null>, enabled: Ref<boolean>) {
  const state = ref<SelectionState | null>(null)

  function clear(): void {
    state.value = null
    const selection = window.getSelection()
    if (selection) selection.removeAllRanges()
  }

  function handleSelection(): void {
    if (!enabled.value || !container.value) return
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      state.value = null
      return
    }
    const text = selection.toString().trim()
    if (!text || text.length < 2 || text.length > 300) {
      state.value = null
      return
    }
    const anchor = selection.anchorNode
    const focus = selection.focusNode
    if (!anchor || !focus) {
      state.value = null
      return
    }
    if (!container.value.contains(anchor) || !container.value.contains(focus)) {
      state.value = null
      return
    }
    const range = selection.getRangeAt(0)
    const rect = range.getBoundingClientRect()
    if (!rect || (rect.width === 0 && rect.height === 0)) {
      state.value = null
      return
    }
    const x = Math.min(Math.max(rect.left + rect.width / 2, 110), window.innerWidth - 110)
    const y = Math.min(Math.max(rect.top - 8, 56), window.innerHeight - 60)
    state.value = { text, x, y }
  }

  function handlePointerDown(event: MouseEvent): void {
    if (!state.value) return
    const target = event.target
    if (target instanceof HTMLElement && target.closest('[data-ask-trigger]')) return
    // 点击题干/选项以外区域时收起浮动按钮
    if (!container.value || !container.value.contains(target as Node)) {
      state.value = null
    }
  }

  function handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Escape') state.value = null
  }

  onMounted(() => {
    document.addEventListener('mouseup', handleSelection)
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('mouseup', handleSelection)
    document.removeEventListener('mousedown', handlePointerDown)
    document.removeEventListener('keydown', handleKeyDown)
  })

  return { state, clear }
}
