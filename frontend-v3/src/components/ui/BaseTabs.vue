<script setup lang="ts">
// 标签页：roving tabindex + 左右/Home/End 键盘切换，aria-controls 关联面板。
import { ref, useId } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    items: Array<{ key: string; label: string }>
    /** 面板容器 id（面板需配对 role="tabpanel" + aria-labelledby）。 */
    panelId?: string
    ariaLabel?: string
    /** 标签栏 id 前缀，便于面板用 aria-labelledby 指回当前标签。 */
    id?: string
  }>(),
  { panelId: '', ariaLabel: '', id: '' },
)

const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

const baseId = props.id || `tabs-${useId()}`
const tabs = ref<Array<HTMLButtonElement | null>>([])

function tabId(key: string): string {
  return `${baseId}-tab-${key.replace(/[^a-zA-Z0-9_-]/g, '-')}`
}

function setTabRef(el: unknown, index: number): void {
  tabs.value[index] = el as HTMLButtonElement | null
}

function activate(index: number, focus = false): void {
  const item = props.items[index]
  if (!item) return
  emit('update:modelValue', item.key)
  if (focus) tabs.value[index]?.focus()
}

function onKeydown(event: KeyboardEvent, index: number): void {
  const total = props.items.length
  if (total === 0) return
  let next = index
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % total
  else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index - 1 + total) % total
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = total - 1
  else return
  event.preventDefault()
  activate(next, true)
}
</script>

<template>
  <div class="tabs" role="tablist" :aria-label="ariaLabel || undefined">
    <button
      v-for="(item, index) in items"
      :id="tabId(item.key)"
      :key="item.key"
      :ref="(el) => setTabRef(el, index)"
      type="button"
      role="tab"
      class="tabs__item"
      :class="{ 'is-active': item.key === modelValue }"
      :aria-selected="item.key === modelValue"
      :aria-controls="panelId || undefined"
      :tabindex="item.key === modelValue ? 0 : -1"
      @click="emit('update:modelValue', item.key)"
      @keydown="onKeydown($event, index)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
