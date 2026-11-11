<!-- 教师复核抽屉：逐题查看作答、改分与备注，保存后即时刷新整卷状态。 -->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { AlertCircle, CheckCircle2, RefreshCw, ShieldCheck } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppDrawer from '@/components/base/AppDrawer.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { attemptsApi } from '@/api/attempts'
import { ATTEMPT_STATUS_META, QUESTION_TYPE_META } from '@/utils/constants'
import { formatAnswer } from '@/utils/questions'
import { formatDateTime } from '@/utils/format'
import type { AttemptAnswer, AttemptResult } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  attemptId: number | null
  studentName?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'reviewed', attemptId: number): void
}>()

interface DraftScore {
  score: string
  comment: string
}

const loading = ref(false)
const error = ref('')
const result = ref<AttemptResult | null>(null)
const drafts = reactive<Record<number, DraftScore>>({})
const rowErrors = reactive<Record<number, string>>({})
const savingId = ref<number | null>(null)

const answers = computed(() => result.value?.answers ?? [])
const pendingCount = computed(() => answers.value.filter((item) => item.needs_review).length)
const statusMeta = computed(() =>
  result.value ? ATTEMPT_STATUS_META[result.value.attempt.status] : null,
)
const attemptSummary = computed(() => result.value?.attempt ?? null)

function seedDrafts(answerList: AttemptAnswer[]): void {
  for (const key of Object.keys(drafts)) delete drafts[Number(key)]
  for (const key of Object.keys(rowErrors)) delete rowErrors[Number(key)]
  for (const answer of answerList) {
    if (answer.answer_record_id === null) continue
    drafts[answer.answer_record_id] = {
      score: String(answer.score),
      comment: '',
    }
  }
}

