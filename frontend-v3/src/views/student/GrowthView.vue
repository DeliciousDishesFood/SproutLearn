<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Sprout } from 'lucide-vue-next'
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

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [summary, activityResult] = await Promise.all([
      workbenchApi.growth(),
      workbenchApi.studentActivity(12),
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
      <p class="page-head__lede">等级、经验与每一次练习留下的记录。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student">回到学习台</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="loading" class="loading-line">正在读取成长记录…</p>

  <template v-else-if="growth">
    <section class="card stack">
      <header class="card__head">
        <h2>等级进度</h2>
        <span class="card__meta">{{ growth.xp_total }} XP</span>
      </header>
      <div class="row" style="align-items: center; gap: 14px">
        <span class="avatar" style="width: 46px; height: 46px; font-size: 16px" aria-hidden="true">
          <Sprout :size="20" />
        </span>
        <div>
          <p class="strong" style="font-size: 16px">Lv.{{ level?.level ?? 1 }} · {{ level?.title ?? '青芽' }}</p>
          <p class="small tertiary">
            累计 {{ growth.xp_total }} XP
            <template v-if="level?.next_min_xp">· 距下一级还需 {{ level?.xp_to_next ?? 0 }} XP</template>
            <template v-else>· 已达最高等级</template>
          </p>
        </div>
      </div>
      <div class="progress">
        <span class="progress__bar"><i :style="{ width: `${progress}%` }" /></span>
        <span class="progress__text">{{ progress }}%</span>
      </div>
      <div class="kv">
        <span>当前等级起点：<b>{{ level?.min_xp ?? 0 }} XP</b></span>
        <span v-if="level?.next_min_xp">下一等级：<b>Lv.{{ level?.next_level }} · {{ level?.next_min_xp }} XP</b></span>
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
        description="完成练习、连续学习都会产生经验。"
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
              <td>{{ item.source }}</td>
              <td class="muted">{{ item.note ?? '—' }}</td>
              <td class="num" :style="{ color: item.xp >= 0 ? 'var(--lime-text)' : 'var(--danger)' }">
                {{ item.xp >= 0 ? '+' : '' }}{{ item.xp }}
              </td>
              <td class="tertiary">{{ formatDateTime(item.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card card--heat">
      <header class="card__head">
        <h2>学习热力</h2>
        <span class="card__meta">最近 12 周 · 悬停查看每日经验</span>
      </header>
      <HeatDots :days="activity" :weeks="12" role="student" />
    </section>
  </template>

  <EmptyState
    v-else-if="!loading"
    title="暂时没有成长数据"
    description="完成第一份练习后，等级与经验流水会出现在这里。"
  />
</template>
