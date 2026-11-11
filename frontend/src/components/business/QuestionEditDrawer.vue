<!-- 题目编辑抽屉：四种题型的选项与答案编辑器，保存走 PATCH /questions/{id}。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertCircle, Plus, X } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppDrawer from '@/components/base/AppDrawer.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppTag from '@/components/base/AppTag.vue'
import { questionsApi } from '@/api/questions'
import { toUserMessage } from '@/api/client'
import {
  DIFFICULTY_META,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import type {
  QuestionDifficulty,
  QuestionItem,
  QuestionOption,
  QuestionType,
} from '@/api/types'
import type { SelectOption } from '@/types'

const props = defineProps<{
  modelValue: boolean
  question: QuestionItem | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved', question: QuestionItem): void
}>()

const typeOptions: SelectOption[] = (Object.keys(QUESTION_TYPE_META) as QuestionType[]).map((value) => ({
  value,
  label: QUESTION_TYPE_META[value].label,
}))
const difficultyOptions: SelectOption[] = (
  Object.keys(DIFFICULTY_META) as QuestionDifficulty[]
).map((value) => ({ value, label: DIFFICULTY_META[value].label }))

const type = ref<QuestionType>('single')
const stem = ref('')
const knowledgeTag = ref('')
const difficulty = ref<QuestionDifficulty>('medium')
const analysis = ref('')
const options = ref<QuestionOption[]>([])
const singleAnswer = ref('')
const multipleAnswer = ref<string[]>([])
const judgeAnswer = ref<'true' | 'false' | ''>('')
const blankAnswers = ref<string[]>([''])
const saving = ref(false)
const error = ref('')

const isChoice = computed(() => type.value === 'single' || type.value === 'multiple')
const letterOptions = computed(() => options.value.filter((item) => item.key.trim()))
const canSave = computed(() => {
  if (stem.value.trim() === '') return false
  if (isChoice.value && letterOptions.value.length < 2) return false
  return true
})

function nextKey(): string {
  const used = new Set(options.value.map((item) => item.key.toUpperCase()))
  for (let index = 0; index < 26; index += 1) {
    const key = String.fromCharCode(65 + index)
    if (!used.has(key)) return key
  }
  return ''
}

function addOption(): void {
  const key = nextKey()
  if (!key) return
  options.value.push({ key, text: '' })
}

function removeOption(index: number): void {
  options.value.splice(index, 1)
}

function syncMultipleFromAnswer(answer: unknown): void {
  if (Array.isArray(answer)) {
    multipleAnswer.value = answer.map((item) => String(item))
  } else if (answer !== null && answer !== undefined && String(answer) !== '') {
    multipleAnswer.value = [String(answer)]
  } else {
    multipleAnswer.value = []
  }
}

function reset(): void {
  const source = props.question
  type.value = source?.type ?? 'single'
  stem.value = source?.stem ?? ''
  knowledgeTag.value = source?.knowledge_tag ?? ''
  difficulty.value = source?.difficulty ?? 'medium'
  analysis.value = source?.analysis ?? ''
  options.value = (source?.options ?? []).map((item) => ({ key: item.key, text: item.text }))
  singleAnswer.value = ''
  multipleAnswer.value = []
  judgeAnswer.value = ''
  blankAnswers.value = ['']
  if (source) {
    if (source.type === 'single') singleAnswer.value = String(source.answer ?? '')
    if (source.type === 'multiple') syncMultipleFromAnswer(source.answer)
    if (source.type === 'judge') {
      judgeAnswer.value = source.answer === true ? 'true' : source.answer === false ? 'false' : ''
    }
    if (source.type === 'blank') {
      blankAnswers.value =
        Array.isArray(source.answer) && source.answer.length > 0
          ? source.answer.map((item) => String(item))
          : ['']
    }
  }
  if (isChoice.value && options.value.length === 0) {
    options.value = [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
    ]
  }
  saving.value = false
  error.value = ''
}

watch(
  () => [props.modelValue, props.question] as const,
  ([open]) => {
    if (open) reset()
  },
  { immediate: true },
)

function handleTypeChange(): void {
  singleAnswer.value = ''
  multipleAnswer.value = []
  judgeAnswer.value = ''
  blankAnswers.value = ['']
  error.value = ''
  if (isChoice.value && options.value.length === 0) {
    options.value = [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
    ]
  }
}

function toggleMultiple(key: string): void {
  const index = multipleAnswer.value.indexOf(key)
  if (index >= 0) multipleAnswer.value.splice(index, 1)
  else multipleAnswer.value.push(key)
  multipleAnswer.value.sort()
}

function addBlank(): void {
  blankAnswers.value.push('')
}

function removeBlank(index: number): void {
  if (blankAnswers.value.length <= 1) return
  blankAnswers.value.splice(index, 1)
}

function buildAnswer(): { answer: unknown; message: string } {
  if (type.value === 'single') {
    if (!singleAnswer.value) return { answer: null, message: '请选择单选题标准答案' }
    if (!letterOptions.value.some((item) => item.key === singleAnswer.value)) {
      return { answer: null, message: '标准答案必须来自当前选项' }
    }
    return { answer: singleAnswer.value, message: '' }
  }
  if (type.value === 'multiple') {
    if (multipleAnswer.value.length === 0) return { answer: null, message: '请选择多选题标准答案' }
    const keys = new Set(letterOptions.value.map((item) => item.key))
    if (multipleAnswer.value.some((item) => !keys.has(item))) {
      return { answer: null, message: '标准答案包含已删除的选项' }
    }
    return { answer: [...multipleAnswer.value].sort(), message: '' }
  }
  if (type.value === 'judge') {
    if (judgeAnswer.value === '') return { answer: null, message: '请选择判断题答案' }
    return { answer: judgeAnswer.value === 'true', message: '' }
  }
  const values = blankAnswers.value.map((item) => item.trim()).filter(Boolean)
  if (values.length === 0) return { answer: null, message: '请填写至少一个填空答案' }
  return { answer: values, message: '' }
}

async function save(): Promise<void> {
  if (!props.question || saving.value) return
  if (!canSave.value) {
    error.value = '请完整填写题干、选项与标准答案'
    return
  }
  if (isChoice.value) {
    const seen = new Set<string>()
    for (const item of letterOptions.value) {
      const key = item.key.toUpperCase()
      if (key.length !== 1 || !/^[A-Z]$/.test(key)) {
        error.value = '选项编号必须是单个字母 A-Z'
        return
      }
      if (seen.has(key)) {
        error.value = '选项编号不能重复'
        return
      }
      if (!item.text.trim()) {
        error.value = `选项 ${key} 的内容不能为空`
        return
      }
      seen.add(key)
    }
  }
  const answerResult = buildAnswer()
  if (answerResult.message) {
    error.value = answerResult.message
    return
  }

  saving.value = true
  error.value = ''
  try {
    const payload = {
      type: type.value,
      stem: stem.value.trim(),
      options: isChoice.value
        ? letterOptions.value.map((item) => ({ key: item.key.toUpperCase(), text: item.text.trim() }))
        : null,
      answer: answerResult.answer,
      analysis: analysis.value.trim() === '' ? null : analysis.value.trim(),
      knowledge_tag: knowledgeTag.value.trim() || '未分类',
      difficulty: difficulty.value,
    }
    const updated = await questionsApi.update(props.question.id, payload)
    emit('saved', updated)
    emit('update:modelValue', false)
  } catch (err) {
    error.value = toUserMessage(err)
  } finally {
    saving.value = false
  }
}

function close(): void {
  if (saving.value) return
  emit('update:modelValue', false)
}
</script>

<template>
  <AppDrawer
    :model-value="modelValue"
    title="编辑题目"
    description="修改后立即生效；已发布试卷引用的题目仅可调整解析。"
    width="640px"
    :prevent-close="saving"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form class="question-form" @submit.prevent="save">
      <div class="form-grid">
        <AppSelect
          v-model="type"
          label="题型"
          :options="typeOptions"
          :disabled="saving"
          @change="handleTypeChange"
        />
        <AppSelect v-model="difficulty" label="难度" :options="difficultyOptions" :disabled="saving" />
      </div>

      <label class="field">
        <span class="field__label">题干</span>
        <textarea
          v-model="stem"
          class="field__textarea"
          rows="3"
          placeholder="请输入题目内容"
          :disabled="saving"
        />
      </label>

      <label class="field">
        <span class="field__label">知识点标签</span>
        <input v-model="knowledgeTag" class="field__input" type="text" placeholder="如：传输层" :disabled="saving" />
      </label>

      <section v-if="isChoice" class="field">
        <div class="field__head">
          <span class="field__label">选项</span>
          <AppButton variant="ghost" size="sm" :disabled="saving" @click="addOption">
            <Plus :size="14" :stroke-width="1.9" />
            添加选项
          </AppButton>
        </div>
        <div class="option-list">
          <div v-for="(option, index) in options" :key="index" class="option-row">
            <input
              v-model="option.key"
              class="option-row__key mono"
              type="text"
              maxlength="1"
              :aria-label="`选项 ${index + 1} 编号`"
              :disabled="saving"
            />
            <input
              v-model="option.text"
              class="option-row__text"
              type="text"
              :placeholder="`选项 ${option.key || index + 1} 内容`"
              :disabled="saving"
            />
            <button
              class="option-row__remove"
              type="button"
              :aria-label="`删除选项 ${option.key}`"
              :disabled="saving || options.length <= 2"
              @click="removeOption(index)"
            >
              <X :size="14" :stroke-width="2" />
            </button>
          </div>
        </div>
      </section>

      <section class="field">
        <span class="field__label">标准答案</span>

        <div v-if="type === 'single'" class="answer-options">
          <button
            v-for="option in letterOptions"
            :key="option.key"
            class="answer-key"
            :class="{ 'answer-key--active': singleAnswer === option.key }"
            type="button"
            :disabled="saving"
            @click="singleAnswer = option.key"
          >
            {{ option.key }}
          </button>
        </div>

        <div v-else-if="type === 'multiple'" class="answer-options">
          <button
            v-for="option in letterOptions"
            :key="option.key"
            class="answer-key"
            :class="{ 'answer-key--active': multipleAnswer.includes(option.key) }"
            type="button"
            :disabled="saving"
            @click="toggleMultiple(option.key)"
          >
            {{ option.key }}
          </button>
        </div>

        <div v-else-if="type === 'judge'" class="judge-options">
          <button
            class="judge-option"
            :class="{ 'judge-option--active': judgeAnswer === 'true' }"
            type="button"
            :disabled="saving"
            @click="judgeAnswer = 'true'"
          >
            正确
          </button>
          <button
            class="judge-option"
            :class="{ 'judge-option--active': judgeAnswer === 'false' }"
            type="button"
            :disabled="saving"
            @click="judgeAnswer = 'false'"
          >
            错误
          </button>
        </div>

        <div v-else class="blank-answers">
          <div v-for="(item, index) in blankAnswers" :key="index" class="blank-answer">
            <span class="blank-answer__label">第 {{ index + 1 }} 空</span>
            <input
              :value="item"
              class="field__input"
              type="text"
              placeholder="标准答案"
              :disabled="saving"
              @input="blankAnswers[index] = ($event.target as HTMLInputElement).value"
            />
            <button
              class="option-row__remove"
              type="button"
              :aria-label="`删除第 ${index + 1} 空`"
              :disabled="saving || blankAnswers.length <= 1"
              @click="removeBlank(index)"
            >
              <X :size="14" :stroke-width="2" />
            </button>
          </div>
          <AppButton variant="ghost" size="sm" :disabled="saving" @click="addBlank">
            <Plus :size="14" :stroke-width="1.9" />
            添加一空
          </AppButton>
        </div>
      </section>

      <label class="field">
        <span class="field__label">解析（可选）</span>
        <textarea
          v-model="analysis"
          class="field__textarea"
          rows="3"
          placeholder="录入标准解析，便于学生复习与讲评"
          :disabled="saving"
        />
      </label>

      <p v-if="error" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ error }}</span>
      </p>

      <div class="form-meta">
        <AppTag tone="neutral">Q-{{ question?.id }}</AppTag>
        <AppTag :tone="question?.status === 'published' ? 'primary' : 'neutral'" dot>
          {{ question?.status === 'published' ? '已入卷' : '草稿' }}
        </AppTag>
      </div>

      <footer class="form-foot">
        <AppButton variant="ghost" :disabled="saving" @click="close">取消</AppButton>
        <AppButton variant="primary" type="submit" :loading="saving">保存修改</AppButton>
      </footer>
    </form>
  </AppDrawer>
