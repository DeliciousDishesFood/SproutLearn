<!-- 基础下拉选择：原生 select 保证可访问性，外观由 token 统一。 -->
<script setup lang="ts">
import { useId } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import type { SelectOption } from '@/types'

withDefaults(
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

function handleChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<template>
  <div class="app-select" :class="{ 'app-select--error': Boolean(error) }">
    <label v-if="label" class="app-select__label" :for="id || resolvedId">{{ label }}</label>
    <div class="app-select__control">
      <select
        :id="id || resolvedId"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        :aria-invalid="Boolean(error) || undefined"
        :aria-describedby="error ? `${id || resolvedId}-error` : hint ? `${id || resolvedId}-hint` : undefined"
        class="app-select__element"
        @change="handleChange"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </select>
      <ChevronDown class="app-select__chevron" :size="16" :stroke-width="1.8" aria-hidden="true" />
    </div>
    <p v-if="error" :id="`${id || resolvedId}-error`" class="app-select__error">{{ error }}</p>
    <p v-else-if="hint" :id="`${id || resolvedId}-hint`" class="app-select__hint">{{ hint }}</p>
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
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
}

.app-select__element:hover {
  border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border-strong));
}

.app-select__element:focus {
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

.app-select__chevron {
  position: absolute;
  top: 50%;
  right: var(--sp-3);
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
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
