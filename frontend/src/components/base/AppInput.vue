<!-- 基础输入框：标签、错误态、提示、密码显示切换，样式全部来自 token。 -->
<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    modelValue: string
    label?: string
    type?: 'text' | 'password' | 'email' | 'tel' | 'search'
    placeholder?: string
    hint?: string
    error?: string
    name?: string
    id?: string
    autocomplete?: string
    maxlength?: number
    disabled?: boolean
    required?: boolean
    inputmode?: 'text' | 'numeric' | 'tel' | 'email' | 'search' | 'none'
  }>(),
  {
    type: 'text',
    autocomplete: 'off',
    disabled: false,
    required: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'blur'): void
  (event: 'focus'): void
}>()

const generatedId = useId()
const inputId = computed(() => props.id || `input-${generatedId}`)
const actualType = ref<'text' | 'password' | 'email' | 'tel' | 'search'>(props.type)
const isPassword = computed(() => props.type === 'password')
const shownPassword = ref(false)

function togglePassword(): void {
  if (!isPassword.value) return
  shownPassword.value = !shownPassword.value
  actualType.value = shownPassword.value ? 'text' : 'password'
}

function handleInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}

function handleBlur(): void {
  emit('blur')
}

function handleFocus(): void {
  emit('focus')
}
</script>

<template>
  <div class="app-input" :class="{ 'app-input--error': Boolean(error) }">
    <label v-if="label" class="app-input__label" :for="inputId">{{ label }}</label>
    <div class="app-input__control">
      <slot name="prefix" />
      <input
        :id="inputId"
        :name="name"
        :type="actualType"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :maxlength="maxlength"
        :disabled="disabled"
        :required="required"
        :inputmode="inputmode"
        :aria-invalid="Boolean(error) || undefined"
        :aria-describedby="error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined"
        class="app-input__element"
        @input="handleInput"
        @blur="handleBlur"
        @focus="handleFocus"
      />
      <button
        v-if="isPassword"
        type="button"
        class="app-input__toggle"
        :aria-label="shownPassword ? '隐藏密码' : '显示密码'"
        @click="togglePassword"
      >
        <EyeOff v-if="shownPassword" :size="16" :stroke-width="1.8" />
        <Eye v-else :size="16" :stroke-width="1.8" />
      </button>
    </div>
    <p v-if="error" :id="`${inputId}-error`" class="app-input__error">{{ error }}</p>
    <p v-else-if="hint" :id="`${inputId}-hint`" class="app-input__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.app-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.app-input__label {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--color-text);
}

.app-input__control {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 40px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out, background-color 160ms ease-out;
}

.app-input__control:hover {
  border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border-strong));
}

.app-input__control:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.app-input--error .app-input__control {
  border-color: var(--color-danger);
}

.app-input--error .app-input__control:focus-within {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-danger) 12%, transparent);
}

.app-input__element {
  width: 100%;
  min-width: 0;
  padding: 9px var(--sp-3);
  border: 0;
  border-radius: var(--radius-sm);
  outline: none;
  background: transparent;
  color: var(--color-text);
  font-size: var(--fs-base);
}

.app-input__element::placeholder {
  color: color-mix(in srgb, var(--color-text-muted) 68%, transparent);
}

.app-input__element:disabled {
  cursor: not-allowed;
  color: var(--color-text-muted);
}

.app-input__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-right: var(--sp-1);
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
}

.app-input__toggle:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.app-input__error {
  font-size: var(--fs-xs);
  color: var(--color-danger);
}

.app-input__hint {
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
}
</style>
