<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Sprout } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import HeatDots from '@/components/ui/HeatDots.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { workbenchApi } from '@/api/workbench'
import { toUserMessage } from '@/api/client'
import type { ActivityDay, GrowthSummary } from '@/api/contract'
import { formatDateTime } from '@/utils/format'

const growth = ref<GrowthSummary | null>(null)
const activity = ref<ActivityDay[]>([])
const loading = ref(true)
const errorText = ref('')

const level = computed(() => growth.value?.level ?? null)
const progress = computed(() => Math.min(100, Math.max(0, level.value?.progress_pct ?? 0)))

const SOURCE_LABEL: Record<string, string> = {
  login: '每日登录',
  practice: '练习作答',
  submission: '提交试卷',
  submit: '提交试卷',
  streak: '连续学习',
  review: '老师复核',
  adjust: '老师调整',
  homework: '作业',
  exam: '考试',
  answer: '作答题目',
}

function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [summary, activityResult] = await Promise.all([
      workbenchApi.growth(),
      workbenchApi.studentActivity(52),
    ])
    growth.value = summary
    activity.value = summary.heatmap ?? summary.activity ?? activityResult.items ?? []
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">我的 · 成长</p>
      <h1>成长</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student">回到学习台</RouterLink>
    </div>
  </header>

  <div v-if="errorText" class="notice notice--danger notice--with-action">
    <span>{{ errorText }}</span>
    <BaseButton size="sm" @click="load">重试</BaseButton>
  </div>
  <p v-if="loading" class="loading-line">正在读取成长记录…</p>

  <template v-else-if="growth">
    <section class="growth-hero">
      <header class="growth-hero__head">
        <div>
          <p class="growth-hero__eyebrow">当前等级</p>
          <p class="growth-hero__level">
            <span class="growth-hero__badge" aria-hidden="true"><Sprout :size="16" /></span>
            Lv.{{ level?.level ?? 1 }} · {{ level?.title ?? '青芽' }}
          </p>
        </div>
        <span class="growth-hero__xp">{{ growth.xp_total }} XP</span>
      </header>
      <div class="growth-hero__progress">
        <span class="progress__bar"><i :style="{ transform: `scaleX(${progress / 100})` }" /></span>
        <span class="growth-hero__pct">{{ progress }}%</span>
      </div>
      <div class="growth-hero__meta">
        <span>本等级起点 {{ level?.min_xp ?? 0 }} XP</span>
        <span v-if="level?.next_min_xp">距下一级还需 {{ level?.xp_to_next ?? 0 }} XP</span>
        <span v-else>已达最高等级</span>
      </div>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>经验流水</h2>
        <span class="card__meta">共 {{ growth.ledger.length }} 条</span>
      </header>
      <EmptyState
        v-if="growth.ledger.length === 0"
        title="还没有经验记录"
      />
      <div v-else class="table-wrap" style="margin-top: 10px; max-height: 460px; overflow-y: auto">
        <table class="table">
          <thead>
            <tr>
              <th>来源</th>
              <th>说明</th>
              <th class="num">经验</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in growth.ledger" :key="item.id">
              <td>{{ sourceLabel(item.source) }}</td>
              <td class="muted">
                {{ item.note ?? '—' }}
                <RouterLink
                  v-if="item.ref_type === 'attempt' && item.ref_id"
                  class="growth-ledger__link"
                  :to="`/student/attempts/${item.ref_id}/result`"
                >
                  查看答卷
                </RouterLink>
              </td>
              <td class="num" :style="{ color: item.xp >= 0 ? 'var(--lime-text)' : 'var(--danger)' }">
                {{ item.xp >= 0 ? '+' : '' }}{{ item.xp }}
              </td>
              <td class="text-3">{{ formatDateTime(item.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card card--heat">
      <header class="card__head">
        <h2>学习热力</h2>
        <span class="card__meta">最近 52 周</span>
      </header>
      <HeatDots :days="activity" :weeks="52" role="student" />
    </section>
  </template>

  <EmptyState v-else-if="!loading" title="暂时没有成长数据" />
</template>
