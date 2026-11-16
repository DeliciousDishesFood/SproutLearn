<script setup lang="ts">
import type { AttemptAnswer } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import { formatAnswer, formatScore } from '@/utils/format'

defineProps<{ answers: AttemptAnswer[] }>()
defineEmits<{ (event: 'review', answer: AttemptAnswer): void }>()

function answerLabel(answer: AttemptAnswer): string {
  return formatAnswer(answer.raw_answer, answer.type)
}
</script>

<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th class="num">题号</th>
          <th>题干</th>
          <th>学生答案</th>
          <th>标准答案</th>
          <th class="num">得分</th>
          <th>状态</th>
          <th class="num">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="answer in answers" :key="answer.question_id">
          <td class="num">{{ answer.seq }}</td>
          <td>
            <span class="row-title">
              <strong>{{ answer.stem }}</strong>
              <em>满分 {{ formatScore(answer.full_score) }} · {{ answer.knowledge_tag }}</em>
            </span>
          </td>
          <td>{{ answerLabel(answer) }}</td>
          <td>{{ formatAnswer(answer.standard_answer, answer.type) }}</td>
          <td class="num">{{ formatScore(answer.score) }}</td>
          <td>
            <BaseBadge v-if="answer.needs_review" tone="amber">待复核</BaseBadge>
            <BaseBadge v-else-if="answer.is_correct" tone="lime">正确</BaseBadge>
            <BaseBadge v-else tone="danger">错误</BaseBadge>
          </td>
          <td>
            <div class="actions">
              <button
                class="btn btn--sm"
                type="button"
                :disabled="answer.answer_record_id === null"
                @click="$emit('review', answer)"
              >
                复核
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
