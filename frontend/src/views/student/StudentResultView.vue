<!-- 学生成绩：总分、逐题正误/解析、待复核不显示确定分数、讲评入口。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import QuestionExplainModal from '@/components/business/QuestionExplainModal.vue'
import { attemptsApi } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'
import {
  ATTEMPT_STATUS_META,
  BLANK_MODE_META,
  DIFFICULTY_META,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import { formatAnswer, formatScore, isAnswerEmpty } from '@/utils/questions'
import type { AttemptAnswer, AttemptResult, AttemptReview } from '@/api/types'

const route = useRoute()
const router = useRouter()

const attemptId = Number(route.params.id)
const result = ref<AttemptResult | null>(null)
const loading = ref(true)
const error = ref('')
const explainOpen = ref(false)
const explainTarget = ref<AttemptAnswer | null>(null)

const answers = computed<AttemptAnswer[]>(() => result.value?.answers ?? [])
const attemptsMeta = computed(() => {
  const attempt = result.value?.attempt
  return attempt ? ATTEMPT_STATUS_META[attempt.status] : null
})
const blankMeta = computed(() =>
  result.value ? BLANK_MODE_META[result.value.paper.blank_mode] : null,
)

function reviewsByRecord(): Map<number, AttemptReview[]> {
  const map = new Map<number, AttemptReview[]>()
  for (const review of result.value?.reviews ?? []) {
    const list = map.get(review.answer_record_id) ?? []
    list.push(review)
    map.set(review.answer_record_id, list)
  }
  return map
}

const reviewMap = computed(reviewsByRecord)
const pendingAnswers = computed(() => answers.value.filter((answer) => answer.needs_review))
const answeredAnswers = computed(() =>
  answers.value.filter(
    (answer) => answer.answer_record_id !== null && !isAnswerEmpty(answer.type, answer.raw_answer),
  ),
)
const correctAnswers = computed(
  () => answers.value.filter((answer) => !answer.needs_review && answer.is_correct).length,
)
const wrongAnswers = computed(
  () =>
    answers.value.filter(
      (answer) => !answer.needs_review && !answer.is_correct && answer.answer_record_id !== null,
    ).length,
)
const needsReview = computed(
  () => Boolean(result.value?.attempt.needs_review) || pendingAnswers.value.length > 0,
)
const scorePercent = computed(() => {
  const attempt = result.value?.attempt
  if (!attempt || attempt.full_score <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((attempt.total_score / attempt.full_score) * 100)))
})

function answerText(answer: AttemptAnswer): string {
  return formatAnswer(answer.raw_answer, answer.type, answer.options)
}

function standardText(answer: AttemptAnswer): string {
  return formatAnswer(answer.standard_answer, answer.type, answer.options)
}

function reviewsOf(answer: AttemptAnswer): AttemptReview[] {
  if (answer.answer_record_id === null) return []
  return reviewMap.value.get(answer.answer_record_id) ?? []
}

function reviewComment(review: AttemptReview): string {
  return review.comment?.trim() || ''
}

function openExplain(answer: AttemptAnswer): void {
  explainTarget.value = answer
  explainOpen.value = true
}

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权查看该次作答成绩'
  if (isApiError(err) && err.code === 40301) return '当前账号没有查看成绩的权限'
  if (isApiError(err) && err.code === 40401) return '成绩不存在或已被删除'
  return toUserMessage(err)
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  if (!Number.isFinite(attemptId) || attemptId <= 0) {
    error.value = '成绩地址无效'
    loading.value = false
    return
  }
  try {
    const data = await attemptsApi.result(attemptId)
    if (data.attempt.status === 'doing') {
      await router.replace({
        name: 'student-attempt',
        params: { id: String(attemptId) },
        query: { paper_id: String(data.attempt.paper_id) },
      })
      return
    }
    result.value = data
  } catch (err) {
    result.value = null
    error.value = mapError(err)
  } finally {
    loading.value = false
  }
}

function backToPapers(): void {
  void router.push('/student/papers')
}

onMounted(load)
</script>

