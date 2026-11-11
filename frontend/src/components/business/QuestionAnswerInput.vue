<!-- 作答控件：单选/多选/判断/填空四种题型，锁定态只读。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { Check, Plus, X } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import type { AttemptQuestion, QuestionOption } from '@/api/types'

const props = withDefaults(
  defineProps<{
    question: Pick<AttemptQuestion, 'id' | 'type' | 'stem' | 'options' | 'seq'>
    modelValue: unknown
    disabled?: boolean
    locked?: boolean
  }>(),
  {
    disabled: false,
    locked: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: unknown): void
  (event: 'blur', value: unknown): void
}>()

const options = computed<QuestionOption[]>(() => props.question.options ?? [])

const singleValue = computed(() => String(props.modelValue ?? ''))
const multipleValue = computed(() =>
  Array.isArray(props.modelValue) ? props.modelValue.map((item) => String(item)) : [],
)
const judgeValue = computed(() => {
  if (props.modelValue === true || props.modelValue === 'true') return true
  if (props.modelValue === false || props.modelValue === 'false') return false
  return null
})
const blankValue = computed(() => {
  if (Array.isArray(props.modelValue)) {
    return props.modelValue.length > 0 ? props.modelValue.map((item) => String(item ?? '')) : ['']
  }
  if (props.modelValue === null || props.modelValue === undefined) return ['']
  return [String(props.modelValue)]
})

function chooseSingle(key: string): void {
  if (props.locked || props.disabled) return
  emit('update:modelValue', key)
  emit('blur', key)
}

function toggleMultiple(key: string): void {
  if (props.locked || props.disabled) return
  const current = [...multipleValue.value]
  const index = current.indexOf(key)
  if (index >= 0) current.splice(index, 1)
  else current.push(key)
  current.sort()
  emit('update:modelValue', current)
  emit('blur', current)
}

function chooseJudge(value: boolean): void {
  if (props.locked || props.disabled) return
  emit('update:modelValue', value)
  emit('blur', value)
}

function setBlank(index: number, value: string): void {
  if (props.locked || props.disabled) return
  const next = [...blankValue.value]
  next[index] = value
  emit('update:modelValue', next)
}

function blurBlank(): void {
  emit('blur', blankValue.value)
}

function addBlank(): void {
  if (props.locked || props.disabled) return
  const next = [...blankValue.value, '']
  emit('update:modelValue', next)
}

function removeBlank(index: number): void {
  if (props.locked || props.disabled || blankValue.value.length <= 1) return
  const next = blankValue.value.filter((_item, idx) => idx !== index)
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="answer-input" :class="{ 'answer-input--locked': locked }">
    <div v-if="question.type === 'single'" class="choice-grid">
      <label
        v-for="option in options"
        :key="option.key"
        class="choice"
        :class="{ 'choice--active': singleValue === option.key }"
      >
        <input
          type="radio"
          class="visually-hidden"
          :name="`q-${question.id}`"
          :value="option.key"
          :checked="singleValue === option.key"
          :disabled="disabled || locked"
          @change="chooseSingle(option.key)"
        />
        <span class="choice__key">{{ option.key }}</span>
        <span class="choice__text">{{ option.text }}</span>
      </label>
    </div>

    <div v-else-if="question.type === 'multiple'" class="choice-grid">
      <label
        v-for="option in options"
        :key="option.key"
        class="choice"
        :class="{ 'choice--active': multipleValue.includes(option.key) }"
      >
        <input
          type="checkbox"
          class="visually-hidden"
          :value="option.key"
          :checked="multipleValue.includes(option.key)"
          :disabled="disabled || locked"
          @change="toggleMultiple(option.key)"
        />
        <span class="choice__key">{{ option.key }}</span>
        <span class="choice__text">{{ option.text }}</span>
        <Check v-if="multipleValue.includes(option.key)" class="choice__check" :size="15" :stroke-width="2" />
      </label>
    </div>

    <div v-else-if="question.type === 'judge'" class="judge-grid">
      <button
        class="judge"
        :class="{ 'judge--active': judgeValue === true }"
        type="button"
        :disabled="disabled || locked"
        @click="chooseJudge(true)"
      >
        <Check :size="17" :stroke-width="2" />
        正确
      </button>
      <button
        class="judge"
        :class="{ 'judge--active': judgeValue === false }"
        type="button"
        :disabled="disabled || locked"
        @click="chooseJudge(false)"
      >
        <X :size="17" :stroke-width="2" />
        错误
      </button>
    </div>

    <div v-else class="blank-list">
      <label v-for="(item, index) in blankValue" :key="index" class="blank-field">
        <span class="blank-field__label">{{ blankValue.length > 1 ? `第 ${index + 1} 空` : '答案' }}</span>
        <textarea
          class="blank-field__input"
          rows="2"
          :value="item"
          :disabled="disabled || locked"
          :placeholder="locked ? undefined : '输入你的答案'"
          @input="setBlank(index, ($event.target as HTMLTextAreaElement).value)"
          @blur="blurBlank"
        />
        <button
          v-if="blankValue.length > 1 && !locked"
          class="blank-field__remove"
          type="button"
          aria-label="删除这一空"
          @click="removeBlank(index)"
        >
          <X :size="13" :stroke-width="2" />
        </button>
      </label>

      <AppButton
        v-if="!locked && !disabled"
        variant="ghost"
        size="sm"
        @click="addBlank"
      >
        <Plus :size="14" :stroke-width="1.9" />
        添加一空
      </AppButton>
    </div>

    <p v-if="locked" class="answer-input__lock">试卷已锁定，答案不可修改</p>
  </div>
</template>

<style scoped>
.answer-input {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.choice-grid {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.choice {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  transition: border-color 160ms ease-out, background-color 160ms ease-out;
}

.choice:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-alt);
}

.choice--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.choice__key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: 999px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  background: var(--color-surface);
}

.choice--active .choice__key {
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
  background: var(--color-primary);
}

.choice__text {
  min-width: 0;
  font-size: var(--fs-base);
  line-height: 1.6;
}

.choice__check {
  margin-left: auto;
  flex-shrink: 0;
  color: var(--color-primary);
}

.judge-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.judge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  min-height: 48px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-weight: 600;
  transition: border-color 160ms ease-out, background-color 160ms ease-out, color 160ms ease-out;
}

.judge:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.judge--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.judge:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.blank-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.blank-field {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.blank-field__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.blank-field__input {
  width: 100%;
  min-height: 64px;
  padding: var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  resize: vertical;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-base);
  line-height: 1.6;
}

.blank-field__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.blank-field__input:disabled {
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
}

.blank-field__remove {
  position: absolute;
  top: 20px;
  right: var(--sp-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
}

.blank-field__remove:hover {
  color: var(--color-danger);
}

.answer-input__lock {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

@media (max-width: 560px) {
  .judge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
