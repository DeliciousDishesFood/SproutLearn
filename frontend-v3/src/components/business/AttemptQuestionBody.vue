<script setup lang="ts">
// 作答题目主体：原生 radio / checkbox（视觉隐藏但可聚焦），桌面与手机共用。
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import type { AttemptQuestion } from '@/api/contract'

const props = defineProps<{
  question: AttemptQuestion
  value: unknown
  disabled: boolean
}>()

const emit = defineEmits<{ (event: 'answer', value: unknown): void }>()

const isMultiple = computed(() => props.question.type === 'multiple')
const isJudge = computed(() => props.question.type === 'judge')
const options = computed(() => props.question.options ?? [])

const selectedCount = computed(() => {
  if (Array.isArray(props.value)) return props.value.length
  return props.value === undefined || props.value === null || props.value === '' ? 0 : 1
})

function chosen(key: string): boolean {
  if (isMultiple.value) {
    return Array.isArray(props.value) && props.value.map(String).includes(key)
  }
  return String(props.value ?? '') === key
}

function onOption(key: string, event: Event): void {
  const input = event.target as HTMLInputElement
  if (isMultiple.value) {
    const current = Array.isArray(props.value) ? (props.value as string[]).map(String) : []
    const next = input.checked ? [...current, key] : current.filter((item) => item !== key)
    emit('answer', next)
  } else {
    emit('answer', key)
  }
}

function judgeValue(flag: boolean): boolean {
  return props.value === flag
}

function onJudge(flag: boolean): void {
  emit('answer', flag)
}

function onBlank(event: Event): void {
  emit('answer', (event.target as HTMLTextAreaElement).value)
}
</script>

<template>
  <p class="q-stem">{{ question.stem }}</p>

  <p v-if="isMultiple" class="q-count">
    已选 {{ selectedCount }} 项
    <span class="q-count__hint">多选题，可选择多个答案</span>
  </p>

  <fieldset v-if="isJudge" class="q-options" :disabled="disabled">
    <legend class="sr-only">判断题选项</legend>
    <label class="option" :class="{ 'is-selected': judgeValue(true) }">
      <input
        class="option__native"
        type="radio"
        :name="`q-${question.id}`"
        :checked="judgeValue(true)"
        :disabled="disabled"
        @change="onJudge(true)"
      />
      <span class="option__key mono" aria-hidden="true">✓</span>
      <span class="option__text">正确</span>
      <span class="option__state" aria-hidden="true">
        <i v-if="judgeValue(true)" class="option__dot" />
        <i v-else class="option__ring" />
      </span>
    </label>
    <label class="option" :class="{ 'is-selected': judgeValue(false) }">
      <input
        class="option__native"
        type="radio"
        :name="`q-${question.id}`"
        :checked="judgeValue(false)"
        :disabled="disabled"
        @change="onJudge(false)"
      />
      <span class="option__key mono" aria-hidden="true">✕</span>
      <span class="option__text">错误</span>
      <span class="option__state" aria-hidden="true">
        <i v-if="judgeValue(false)" class="option__dot" />
        <i v-else class="option__ring" />
      </span>
    </label>
  </fieldset>

  <fieldset v-else-if="options.length" class="q-options" :disabled="disabled">
    <legend class="sr-only">{{ isMultiple ? '多选题选项，可多选' : '单选题选项' }}</legend>
    <label
      v-for="option in options"
      :key="option.key"
      class="option"
      :class="{ 'is-selected': chosen(option.key), 'is-multiple': isMultiple }"
    >
      <input
        class="option__native"
        :type="isMultiple ? 'checkbox' : 'radio'"
        :name="`q-${question.id}`"
        :value="option.key"
        :checked="chosen(option.key)"
        :disabled="disabled"
        @change="onOption(option.key, $event)"
      />
      <span class="option__key mono" aria-hidden="true">{{ option.key }}</span>
      <span class="option__text">{{ option.text }}</span>
      <span class="option__state" aria-hidden="true">
        <Check v-if="chosen(option.key) && isMultiple" :size="12" :stroke-width="3" />
        <i v-else-if="chosen(option.key)" class="option__dot" />
        <i v-else class="option__ring" />
      </span>
    </label>
  </fieldset>

  <div v-else class="blank-input">
    <label class="field">
      <span>你的答案</span>
      <textarea
        :value="value === undefined ? '' : String(value)"
        class="input"
        rows="3"
        placeholder="在这里填写答案"
        :disabled="disabled"
        @input="onBlank"
      />
    </label>
  </div>