<template>
  <div class="page result-page">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">MY RESULT</p>
        <h1 class="page-title">{{ result?.paper.title || '成绩单' }}</h1>
        <p class="page-subtitle">逐题查看判定、标准答案与解析；待复核题暂不显示确定分数。</p>
      </div>
      <div class="head-actions">
        <AppButton variant="ghost" @click="backToPapers">
          <ArrowLeft :size="15" :stroke-width="1.9" />
          返回试卷
        </AppButton>
        <AppButton variant="secondary" :loading="loading" @click="load">
          <RefreshCw v-if="!loading" :size="15" :stroke-width="1.8" />
          刷新成绩
        </AppButton>
      </div>
    </header>

    <section v-if="loading" class="content-stack" aria-busy="true">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="6" />
      </div>
    </section>

    <section v-else-if="error" class="panel">
      <AppEmpty error title="成绩暂时无法打开" :description="error">
        <template #action>
          <AppButton variant="secondary" @click="load">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <template v-else-if="result">
      <section class="score-hero panel panel-body">
        <div class="score-hero__info">
          <div class="score-hero__tags">
            <AppTag v-if="attemptsMeta" :tone="attemptsMeta.tone" dot>{{ attemptsMeta.label }}</AppTag>
            <AppTag tone="neutral">{{ blankMeta?.label }}</AppTag>
            <AppTag v-if="result.attempt.late" tone="danger">超时提交</AppTag>
            <AppTag v-if="needsReview" tone="accent" dot>待教师复核</AppTag>
          </div>

          <dl class="score-meta">
            <div>
              <dt>提交时间</dt>
              <dd>{{ formatDateTime(result.attempt.submitted_at) }}</dd>
            </div>
            <div>
              <dt>截止时间</dt>
              <dd>{{ formatDateTime(result.attempt.deadline_at) }}</dd>
            </div>
            <div>
              <dt>作答进度</dt>
              <dd class="tabular">{{ answeredAnswers.length }} / {{ answers.length }} 题</dd>
            </div>
          </dl>

          <p class="score-note">
            <AlertCircle v-if="needsReview" :size="14" :stroke-width="1.9" />
            <ShieldCheck v-else :size="14" :stroke-width="1.9" />
            {{
              needsReview
                ? `本卷有 ${pendingAnswers.length} 题低置信答案正在教师复核，复核完成前不显示确定总分与这些题的分数。`
                : '本卷已完成自动判分；如对分数有疑问，可联系任课教师复核。'
            }}
          </p>
        </div>

        <div class="score-hero__score" :class="{ 'score-hero__score--pending': needsReview }">
          <template v-if="needsReview">
            <span class="score-pending">复核中</span>
            <span class="score-denom">共 {{ result.attempt.full_score }} 分</span>
          </template>
          <template v-else>
            <strong class="score-value tabular">{{ formatScore(result.attempt.total_score) }}</strong>
            <span class="score-denom">/ {{ result.attempt.full_score }} 分</span>
            <span class="score-percent tabular">{{ scorePercent }}%</span>
          </template>
        </div>
      </section>

      <section v-if="needsReview" class="pending-banner" role="status">
        <Clock3 :size="18" :stroke-width="1.9" aria-hidden="true" />
        <div class="grow">
          <strong>教师复核中</strong>
          <p>
            第
            <template v-for="(answer, index) in pendingAnswers" :key="answer.question_id">
              {{ answer.seq }}<template v-if="index < pendingAnswers.length - 1">、</template>
            </template>
            题的作答已提交人工复核。复核完成后刷新本页，总分与逐题分数会同步更新。
          </p>
        </div>
      </section>

      <section class="summary-strip" aria-label="判分概览">
        <div class="summary-item">
          <span class="summary-item__value tabular">{{ answeredAnswers.length }}</span>
          <span class="summary-item__label">已作答</span>
        </div>
        <div class="summary-item summary-item--success">
          <span class="summary-item__value tabular">{{ correctAnswers }}</span>
          <span class="summary-item__label">判定正确</span>
        </div>
        <div class="summary-item summary-item--danger">
          <span class="summary-item__value tabular">{{ wrongAnswers }}</span>
          <span class="summary-item__label">判定错误</span>
        </div>
        <div class="summary-item summary-item--accent">
          <span class="summary-item__value tabular">{{ pendingAnswers.length }}</span>
          <span class="summary-item__label">待复核</span>
        </div>
        <div v-if="result.grading_ms !== null" class="summary-item">
          <span class="summary-item__value tabular">{{ result.grading_ms }}</span>
          <span class="summary-item__label">判分毫秒</span>
        </div>
      </section>

      <section class="answer-section">
        <header class="section-head">
          <div>
            <h2 class="section-title">逐题解析</h2>
            <p class="section-note">待复核题只显示“教师复核中”，不展示确定分数与正误结论。</p>
          </div>
          <AppTag tone="neutral">{{ answers.length }} 题</AppTag>
        </header>

        <AppEmpty
          v-if="answers.length === 0"
          title="这份试卷没有题目"
          description="试卷题目可能已被清空，请联系任课教师。"
        />

        <ol v-else class="answer-list">
          <li
            v-for="answer in answers"
            :key="answer.question_id"
            class="answer-card panel panel-body"
            :class="{ 'answer-card--pending': answer.needs_review }"
          >
            <header class="answer-card__head">
              <div class="answer-card__title">
                <span class="answer-seq tabular">第 {{ answer.seq }} 题</span>
                <AppTag :tone="QUESTION_TYPE_META[answer.type].tone">
                  {{ QUESTION_TYPE_META[answer.type].label }}
                </AppTag>
                <AppTag :tone="DIFFICULTY_META[answer.difficulty].tone">
                  {{ DIFFICULTY_META[answer.difficulty].label }}
                </AppTag>
                <AppTag tone="neutral">{{ answer.knowledge_tag }}</AppTag>
              </div>

              <div class="answer-verdict">
                <template v-if="answer.needs_review">
                  <AppTag tone="accent" dot>教师复核中</AppTag>
                  <span class="verdict-score verdict-score--pending">分数待定</span>
                </template>
                <template v-else-if="answer.answer_record_id === null || isAnswerEmpty(answer.type, answer.raw_answer)">
                  <AppTag tone="neutral" dot>未作答</AppTag>
                  <span class="verdict-score verdict-score--wrong">0 / {{ answer.full_score }} 分</span>
                </template>
                <template v-else>
                  <AppTag :tone="answer.is_correct ? 'success' : 'danger'" dot>
                    {{ answer.is_correct ? '正确' : '错误' }}
                  </AppTag>
                  <span
                    class="verdict-score tabular"
                    :class="answer.is_correct ? 'verdict-score--correct' : 'verdict-score--wrong'"
                  >
                    {{ formatScore(answer.score) }} / {{ answer.full_score }} 分
                  </span>
                </template>
              </div>
            </header>

            <p class="answer-stem">{{ answer.stem }}</p>

            <dl class="answer-compare">
              <div>
                <dt>
                  <CheckCircle2 :size="14" :stroke-width="1.9" aria-hidden="true" />
                  你的作答
                </dt>
                <dd>{{ answerText(answer) }}</dd>
              </div>
              <div>
                <dt>
                  <Sparkles :size="14" :stroke-width="1.9" aria-hidden="true" />
                  标准答案
                </dt>
                <dd>{{ standardText(answer) }}</dd>
              </div>
            </dl>

            <div v-if="answer.analysis" class="answer-analysis">
              <p class="answer-analysis__label">解析</p>
              <p>{{ answer.analysis }}</p>
            </div>

            <div v-if="reviewsOf(answer).length > 0" class="review-log">
              <p class="review-log__label">教师复核记录</p>
              <div v-for="review in reviewsOf(answer)" :key="review.id" class="review-log__item">
                <div class="review-log__head">
                  <strong class="tabular">{{ formatScore(review.new_score) }} 分</strong>
                  <span class="muted text-xs">{{ formatDateTime(review.created_at) }}</span>
                </div>
                <p v-if="reviewComment(review)" class="review-log__comment">{{ reviewComment(review) }}</p>
              </div>
            </div>

            <footer class="answer-card__foot">
              <AppTag v-if="answer.needs_review" tone="warning">最终分数以教师复核为准</AppTag>
              <span v-else class="muted text-xs">自动判分 · {{ answer.engine || 'rule' }}</span>
              <AppButton variant="ghost" size="sm" @click="openExplain(answer)">
                <Sparkles :size="14" :stroke-width="1.9" />
                题目讲评
              </AppButton>
            </footer>
          </li>
        </ol>
      </section>

      <p v-if="error" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ error }}</span>
      </p>
    </template>

    <QuestionExplainModal
      v-model="explainOpen"
      :question-id="explainTarget?.question_id ?? null"
      :question-stem="explainTarget?.stem"
      :student-answer="explainTarget?.raw_answer"
    />
  </div>