async function load(): Promise<void> {
  if (!props.attemptId) {
    result.value = null
    error.value = ''
    return
  }
  loading.value = true
  error.value = ''
  try {
    const data = await attemptsApi.result(props.attemptId)
    result.value = data
    seedDrafts(data.answers)
  } catch (err) {
    result.value = null
    error.value = toUserMessage(err)
    if (isApiError(err) && err.code === 40302) {
      error.value = '无权访问该班级资源'
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.attemptId] as const,
  ([open, attemptId]) => {
    if (open && attemptId !== null) void load()
    if (!open) {
      result.value = null
      error.value = ''
    }
  },
  { immediate: true },
)

function maxScore(answer: AttemptAnswer): number {
  return Number(answer.full_score ?? 0)
}

function draftOf(answer: AttemptAnswer): DraftScore {
  return drafts[answer.answer_record_id as number]
}

function rowErrorOf(answer: AttemptAnswer): string {
  return answer.answer_record_id === null ? '' : rowErrors[answer.answer_record_id] ?? ''
}

function close(): void {
  emit('update:modelValue', false)
}

async function save(answer: AttemptAnswer): Promise<void> {
  if (answer.answer_record_id === null || !props.attemptId) return
  const attemptId = props.attemptId
  const recordId = answer.answer_record_id
  const draft = drafts[recordId]
  if (!draft) return
  const score = Number(draft.score)
  if (!Number.isFinite(score)) {
    rowErrors[recordId] = '请输入数字分数'
    return
  }
  if (score < 0 || score > maxScore(answer)) {
    rowErrors[recordId] = `分数需在 0 到 ${maxScore(answer)} 之间`
    return
  }
  if (draft.comment.trim().length > 500) {
    rowErrors[recordId] = '备注不能超过 500 字'
    return
  }
  savingId.value = recordId
  rowErrors[recordId] = ''
  try {
    const updated = await attemptsApi.review(attemptId, {
      answer_record_id: recordId,
      new_score: Math.round(score * 100) / 100,
      comment: draft.comment.trim() || undefined,
    })
    result.value = updated
    seedDrafts(updated.answers)
    emit('reviewed', attemptId)
  } catch (err) {
    rowErrors[recordId] = toUserMessage(err)
  } finally {
    savingId.value = null
  }
}
</script>

<template>
  <AppDrawer
    :model-value="modelValue"
    title="作答复核"
    :description="studentName ? `${studentName} 的本次作答 · 逐题改分并附备注` : '逐题改分并附备注'"
    width="680px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="review">
      <div v-if="loading" class="review__loading" aria-busy="true">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="6" />
      </div>

      <AppEmpty
        v-else-if="error"
        error
        title="复核内容暂时无法加载"
        :description="error"
      >
        <template #action>
          <AppButton variant="secondary" :disabled="loading" @click="load">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>

      <template v-else-if="result && attemptSummary">
        <header class="review-summary">
          <div class="review-summary__score">
            <span class="review-summary__value tabular">{{ attemptSummary.total_score }}</span>
            <span class="review-summary__unit">/ {{ attemptSummary.full_score }} 分</span>
          </div>
          <dl class="review-summary__meta">
            <div>
              <dt>状态</dt>
              <dd>
                <AppTag v-if="statusMeta" :tone="statusMeta.tone" dot>{{ statusMeta.label }}</AppTag>
              </dd>
            </div>
            <div>
              <dt>待复核</dt>
              <dd class="tabular">{{ pendingCount }} 题</dd>
            </div>
            <div>
              <dt>提交时间</dt>
              <dd>{{ formatDateTime(attemptSummary.submitted_at) }}</dd>
            </div>
          </dl>
        </header>

        <section v-if="pendingCount === 0" class="review-done">
          <CheckCircle2 :size="18" :stroke-width="1.9" aria-hidden="true" />
          所有低置信题均已复核，学生端会显示确定分数。
        </section>

        <AppEmpty
          v-if="answers.length === 0"
          title="这份作答暂无题目"
          description="试卷可能已撤回或题目记录不存在。"
        />

        <article
          v-for="answer in answers"
          :key="answer.question_id"
          class="review-item"
          :class="{ 'review-item--pending': answer.needs_review }"
        >
          <header class="review-item__head">
            <span class="review-item__seq mono tabular">第 {{ answer.seq }} 题</span>
            <AppTag tone="neutral">{{ QUESTION_TYPE_META[answer.type]?.short || answer.type }}</AppTag>
            <AppTag v-if="answer.needs_review" tone="accent" dot>教师复核中</AppTag>
            <AppTag v-else tone="success" dot>自动判分</AppTag>
            <span class="spacer" />
            <span class="review-item__score tabular">
              {{ answer.score }} / {{ answer.full_score }} 分
            </span>
          </header>
          <p class="review-item__stem">{{ answer.stem }}</p>

          <dl class="review-item__answers">
            <div>
              <dt>学生作答</dt>
              <dd>{{ formatAnswer(answer.raw_answer, answer.type, answer.options) }}</dd>
            </div>
            <div>
              <dt>标准答案</dt>
              <dd>{{ formatAnswer(answer.standard_answer, answer.type, answer.options) }}</dd>
            </div>
          </dl>

          <p v-if="answer.answer_record_id === null" class="review-item__hint">
            该题未作答，没有可复核的答题记录。
          </p>

          <div v-else class="review-item__form">
            <label class="score-field">
              <span>新分数</span>
              <input
                v-model="draftOf(answer).score"
                class="score-field__input tabular"
                type="number"
                min="0"
                :max="maxScore(answer)"
                step="0.5"
                :disabled="savingId !== null"
              />
              <span class="score-field__max">/ {{ maxScore(answer) }}</span>
            </label>
            <input
              v-model="draftOf(answer).comment"
              class="review-comment"
              type="text"
              maxlength="500"
              placeholder="备注（可选，学生可见）"
              :disabled="savingId !== null"
            />
            <AppButton
              variant="secondary"
              size="sm"
              :loading="savingId === answer.answer_record_id"
              :disabled="savingId !== null"
              @click="save(answer)"
            >
              <ShieldCheck v-if="savingId !== answer.answer_record_id" :size="14" :stroke-width="1.9" />
              保存复核
            </AppButton>
          </div>

          <p v-if="rowErrorOf(answer)" class="review-item__error" role="alert">
            <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
            {{ rowErrorOf(answer) }}
          </p>
        </article>

        <footer class="review__foot">
          <span class="muted text-xs">
            <ShieldCheck :size="13" :stroke-width="1.8" />
            改分后会自动重算总分并更新学生成绩页
          </span>
          <AppButton variant="ghost" @click="close">关闭</AppButton>
        </footer>
      </template>

      <AppEmpty
        v-else
        title="请选择一份作答"
        description="在成绩表中点击“复核”后再查看逐题明细。"
      />
    </div>
  </AppDrawer>
</template>

<style scoped>
.review {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.review__loading {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.review-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  flex-wrap: wrap;
}

.review-summary__score {
  display: flex;
  align-items: baseline;
  gap: var(--sp-1);
}

.review-summary__value {
  color: var(--color-primary);
  font-size: var(--fs-2xl);
  font-weight: 700;
}

.review-summary__unit {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.review-summary__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  flex-wrap: wrap;
}

.review-summary__meta dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.review-summary__meta dd {
  margin-top: 2px;
  font-size: var(--fs-sm);
}

.review-done {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-success) 24%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-success) 7%, var(--color-surface));
  color: var(--color-success);
  font-size: var(--fs-sm);
}

.review-item {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.review-item--pending {
  border-color: color-mix(in srgb, var(--color-accent) 34%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 4%, var(--color-surface));
}

.review-item__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.review-item__seq {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.review-item__score {
  color: var(--color-text);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.review-item__stem {
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.review-item__answers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-2);
}

.review-item__answers dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.review-item__answers dd {
  margin-top: 2px;
  font-size: var(--fs-sm);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.review-item__answers > div:first-child dd {
  color: var(--color-text);
}

.review-item__answers > div:last-child dd {
  color: var(--color-success);
}

.review-item__hint {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.review-item__form {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
  padding-top: var(--sp-2);
  border-top: 1px dashed var(--color-border);
}

.score-field {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.score-field__input {
  width: 72px;
  height: 34px;
  padding: 0 var(--sp-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-sm);
}

.score-field__input:focus {
  border-color: var(--color-primary);
}

.score-field__max {
  color: var(--color-text-muted);
}

.review-comment {
  flex: 1;
  min-width: 160px;
  height: 34px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  outline: none;
  background: var(--color-surface);
  font-size: var(--fs-sm);
}

.review-comment:focus {
  border-color: var(--color-primary);
}

.review-item__error {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--color-danger);
  font-size: var(--fs-xs);
}

.review__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.review__foot .muted {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

@media (max-width: 560px) {
  .review-item__answers {
    grid-template-columns: 1fr;
  }
}
</style>