</template>

<style scoped>
.question-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.field__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.field__label {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--color-text);
}

.field__input,
.field__textarea {
  width: 100%;
  min-height: 40px;
  padding: 9px var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-base);
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
}

.field__textarea {
  min-height: 84px;
  resize: vertical;
  line-height: 1.7;
}

.field__input:focus,
.field__textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.option-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.option-row {
  min-width: 0;
}

.option-row__key {
  width: 40px;
  min-height: 40px;
  padding: 9px 0;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface-alt);
  color: var(--color-primary);
  font-weight: 600;
  text-align: center;
  text-transform: uppercase;
}

.option-row__text {
  flex: 1;
  min-height: 40px;
  padding: 9px var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
}

.option-row__text:focus,
.option-row__key:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.option-row__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.option-row__remove:hover:not(:disabled) {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}

.option-row__remove:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.answer-options {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.answer-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  height: 38px;
  padding: 0 var(--sp-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-weight: 600;
}

.answer-key:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.answer-key--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.judge-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-2);
}

.judge-option {
  min-height: 40px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-weight: 600;
}

.judge-option--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.blank-answers {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.blank-answer {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.blank-answer__label {
  flex-shrink: 0;
  width: 48px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.blank-answer .field__input {
  flex: 1;
}

.form-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.form-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
}

@media (max-width: 560px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
