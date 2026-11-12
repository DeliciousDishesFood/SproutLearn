<!-- 基础下拉选择：自定义弹层保证长文本与窄容器下不被浏览器裁切，对外 API 与原生版一致。 -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
import type { SelectOption } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: string
    label?: string
    options: SelectOption[]
    placeholder?: string
    hint?: string
    error?: string
    id?: string
    disabled?: boolean
    required?: boolean
  }>(),
  {
    options: () => [],
    disabled: false,
    required: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'change', value: string): void
}>()

const resolvedId = useId()
const triggerId = computed(() => props.id || resolvedId)
const labelId = computed(() => `${triggerId.value}-label`)
const listboxId = computed(() => `${triggerId.value}-listbox`)

const open = ref(false)
const activeIndex = ref(-1)
const triggerRef = ref<HTMLButtonElement | null>(null)
const popupRef = ref<HTMLElement | null>(null)
const popupStyle = ref<Record<string, string>>({ visibility: 'hidden' })

const normalizedValue = computed(() =>
  props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue),
)
const selectedIndex = computed(() =>
  props.options.findIndex((option) => String(option.value) === normalizedValue.value),
)
const selectedOption = computed<SelectOption | null>(() =>
  selectedIndex.value >= 0 ? props.options[selectedIndex.value] : null,
)
const displayText = computed(
  () => selectedOption.value?.label ?? props.placeholder ?? '',
)
const showPlaceholder = computed(() => selectedOption.value === null)

function optionId(index: number): string {
  return `${listboxId.value}-option-${index}`
}

function firstEnabledIndex(from = 0): number {
  for (let index = from; index < props.options.length; index += 1) {
    if (!props.options[index].disabled) return index
  }
  return -1
}

function lastEnabledIndex(): number {
  for (let index = props.options.length - 1; index >= 0; index -= 1) {
    if (!props.options[index].disabled) return index
  }
  return -1
}

function moveActive(delta: 1 | -1): void {
  if (props.options.length === 0) return
  let index = activeIndex.value
  for (let step = 0; step < props.options.length; step += 1) {
    index = (index + delta + props.options.length) % props.options.length
    if (!props.options[index].disabled) {
      activeIndex.value = index
      scrollActiveIntoView()
      return
    }
  }
}

function scrollActiveIntoView(): void {
  if (!open.value || activeIndex.value < 0) return
  const element = document.getElementById(optionId(activeIndex.value))
  element?.scrollIntoView({ block: 'nearest' })
}

function updatePosition(): void {
  const trigger = triggerRef.value
  const popup = popupRef.value
  if (!open.value || !trigger || !popup) return

  const rect = trigger.getBoundingClientRect()
  const gap = 4
  const margin = 8
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const maxWidth = Math.min(480, viewportWidth - 16)
  const popupWidth = Math.min(popup.getBoundingClientRect().width, maxWidth)
  const left = Math.max(margin, Math.min(rect.left, viewportWidth - margin - popupWidth))

  const spaceBelow = viewportHeight - rect.bottom - gap - margin
  const spaceAbove = rect.top - gap - margin
  const placeAbove = spaceBelow < 220 && spaceAbove > spaceBelow
  const maxHeight = Math.max(160, Math.min(320, placeAbove ? spaceAbove : spaceBelow))

  popupStyle.value = {
    left: `${Math.round(left)}px`,
    minWidth: `${Math.round(rect.width)}px`,
    maxWidth: `${Math.round(maxWidth)}px`,
    maxHeight: `${Math.round(maxHeight)}px`,
    ...(placeAbove
      ? { bottom: `${Math.round(viewportHeight - rect.top + gap)}px` }
      : { top: `${Math.round(rect.bottom + gap)}px` }),
    visibility: 'visible',
  }
}

function openPopup(direction: 1 | -1 = 1): void {
  if (open.value || props.disabled || props.options.length === 0) return
  const rect = triggerRef.value?.getBoundingClientRect()
  if (!rect) return

  const start = selectedIndex.value >= 0
    ? selectedIndex.value
    : direction === 1
      ? firstEnabledIndex()
      : lastEnabledIndex()
  activeIndex.value = start
  popupStyle.value = {
    left: `${Math.round(rect.left)}px`,
    top: `${Math.round(rect.bottom + 4)}px`,
    minWidth: `${Math.round(rect.width)}px`,
    maxWidth: `${Math.round(Math.min(480, window.innerWidth - 16))}px`,
    visibility: 'hidden',
  }
  open.value = true

  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
  document.addEventListener('pointerdown', onDocumentPointerDown, true)

  void nextTick(() => {
    updatePosition()
    scrollActiveIntoView()
  })
}

function closePopup(): void {
  if (!open.value) return
  open.value = false
  activeIndex.value = -1
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
  document.removeEventListener('pointerdown', onDocumentPointerDown, true)
}

function choose(index: number): void {
  const option = props.options[index]
  if (!option || option.disabled) return
  const value = String(option.value)
  closePopup()
  triggerRef.value?.focus()
  if (value === normalizedValue.value) return
  emit('update:modelValue', value)
  emit('change', value)
}

function onDocumentPointerDown(event: PointerEvent): void {
  const target = event.target as Node | null
  if (!target) return
  if (triggerRef.value?.contains(target) || popupRef.value?.contains(target)) return
  closePopup()
}

function onTriggerClick(): void {
  if (open.value) closePopup()
  else openPopup()
}

function onOptionMouseDown(event: MouseEvent): void {
  event.preventDefault()
}