</template>

<style scoped>
.head-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.score-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-5);
  margin-bottom: var(--sp-4);
  background:
    linear-gradient(
      125deg,
      color-mix(in srgb, var(--color-primary-soft) 65%, var(--color-surface)),
      var(--color-surface) 70%);
  border-color: color-mix(in srgb, var(--color-primary) 24%, var(--color-border));
  flex-wrap: wrap;
}

.score-hero__info {
  min-width: 0;
  flex: 1 1 420px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.score-hero__tags {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.score-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
  flex-wrap: wrap;
}

.score-meta dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.score-meta dd {
  margin-top: 2px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.score-note {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  max-width: 620px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.65;
}

.score-note svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.score-hero__score {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 160px;
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.score-value {
  font-family: var(--font-mono);
  font-size: var(--fs-2xl);
  line-height: 1.1;
  color: var(--color-primary);
}

.score-denom {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.score-percent {
  margin-top: var(--sp-1);
  padding: 1px var(--sp-2);
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.score-hero__score--pending {
  border-style: dashed;
}

.score-pending {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--color-accent);
}

.pending-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  margin-bottom: var(--sp-4);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-accent) 30%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-accent) 8%, var(--color-surface));
  color: var(--color-accent);
}

.pending-banner p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.65;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-3);
  margin-bottom: var(--sp-5);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.summary-item__value {
  font-size: var(--fs-xl);
  font-weight: 700;
}

