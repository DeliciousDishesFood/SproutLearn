<script setup lang="ts">
// 自定义下拉：触发器 + 浮层列表（Teleport 到 body，固定定位，不挤占文档流）。
import { computed, nextTick, onBeforeUnmount, ref, type Component } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'

type SelectValue = string | number | boolean | null

interface SelectOption {
  label: string
  value: SelectValue
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    options: SelectOption[]
    placeholder?: string
    disabled?: boolean
    size?: 'sm' | 'md'
    ariaLabel?: string
    id?: string
    /** 触发器左侧语义图标（如题库用 Library）。 */
    icon?: Component
  }>(),
  { placeholder: '请选择', disabled: false, size: 'md', ariaLabel: '', id: undefined, icon: undefined },
)

const model = defineModel<any>({ default: null })

const open = ref(false)
const activeIndex = ref(-1)
const trigger = ref<HTMLButtonElement | null>(null)
const pop = ref<HTMLDivElement | null>(null)
const popStyle = ref<Record<string, string>>({})
const listId = `select-${Math.random().toString(36).slice(2, 8)}`

function same(a: SelectValue, b: SelectValue): boolean {
  if (a === b) return true
  if (a === null || a === undefined || b === null || b === undefined) return false
  return String(a) === String(b)
}

const selected = computed(() => props.options.find((item) => same(item.value, model.value)) ?? null)

function position(): void {
  const rect = trigger.value?.getBoundingClientRect()
  if (!rect) return
  const height = pop.value?.offsetHeight ?? 0
  const spaceBelow = window.innerHeight - rect.bottom
  const openUp = spaceBelow < height + 12 && rect.top > height + 12
  popStyle.value = {
    left: `${Math.round(rect.left)}px`,
    width: `${Math.round(rect.width)}px`,
    top: `${Math.round(openUp ? rect.top - height - 6 : rect.bottom + 6)}px`,
  }
}

function onDocPointer(event: Event): void {
  const target = event.target as Node
  if (trigger.value?.contains(target) || pop.value?.contains(target)) return
  close()
}

function onViewportChange(event?: Event): void {
  // 浮层内部滚动不关闭；页面滚动/缩放时收起，避免与触发器错位。
  if (event?.target instanceof Node && pop.value?.contains(event.target)) return
  close()
}

function bind(): void {
  document.addEventListener('pointerdown', onDocPointer)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
}

function unbind(): void {
  document.removeEventListener('pointerdown', onDocPointer)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
}

async function show(): Promise<void> {
  if (props.disabled || props.options.length === 0) return
  open.value = true
  const current = props.options.findIndex((item) => same(item.value, model.value))
  activeIndex.value = current >= 0 ? current : 0
  bind()
  await nextTick()
  position()
  pop.value?.querySelector<HTMLElement>('.select__option.is-active')?.scrollIntoView({ block: 'nearest' })
}

function close(): void {
  if (!open.value) return
  open.value = false
  unbind()
}

function toggle(): void {
  if (open.value) close()
  else void show()
}

function choose(index: number): void {
  const option = props.options[index]
  if (!option || option.disabled) return
  model.value = option.value
  close()
  trigger.value?.focus()
}

function move(step: number): void {
  const total = props.options.length
  if (total === 0) return
  let next = activeIndex.value
  for (let i = 0; i < total; i += 1) {
    next = (next + step + total) % total
    if (!props.options[next]?.disabled) break
  }
  activeIndex.value = next
  pop.value?.querySelectorAll<HTMLElement>('.select__option')[next]?.scrollIntoView({ block: 'nearest' })
}

function onKeydown(event: KeyboardEvent): void {
  if (props.disabled) return
  if (!open.value) {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
      event.preventDefault()
      void show()
    }
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  } else if (event.key === 'Home') {
    event.preventDefault()
    activeIndex.value = 0
  } else if (event.key === 'End') {
    event.preventDefault()
    activeIndex.value = props.options.length - 1
  } else if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    choose(activeIndex.value)
  } else if (event.key === 'Tab') {
    close()
  }
}

onBeforeUnmount(unbind)
</script>

<template>
  <div class="select" :class="[`select--${size}`, { 'is-open': open, 'is-disabled': disabled }]">
    <button
      :id="id"
      ref="trigger"
      class="select__trigger"
      type="button"
      :disabled="disabled"
      :aria-label="ariaLabel || undefined"
      :aria-expanded="open"
      :aria-controls="open ? listId : undefined"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown="onKeydown"
    >
      <span v-if="icon" class="select__icon" aria-hidden="true">
        <component :is="icon" :size="14" />
      </span>
      <span class="select__value" :class="{ 'is-placeholder': !selected }">
        {{ selected ? selected.label : placeholder }}
      </span>
      <ChevronDown class="select__chevron" :size="14" aria-hidden="true" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        :id="listId"
        ref="pop"
        class="select__pop"
        role="listbox"
        :aria-label="ariaLabel || undefined"
        :style="popStyle"
      >
        <button
          v-for="(option, index) in options"
          :key="String(option.value) + index"
          class="select__option"
          :class="{ 'is-active': index === activeIndex, 'is-selected': same(option.value, model) }"
          type="button"
          role="option"
          :aria-selected="same(option.value, model)"
          :disabled="option.disabled"
          @mouseenter="activeIndex = index"
          @click="choose(index)"
        >
          <span class="select__option-label">{{ option.label }}</span>
          <Check v-if="same(option.value, model)" :size="14" aria-hidden="true" />
        </button>
      </div>
    </Teleport>
  </div>
</template>