function onTriggerKeydown(event: KeyboardEvent): void {
  if (props.disabled) return
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      if (open.value) moveActive(1)
      else openPopup(1)
      break
    case 'ArrowUp':
      event.preventDefault()
      if (open.value) moveActive(-1)
      else openPopup(-1)
      break
    case 'Enter':
    case ' ':
      event.preventDefault()
      if (open.value) {
        if (activeIndex.value >= 0) choose(activeIndex.value)
        else closePopup()
      } else {
        openPopup()
      }
      break
    case 'Home':
      if (!open.value) return
      event.preventDefault()
      activeIndex.value = firstEnabledIndex()
      scrollActiveIntoView()
      break
    case 'End':
      if (!open.value) return
      event.preventDefault()
      activeIndex.value = lastEnabledIndex()
      scrollActiveIntoView()
      break
    case 'Escape':
      if (open.value) {
        event.preventDefault()
        event.stopPropagation()
        closePopup()
      }
      break
    case 'Tab':
      if (open.value) closePopup()
      break
    default:
      break
  }
}

watch(
  () => props.disabled,
  (value) => {
    if (value) closePopup()
  },
)

watch(
  () => props.options.length,
  (length) => {
    if (length === 0) closePopup()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
  document.removeEventListener('pointerdown', onDocumentPointerDown, true)
})
</script>

<template>
  <div class="app-select" :class="{ 'app-select--error': Boolean(error), 'app-select--open': open }">
    <label v-if="label" :id="labelId" class="app-select__label" :for="triggerId">{{ label }}</label>
    <div class="app-select__control">
      <button
        :id="triggerId"
        ref="triggerRef"
        type="button"
        class="app-select__element"
        :class="{ 'app-select__element--open': open }"
        role="combobox"
        aria-haspopup="listbox"
        :aria-expanded="open"
        :aria-controls="listboxId"
        :aria-activedescendant="open && activeIndex >= 0 ? optionId(activeIndex) : undefined"
        :aria-labelledby="label ? labelId : undefined"
        :aria-invalid="Boolean(error) || undefined"
        :aria-required="required || undefined"
        :aria-describedby="error ? `${triggerId}-error` : hint ? `${triggerId}-hint` : undefined"
        :disabled="disabled"
        @click="onTriggerClick"
        @keydown="onTriggerKeydown"
      >
        <span class="app-select__value" :class="{ 'app-select__value--placeholder': showPlaceholder }">
          {{ displayText }}
        </span>
        <ChevronDown
          class="app-select__chevron"
          :class="{ 'app-select__chevron--open': open }"
          :size="16"
          :stroke-width="1.8"
          aria-hidden="true"
        />
      </button>
    </div>
    <p v-if="error" :id="`${triggerId}-error`" class="app-select__error">{{ error }}</p>
    <p v-else-if="hint" :id="`${triggerId}-hint`" class="app-select__hint">{{ hint }}</p>

    <Teleport to="body">
      <div
        v-if="open"
        :id="listboxId"
        ref="popupRef"
        class="app-select__popup"
        :style="popupStyle"
        role="listbox"
        :aria-labelledby="label ? labelId : triggerId"
      >
        <div
          v-for="(option, index) in options"
          :id="optionId(index)"
          :key="index"
          class="app-select__option"
          :class="{
            'app-select__option--active': index === activeIndex,
            'app-select__option--selected': index === selectedIndex,
            'app-select__option--disabled': Boolean(option.disabled),
          }"
          role="option"
          :aria-selected="index === selectedIndex"
          :aria-disabled="option.disabled || undefined"
          @mouseenter="activeIndex = index"
          @mousedown="onOptionMouseDown"
          @click="choose(index)"
        >
          <span class="app-select__option-text">{{ option.label }}</span>
          <Check
            v-if="index === selectedIndex"
            class="app-select__check"
            :size="14"
            :stroke-width="2.2"
            aria-hidden="true"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.app-select {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.app-select__label {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.app-select__control {
  position: relative;
}

.app-select__element {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 40px;
  padding: 9px 36px 9px var(--sp-3);
  appearance: none;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-base);
  line-height: 1.2;
  text-align: left;
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
}

.app-select__element:hover {
  border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border-strong));
}

.app-select__element:focus-visible,
.app-select__element--open {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.app-select__element:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.app-select--error .app-select__element {
  border-color: var(--color-danger);
}

.app-select__value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-select__value--placeholder {
  color: var(--color-text-muted);
}

.app-select__chevron {
  position: absolute;
  top: 50%;
  right: var(--sp-3);
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
  transition: transform 160ms ease-out;
}

.app-select__chevron--open {
  transform: translateY(-50%) rotate(180deg);
}

.app-select__popup {
  position: fixed;
  z-index: 120;
  width: max-content;
  padding: var(--sp-1);
  overflow-y: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: var(--shadow-2);
}

.app-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  padding: 8px var(--sp-2);
  border-radius: var(--radius-xs);
  font-size: var(--fs-sm);
  line-height: 1.5;
  cursor: pointer;
}

.app-select__option--active {
  background: var(--color-primary-soft);
}

.app-select__option--selected {
  font-weight: 600;
}

.app-select__option--disabled {
  color: var(--color-text-muted);
  opacity: 0.55;
  cursor: not-allowed;
}

.app-select__option--disabled.app-select__option--active {
  background: transparent;
}

.app-select__option-text {
  display: -webkit-box;
  min-width: 0;
  overflow: hidden;
  overflow-wrap: anywhere;
  white-space: normal;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.app-select__check {
  flex-shrink: 0;
  color: var(--color-primary);
}

.app-select__error {
  font-size: var(--fs-xs);
  color: var(--color-danger);
}

.app-select__hint {
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
}
</style>
