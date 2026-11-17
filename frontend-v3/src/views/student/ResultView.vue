<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { attemptsApi } from '@/api/attempts'
import { questionsApi } from '@/api/questions'
import { isApiError, toUserMessage } from '@/api/client'
import type { AttemptAnswer, AttemptResult } from '@/api/contract'
import {
  ATTEMPT_STATUS_LABEL,
  attemptStatusTone,
  formatAnswer,
  formatDateTime,
  formatScore,
} from '@/utils/format'

type ResultFilter = 'all' | 'wrong' | 'review'

const route = useRoute()
const attemptId = computed(() => Number(route.params.attemptId))

const result = ref<AttemptResult | null>(null)
const loading = ref(true)
const errorText = ref('')
const blockedText = ref('')
const filter = ref<ResultFilter>('all')

const explainOpen = ref(false)
const explainLoading = ref(false)
const explainText = ref('')
const explainError = ref('')
const explainStem = ref('')
const explainAnswer = ref<AttemptAnswer | null>(null)
const explainEngine = ref('')
const explainDegraded = ref(false)

const answers = computed(() => result.value?.answers ?? [])
const correctCount = computed(() => answers.value.filter((answer) => answer.is_correct).length)
const pendingCount = computed(() => answers.value.filter((answer) => answer.needs_review).length)
const wrongCount = computed(
  () => answers.value.filter((answer) => !answer.needs_review && !answer.is_correct).length,
)

const filterOptions = computed(() => [
  { key: 'all' as const, label: '全部', count: answers.value.length },
  { key: 'wrong' as const, label: '错题', count: wrongCount.value },
  { key: 'review' as const, label: '待复核', count: pendingCount.value },
])

const filteredAnswers = computed(() => {
  if (filter.value === 'wrong') {
    return answers.value.filter((answer) => !answer.needs_review && !answer.is_correct)
  }
  if (filter.value === 'review') {
    return answers.value.filter((answer) => answer.needs_review)
  }
  return answers.value
})

const explainEngineLabel = computed(() => {
  if (explainDegraded.value) return '降级内容'
  if (explainEngine.value === 'template') return '模板讲评'
  if (explainEngine.value === 'llm') return 'AI 生成'
  return ''
})

const explainTone = computed(() =>
  explainEngineLabel.value && explainEngine.value === 'llm' && !explainDegraded.value
    ? 'lime'
    : 'amber',
)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  blockedText.value = ''
  try {
    result.value = await attemptsApi.result(attemptId.value)
  } catch (error) {
    if (isApiError(error) && error.code === 40910) {
      blockedText.value = '本次作答尚未提交，不能查看结果。请先完成作答并提交。'
    } else {
      errorText.value = toUserMessage(error)
    }
  } finally {
    loading.value = false
  }
}

async function explain(answer: AttemptAnswer): Promise<void> {
  explainOpen.value = true
  explainLoading.value = true
  explainText.value = ''
  explainError.value = ''
  explainEngine.value = ''
  explainDegraded.value = false
  explainStem.value = answer.stem
  explainAnswer.value = answer
  try {
    const res = await questionsApi.explain(answer.question_id, answer.raw_answer)
    explainText.value = res.explanation ?? res.content ?? '暂无讲评内容。'
    explainEngine.value = res.engine ?? ''
    explainDegraded.value = res.degraded === true
  } catch (error) {
    explainError.value = toUserMessage(error)
  } finally {
    explainLoading.value = false
  }
}

/** 讲评失败原地重试：不离开结果页、不清空题目与答案上下文。 */
async function regenerate(): Promise<void> {
  if (explainAnswer.value) await explain(explainAnswer.value)
}

function answerText(answer: AttemptAnswer): string {
  return formatAnswer(answer.raw_answer, answer.type)
}