</template>

<style scoped>
/* 题干：比普通卡片标题更明确，长题干自然换行 */
.q-stem {
  margin: 0;
  max-width: 46em;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.62;
  letter-spacing: -0.01em;
  white-space: pre-wrap;
  word-break: break-word;
  text-wrap: pretty;
}

.q-count {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0 0;
  color: var(--lime-text);
  font-size: 12px;
  font-weight: 600;
}

.q-count::before {
  content: '';
  width: 14px;
  height: 2px;
  background: var(--lime);
}

.q-count__hint {
  color: var(--text-3);
  font-weight: 400;
}

/* 选项列表：取消外框，只用细分割线与留白组织 */
.q-options {
  display: block;
  margin: 18px 0 0;
  padding: 0;
  border: 0;
  border-bottom: 1px solid var(--line-cool, var(--line));
  min-width: 0;
}

.option {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 18px;
  align-items: start;
  gap: 14px;
  width: 100%;
  padding: 18px 14px;
  border: 0;
  border-top: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  color: var(--text);
  font-size: 14.5px;
  line-height: 1.65;
  text-align: left;
  cursor: pointer;
  transition:
    background 140ms ease,
    color 140ms ease;
}

.option:hover {
  background: var(--surface-cool, var(--surface-alt));
  border-color: var(--line);
}

.option.is-selected {
  background: var(--option-selected-bg);
  border-color: var(--option-selected-line);
  box-shadow: none;
  color: var(--option-selected-ink);
}

.option.is-selected:hover {
  background: var(--option-selected-bg);
}

/* 键盘焦点：深墨轮廓 + 青柠外环；鼠标点击不残留 */
.option:has(.option__native:focus-visible) {
  outline: 2px solid var(--text);
  outline-offset: 2px;
  box-shadow: var(--focus-halo);
  z-index: 1;
}

.option.is-selected:has(.option__native:focus-visible) {
  outline-color: var(--lime-hi);
}

.option__native {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* 字母标记：等宽、带右侧细线，像曲目序号一样精确 */
.option__key {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 24px;
  border: 0;
  border-right: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.option.is-selected .option__key {
  border-right-color: var(--option-selected-line);
  background: transparent;
  color: var(--lime);
}

.option__text {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.option.is-selected .option__text {
  color: var(--option-selected-ink);
}

.option__state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  color: var(--lime-ink);
}

.option__ring,
.option__dot {
  display: block;
  width: 14px;
  height: 14px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  transition:
    border-color 140ms ease,
    background 140ms ease;
}

.option__dot {
  border-color: var(--lime);
  background: var(--lime);
  box-shadow: inset 0 0 0 3px var(--option-selected-bg);
}

/* 多选使用方形状态形状，与单选区分 */
.option.is-multiple .option__ring,
.option.is-multiple .option__dot {
  border-radius: 4px;
}

.option.is-multiple.is-selected .option__state {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: var(--lime);
  color: var(--lime-ink);
}

.option.is-selected .option__ring {
  border-color: var(--option-selected-line);
}

/* 截止后仍能辨认正文，不只把整行降到极浅 */
.option:has(.option__native:disabled) {
  cursor: default;
}

.option:has(.option__native:disabled) .option__text {
  color: var(--muted);
}

.option.is-selected:has(.option__native:disabled) .option__text {
  color: var(--option-selected-ink);
  opacity: 0.85;
}

.blank-input {
  margin-top: 18px;
}

@media (max-width: 900px) {
  .q-stem {
    font-size: 17px;
    line-height: 1.6;
  }

  .q-options {
    margin-top: 14px;
  }

  .option {
    grid-template-columns: 26px minmax(0, 1fr) 18px;
    gap: 10px;
    min-height: 44px;
    padding: 16px 2px;
    font-size: 14px;
  }

  .option__key {
    width: 26px;
    font-size: 12px;
  }
}
</style>