.summary-item__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.summary-item--success .summary-item__value {
  color: var(--color-success);
}

.summary-item--danger .summary-item__value {
  color: var(--color-danger);
}

.summary-item--accent .summary-item__value {
  color: var(--color-accent);
}

.answer-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.section-note {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.answer-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.answer-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.answer-card--pending {
  border-color: color-mix(in srgb, var(--color-accent) 38%, var(--color-border));
}

.answer-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.answer-card__title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.answer-seq {
  font-size: var(--fs-sm);
  font-weight: 700;
}

.answer-verdict {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.verdict-score {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.verdict-score--correct {
  color: var(--color-success);
}

.verdict-score--wrong {
  color: var(--color-danger);
}

.verdict-score--pending {
  color: var(--color-accent);
}

.answer-stem {
  font-size: var(--fs-lg);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.answer-compare {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-3);
}

.answer-compare div {
  padding: var(--sp-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.answer-compare dt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.answer-compare dd {
  margin-top: var(--sp-1);
  font-size: var(--fs-sm);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.answer-analysis {
  padding: var(--sp-3);
  border-left: 2px solid var(--color-border-strong);
}

.answer-analysis__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.answer-analysis p {
  margin-top: 2px;
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.review-log {
  padding: var(--sp-3);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-success) 6%, var(--color-surface));
  border: 1px solid color-mix(in srgb, var(--color-success) 22%, transparent);
}

.review-log__label {
  color: var(--color-success);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.review-log__item {
  margin-top: var(--sp-2);
}

.review-log__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.review-log__comment {
  margin-top: 2px;
  color: var(--color-text);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.answer-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  padding-top: var(--sp-3);
  border-top: 1px dashed var(--color-border);
}

@media (max-width: 720px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .answer-compare {
    grid-template-columns: 1fr;
  }

  .score-hero {
    align-items: flex-start;
  }

  .score-hero__score {
    width: 100%;
  }
}
</style>