/** 清理模型偶发返回的 Markdown 记号，保持纯文本渲染，不引入 v-html。 */
function cleanPlainText(text: string): string {
  return text
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*|__|`/g, '')
    .replace(/^\s*[-*•]\s+/gm, '• ')
    .trim()
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink to="/student/papers">试卷</RouterLink> · 作答结果
      </p>
      <h1>{{ result?.paper.title ?? '作答结果' }}</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student/papers">返回试卷</RouterLink>
      <RouterLink class="btn btn--primary" to="/student/growth">看成长</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="blockedText" class="notice notice--warn">
    {{ blockedText }}
    <RouterLink class="card__link" :to="`/student/attempts/${attemptId}`" style="margin-left: 8px">
      继续作答
    </RouterLink>
  </p>
  <p v-if="loading" class="loading-line">正在读取结果…</p>

  <template v-else-if="result">
    <section class="result-hero">
      <div class="result-hero__main">
        <p class="result-hero__eyebrow">本次得分</p>
        <p class="result-hero__score">
          {{ formatScore(result.attempt.total_score) }}<small> / {{ formatScore(result.attempt.full_score) }}</small>
        </p>
        <p class="result-hero__state">
          <BaseBadge :tone="attemptStatusTone(result.attempt.status)">
            {{ ATTEMPT_STATUS_LABEL[result.attempt.status] }}
          </BaseBadge>
        </p>
      </div>
      <dl class="result-metrics">
        <div class="result-metrics__item">
          <dt>正确</dt>
          <dd>{{ correctCount }} / {{ answers.length }}</dd>
        </div>
        <div class="result-metrics__item">
          <dt>待复核</dt>
          <dd>{{ pendingCount }}</dd>
        </div>
        <div v-if="result.attempt.late" class="result-metrics__item">
          <dt>提交</dt>
          <dd>迟交</dd>
        </div>
      </dl>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>逐题结果</h2>
        <span class="card__meta">共 {{ answers.length }} 题</span>
      </header>

      <div class="result-filter" role="group" aria-label="按作答结果筛选">
        <BaseButton
          v-for="option in filterOptions"
          :key="option.key"
          size="sm"
          :variant="filter === option.key ? 'primary' : 'secondary'"
          :aria-pressed="filter === option.key"
          @click="filter = option.key"
        >
          {{ option.label }} {{ option.count }}
        </BaseButton>
        <span class="result-filter__hint">当前显示 {{ filteredAnswers.length }} 题</span>
      </div>

      <EmptyState
        v-if="filteredAnswers.length === 0"
        title="当前筛选下没有题目"
        action-label="查看全部"
        @action="filter = 'all'"
      />

      <template v-else>
        <article v-for="answer in filteredAnswers" :key="answer.question_id" class="answer-item">
        <div class="answer-item__head">
          <div style="min-width: 0">
            <div class="row row--wrap" style="margin-bottom: 4px">
              <span class="q-index">第 {{ answer.seq }} 题</span>
              <BaseBadge v-if="answer.needs_review" tone="amber">待老师复核</BaseBadge>
              <BaseBadge v-else-if="answer.is_correct" tone="lime">正确</BaseBadge>
              <BaseBadge v-else tone="danger">错误</BaseBadge>
              <span class="small text-3">{{ answer.knowledge_tag }} · 满分 {{ formatScore(answer.full_score) }}</span>
            </div>
            <p class="answer-item__stem">{{ answer.stem }}</p>
          </div>
          <div class="answer-item__score">
            <span class="strong num">{{ formatScore(answer.score) }} 分</span>
            <span v-if="answer.needs_review" class="answer-item__adjust">分数可能调整</span>
          </div>
        </div>

        <div class="answer-grid">
          <div><span>你的答案</span><b>{{ answerText(answer) }}</b></div>
          <div><span>标准答案</span><b>{{ formatAnswer(answer.standard_answer, answer.type) }}</b></div>
        </div>

        <div v-if="answer.analysis" class="analysis-block">{{ answer.analysis }}</div>

        <div class="row" style="margin-top: 8px">
          <BaseButton
            size="sm"
            :variant="answer.is_correct && !answer.needs_review ? 'ghost' : 'primary'"
            @click="explain(answer)"
          >
            看讲评
          </BaseButton>
        </div>
      </article>
      </template>
    </section>

    <section v-if="result.reviews.length" class="card">
      <header class="card__head"><h2>老师复核记录</h2></header>
      <div class="stack" style="margin-top: 10px">
        <div v-for="review in result.reviews" :key="review.id" class="notice">
          <div class="row row--between row--wrap">
            <span>
              得分 {{ formatScore(review.old_score) }} → <b>{{ formatScore(review.new_score) }}</b>
            </span>
            <span class="small text-3">{{ formatDateTime(review.created_at) }}</span>
          </div>
          <p v-if="review.comment" class="small muted" style="margin-top: 4px">{{ review.comment }}</p>
          <details class="tech-details">
            <summary>技术详情</summary>
            <span>题目记录 #{{ review.answer_record_id }} · 复核记录 #{{ review.id }}</span>
          </details>
        </div>
      </div>
    </section>
  </template>

  <BaseModal :open="explainOpen" title="题目讲评" wide @close="explainOpen = false">
    <p class="small muted" style="margin-bottom: 10px">{{ explainStem }}</p>
    <div v-if="explainAnswer" class="answer-grid" style="margin-bottom: 12px">
      <div><span>你的答案</span><b>{{ answerText(explainAnswer) }}</b></div>
      <div><span>标准答案</span><b>{{ formatAnswer(explainAnswer.standard_answer, explainAnswer.type) }}</b></div>
    </div>

    <section v-if="explainAnswer?.analysis" class="explain-section">
      <h3 class="explain-section__title">官方解析</h3>
      <p class="explain-section__body">{{ cleanPlainText(explainAnswer.analysis) }}</p>
    </section>

    <section class="explain-section">
      <h3 class="explain-section__title">
        AI 讲评
        <BaseBadge v-if="explainEngineLabel" :tone="explainTone">{{ explainEngineLabel }}</BaseBadge>
      </h3>
      <p class="explain-section__note">由 AI 生成，仅供学习参考。</p>

      <p v-if="explainLoading" class="loading-line">正在生成讲评…</p>
      <template v-else-if="explainError">
        <p class="notice notice--danger">{{ explainError }}</p>
        <p class="small text-3" style="margin-top: 6px">
          题目与你的答案已保留，可直接重新生成，不会新建作答记录。
        </p>
      </template>
      <p v-else class="explain-section__body">{{ cleanPlainText(explainText) }}</p>
    </section>

    <template #footer>
      <BaseButton @click="explainOpen = false">关闭</BaseButton>
      <BaseButton
        v-if="explainError"
        variant="primary"
        :loading="explainLoading"
        @click="regenerate"
      >
        重新生成
      </BaseButton>
    </template>
  </BaseModal>
</template>
