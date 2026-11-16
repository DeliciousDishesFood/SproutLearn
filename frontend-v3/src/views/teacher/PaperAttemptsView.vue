<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { PaperAttemptItem, PaperDetail } from '@/api/contract'
import { ATTEMPT_STATUS_LABEL, attemptStatusTone, formatDateTime, formatScore } from '@/utils/format'

const route = useRoute()
const paperId = computed(() => Number(route.params.paperId))

const paper = ref<PaperDetail | null>(null)
const attempts = ref<PaperAttemptItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const errorText = ref('')

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [detail, result] = await Promise.all([
      papersApi.detail(paperId.value),
      papersApi.attempts(paperId.value, { page: page.value, page_size: pageSize }),
    ])
    paper.value = detail
    attempts.value = result.list
    total.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

watch(page, () => void load())
onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/papers/${paperId}`">试卷详情</RouterLink> · 作答列表
      </p>
      <h1>{{ paper?.title ?? '作答列表' }}</h1>
      <p class="page-head__lede">按学生查看作答状态与得分，待复核题目可进入结果页逐题复核。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/papers/${paperId}`">返回试卷</RouterLink>
      <BaseButton @click="load">刷新</BaseButton>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="card">
    <header class="card__head">
      <h2>学生作答</h2>
      <span class="card__meta">共 {{ total }} 人次</span>
    </header>

    <p v-if="loading" class="loading-line">正在读取作答…</p>
    <EmptyState
      v-else-if="attempts.length === 0"
      title="还没有学生作答"
      description="试卷发布后，学生开始作答就会出现在这里。"
    />
    <template v-else>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>学生</th>
              <th>状态</th>
              <th class="num">得分</th>
              <th class="num">待复核</th>
              <th>开始时间</th>
              <th>提交时间</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in attempts" :key="item.id">
              <td>
                <span class="row-title">
                  <strong>{{ item.student_name ?? '未知学生' }}</strong>
                  <em>{{ item.student_no ?? '—' }}</em>
                </span>
              </td>
              <td>
                <BaseBadge :tone="attemptStatusTone(item.status)">
                  {{ ATTEMPT_STATUS_LABEL[item.status] }}
                </BaseBadge>
              </td>
              <td class="num">{{ formatScore(item.total_score) }} / {{ formatScore(item.full_score) }}</td>
              <td class="num">
                <BaseBadge v-if="item.needs_review_count > 0" tone="amber">
                  {{ item.needs_review_count }}
                </BaseBadge>
                <span v-else class="tertiary">0</span>
              </td>
              <td class="tertiary">{{ formatDateTime(item.started_at) }}</td>
              <td class="tertiary">{{ formatDateTime(item.submitted_at) }}</td>
              <td>
                <div class="actions">
                  <RouterLink class="btn btn--sm" :to="`/teacher/attempts/${item.attempt_id}/result`">
                    查看与复核
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
    </template>
  </section>
</template>
