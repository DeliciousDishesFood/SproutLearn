<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ReviewTable from '@/components/business/ReviewTable.vue'
import { attemptsApi } from '@/api/attempts'
import { toUserMessage } from '@/api/client'
import type { AttemptAnswer, AttemptResult } from '@/api/contract'
import { ATTEMPT_STATUS_LABEL, attemptStatusTone, formatAnswer, formatDateTime, formatScore } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const toast = useToast()
const attemptId = computed(() => Number(route.params.attemptId))

const result = ref<AttemptResult | null>(null)
const loading = ref(true)
const errorText = ref('')

const reviewOpen = ref(false)
const reviewing = ref(false)
const reviewError = ref('')
const current = ref<AttemptAnswer | null>(null)
const reviewForm = reactive({ new_score: 0, comment: '' })

const correctCount = computed(
  () => result.value?.answers.filter((answer) => answer.is_correct).length ?? 0,
)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    result.value = await attemptsApi.result(attemptId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

function openReview(answer: AttemptAnswer): void {
  current.value = answer
  reviewForm.new_score = answer.score
  reviewForm.comment = ''
  reviewError.value = ''
  reviewOpen.value = true
}

async function submitReview(): Promise<void> {
  if (!current.value || current.value.answer_record_id === null) return
  if (reviewForm.new_score < 0 || reviewForm.new_score > current.value.full_score) {
    reviewError.value = `分数需在 0 ~ ${current.value.full_score} 之间`
    return
  }
  reviewing.value = true
  reviewError.value = ''
  try {
    result.value = await attemptsApi.review(attemptId.value, {
      answer_record_id: current.value.answer_record_id,
      new_score: reviewForm.new_score,
      comment: reviewForm.comment.trim() || undefined,
    })
    reviewOpen.value = false
    toast.success('复核已保存')
  } catch (error) {
    reviewError.value = toUserMessage(error)
  } finally {
    reviewing.value = false
  }
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/papers/${result?.attempt.paper_id ?? ''}/attempts`">作答列表</RouterLink>
        · 批改复核
      </p>
      <h1>{{ result?.paper.title ?? '批改复核' }}</h1>
      <p class="page-head__lede">逐题查看学生答案与标准答案，待复核题目可直接修改得分。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink
        class="btn"
        :to="`/teacher/papers/${result?.attempt.paper_id ?? ''}/attempts`"
      >
        返回列表
      </RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="loading" class="loading-line">正在读取作答结果…</p>

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
        <span>提交：<b>{{ formatDateTime(result.attempt.submitted_at) }}</b></span>
        <span v-if="result.grading_ms !== null">批改耗时：<b>{{ result.grading_ms }} ms</b></span>
      </div>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>逐题明细</h2>
        <span class="card__meta">共 {{ result.answers.length }} 题</span>
      </header>
      <ReviewTable :answers="result.answers" style="margin-top: 10px" @review="openReview" />
    </section>

    <section v-if="result.reviews.length" class="card">
      <header class="card__head"><h2>复核记录</h2></header>
      <div class="stack" style="margin-top: 10px">
        <div v-for="review in result.reviews" :key="review.id" class="notice">
          <div class="row row--between row--wrap">
            <span>
              题目记录 #{{ review.answer_record_id }}：{{ formatScore(review.old_score) }} →
              <b>{{ formatScore(review.new_score) }}</b>
            </span>
            <span class="small tertiary">{{ formatDateTime(review.created_at) }}</span>
          </div>
          <p v-if="review.comment" class="small muted" style="margin-top: 4px">{{ review.comment }}</p>
        </div>
      </div>
    </section>
  </template>

  <BaseModal
    :open="reviewOpen"
    title="复核得分"
    :description="current ? `本题满分 ${formatScore(current.full_score)} 分` : ''"
    @close="reviewOpen = false"
  >
    <div v-if="current" class="form">
      <p class="notice" style="white-space: pre-wrap">{{ current.stem }}</p>
      <div class="form-row">
        <BaseField label="学生答案">
          <input class="input" type="text" :value="formatAnswer(current.raw_answer, current.type)" disabled />
        </BaseField>
        <BaseField label="标准答案">
          <input class="input" type="text" :value="formatAnswer(current.standard_answer, current.type)" disabled />
        </BaseField>
      </div>
      <BaseField label="新得分" required>
        <input
          v-model.number="reviewForm.new_score"
          class="input"
          type="number"
          min="0"
          :max="current.full_score"
          step="0.5"
        />
      </BaseField>
      <BaseField label="复核说明（选填）">
        <textarea v-model="reviewForm.comment" class="input" rows="2" placeholder="给学生看的说明" />
      </BaseField>
      <p v-if="reviewError" class="form-error">{{ reviewError }}</p>
    </div>
    <template #footer>
      <BaseButton @click="reviewOpen = false">取消</BaseButton>
      <BaseButton variant="primary" :loading="reviewing" @click="submitReview">保存复核</BaseButton>
    </template>
  </BaseModal>
</template>
