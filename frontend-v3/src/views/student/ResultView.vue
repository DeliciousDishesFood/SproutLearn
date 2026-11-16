<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
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

const route = useRoute()
const attemptId = computed(() => Number(route.params.attemptId))

const result = ref<AttemptResult | null>(null)
const loading = ref(true)
const errorText = ref('')
const blockedText = ref('')

const explainOpen = ref(false)
const explainLoading = ref(false)
const explainText = ref('')
const explainError = ref('')
const explainStem = ref('')
const explainAnswer = ref<AttemptAnswer | null>(null)

const correctCount = computed(
  () => result.value?.answers.filter((answer) => answer.is_correct).length ?? 0,
)
const pendingCount = computed(
  () => result.value?.answers.filter((answer) => answer.needs_review).length ?? 0,
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
  explainStem.value = answer.stem
  explainAnswer.value = answer
  try {
    const res = await questionsApi.explain(answer.question_id, answer.raw_answer)
    explainText.value = res.explanation ?? res.content ?? '暂无讲评内容。'
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
      <div>
        <p class="eyebrow">SCORE</p>
        <p class="result-hero__score">
          {{ formatScore(result.attempt.total_score) }}<small> / {{ formatScore(result.attempt.full_score) }}</small>
        </p>
      </div>
      <div class="kv">
        <span>状态：<BaseBadge :tone="attemptStatusTone(result.attempt.status)">{{ ATTEMPT_STATUS_LABEL[result.attempt.status] }}</BaseBadge></span>
        <span>正确：<b>{{ correctCount }} / {{ result.answers.length }}</b></span>
        <span v-if="pendingCount > 0">待老师复核：<b>{{ pendingCount }} 题</b></span>
        <span v-if="result.attempt.late">迟交：<b>是</b></span>
      </div>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>逐题结果</h2>
        <span class="card__meta">共 {{ result.answers.length }} 题</span>
      </header>

      <article v-for="answer in result.answers" :key="answer.question_id" class="answer-item">
        <div class="answer-item__head">
          <div style="min-width: 0">
            <div class="row row--wrap" style="margin-bottom: 4px">
              <span class="q-index">第 {{ answer.seq }} 题</span>
              <BaseBadge v-if="answer.needs_review" tone="amber">待老师复核</BaseBadge>
              <BaseBadge v-else-if="answer.is_correct" tone="lime">正确</BaseBadge>
              <BaseBadge v-else tone="danger">错误</BaseBadge>
              <span class="small tertiary">{{ answer.knowledge_tag }} · 满分 {{ formatScore(answer.full_score) }}</span>
            </div>
            <p class="answer-item__stem">{{ answer.stem }}</p>
          </div>
          <span class="strong num" style="white-space: nowrap">{{ formatScore(answer.score) }} 分</span>
        </div>

        <div class="answer-grid">
          <div><span>你的答案</span><b>{{ answerText(answer) }}</b></div>
          <div><span>标准答案</span><b>{{ formatAnswer(answer.standard_answer, answer.type) }}</b></div>
        </div>

        <div v-if="answer.analysis" class="analysis-block">{{ answer.analysis }}</div>

        <div class="row" style="margin-top: 8px">
          <BaseButton size="sm" @click="explain(answer)">看讲评</BaseButton>
        </div>
      </article>
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
    <div v-if="explainAnswer" class="answer-grid" style="margin-bottom: 10px">
      <div><span>你的答案</span><b>{{ answerText(explainAnswer) }}</b></div>
      <div><span>标准答案</span><b>{{ formatAnswer(explainAnswer.standard_answer, explainAnswer.type) }}</b></div>
    </div>
    <p v-if="explainLoading" class="loading-line">正在生成讲评…</p>
    <template v-else-if="explainError">
      <p class="notice notice--danger">{{ explainError }}</p>
      <p class="small text-3" style="margin-top: 6px">
        题目与你的答案已保留，可直接重新生成，不会新建作答记录。
      </p>
    </template>
    <p v-else class="notice" style="white-space: pre-wrap; line-height: 1.75">{{ explainText }}</p>
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
