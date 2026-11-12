<!-- 标签页：下划线/胶囊两档，支持计数与键盘左右切换；页面不再各写一套 tab。 -->
<script setup lang="ts">
import { ref } from 'vue'

interface AppTabItem {
  key: string
  label: string
  count?: number
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    items: AppTabItem[]
    variant?: 'underline' | 'pill'
  }>(),
  {
    variant: 'underline',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const barRef = ref<HTMLElement | null>(null)

function select(item: AppTabItem): void {
  if (item.disabled || item.key === props.modelValue) return
  emit('update:modelValue', item.key)
}

function onKeydown(event: KeyboardEvent, index: number): void {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
  event.preventDefault()
  const enabled = props.items.filter((item) => !item.disabled)
  if (enabled.length === 0) return
  const current = props.items[index]
  const enabledIndex = enabled.findIndex((item) => item.key === current.key)
  const nextIndex =
    event.key === 'ArrowRight'
      ? (enabledIndex + 1) % enabled.length
      : (enabledIndex - 1 + enabled.length) % enabled.length
  const next = enabled[nextIndex]
  if (!next) return
  emit('update:modelValue', next.key)
  const buttons = barRef.value?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
  buttons?.[props.items.indexOf(next)]?.focus()
}
</script>

<template>
  <div class="app-tabs" :class="`app-tabs--${variant}`">
    <div ref="barRef" class="app-tabs__bar" role="tablist">
      <button
        v-for="(item, index) in items"
        :key="item.key"
        type="button"
        role="tab"
        class="app-tabs__item"
        :class="{ 'app-tabs__item--active': item.key === modelValue }"
        :aria-selected="item.key === modelValue"
        :disabled="item.disabled"
        :tabindex="item.key === modelValue ? 0 : -1"
        @click="select(item)"
        @keydown="onKeydown($event, index)"
      >
        <span>{{ item.label }}</span>
        <span v-if="item.count !== undefined" class="app-tabs__count tabular">{{ item.count }}</span>
      </button>
    </div>
    <div v-if="$slots.extra" class="app-tabs__extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<style scoped>
.app-tabs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  min-width: 0;
}

.app-tabs__bar {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  min-width: 0;
  overflow-x: auto;
}

.app-tabs__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 var(--sp-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  font-weight: 500;
  white-space: nowrap;
  transition: color 160ms var(--ease-out), background-color 160ms var(--ease-out);
}

.app-tabs__item:hover:not(:disabled) {
  color: var(--color-text);
  background: var(--color-surface-alt);
}

.app-tabs__item:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.app-tabs__count {
  min-width: 20px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}

.app-tabs__item--active {
  color: var(--color-primary);
  font-weight: 600;
}

.app-tabs__extra {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-shrink: 0;
}

.app-tabs--underline .app-tabs__bar {
  border-bottom: 1px solid var(--color-border);
}

.app-tabs--underline .app-tabs__item {
  position: relative;
  border-radius: 0;
}

.app-tabs--underline .app-tabs__item--active {
  background: transparent;
}

.app-tabs--underline .app-tabs__item--active::after {
  content: '';
  position: absolute;
  right: var(--sp-3);
  bottom: -1px;
  left: var(--sp-3);
  height: 2px;
  border-radius: 999px;
  background: var(--color-primary);
}

.app-tabs--pill .app-tabs__bar {
  padding: var(--sp-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.app-tabs--pill .app-tabs__item--active {
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.app-tabs--pill .app-tabs__item--active .app-tabs__count {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
</style>
