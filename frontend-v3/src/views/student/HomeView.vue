<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Sprout } from 'lucide-vue-next'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import HeatDots from '@/components/ui/HeatDots.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import { workbenchApi } from '@/api/workbench'
import { notificationsApi } from '@/api/notifications'
import { toUserMessage } from '@/api/client'
import type { ActivityDay, StudentWorkbench } from '@/api/contract'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import {
  ATTEMPT_STATUS_LABEL,
  formatDateTime,
  formatScore,
  greeting,
  todayLabel,
} from '@/utils/format'

const auth = useAuthStore()
const ui = useUiStore()

const workbench = ref<StudentWorkbench | null>(null)
const activity = ref<ActivityDay[]>([])
const loading = ref(true)
const errorText = ref('')

const pending = computed(() => workbench.value?.pending_papers ?? workbench.value?.pending ?? [])
const recent = computed(() => workbench.value?.recent_scores ?? workbench.value?.recent ?? [])
const level = computed(() => workbench.value?.level ?? null)
const today = computed(() => workbench.value?.today ?? null)
const capPercent = computed(() => {
  if (!today.value || today.value.cap <= 0) return 0
  return Math.min(100, Math.round((today.value.total_xp / today.value.cap) * 100))
})
const levelPercent = computed(() =>
  Math.min(100, Math.max(0, Math.round(level.value?.progress_pct ?? 0))),
)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [summary, activityResult] = await Promise.all([
      workbenchApi.student(),
      workbenchApi.studentActivity(52),
    ])
    workbench.value = summary
    activity.value = activityResult.items ?? activityResult.activity ?? []
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
  try {
    const unread = await notificationsApi.unreadCount()
    ui.setUnreadCount(unread.count)
  } catch {
    // 未读数失败不影响首页
  }
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">{{ todayLabel() }}<template v-if="auth.student?.class_name"> · {{ auth.student.class_name }}</template></p>
      <h1>{{ greeting() }}，{{ auth.displayName }}</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student/growth">我的成长</RouterLink>
      <RouterLink class="btn btn--primary" to="/student/papers">去练习</RouterLink>
    </div>
  </header>

  <div v-if="errorText" class="notice notice--danger notice--with-action">
    <span>{{ errorText }}</span>
    <BaseButton size="sm" @click="load">重试</BaseButton>
  </div>
  <template v-if="loading">
    <div class="stats">
      <div v-for="index in 4" :key="index" class="skeleton stat-skeleton" />
    </div>
    <BaseSkeleton :count="5" height="18px" />
  </template>

  <template v-else-if="workbench">
    <section class="stats">
      <article class="stat stat--focus">
        <div class="stat__label">
          <span class="stat__icon stat__icon--focus" aria-hidden="true"><Sprout :size="15" /></span>当前等级
        </div>
        <div class="stat__row">
          <span class="stat__value">Lv.{{ level?.level ?? 1 }}</span>
          <span class="stat__delta stat__delta--focus">{{ level?.title ?? '青芽' }}</span>
        </div>
        <div class="stat__focus-progress">
          <span class="progress__bar"><i :style="{ transform: `scaleX(${levelPercent / 100})` }" /></span>
          <span class="stat__focus-note">
            {{ level?.next_min_xp ? `距下一级还需 ${level?.xp_to_next ?? 0} XP` : '已达最高等级' }}
          </span>
        </div>
      </article>
      <article class="stat">
        <div class="stat__label">累计经验</div>
        <div class="stat__row">
          <span class="stat__value">{{ workbench.xp_total }}</span>
          <span class="stat__delta stat__delta--soft">XP</span>
        </div>
      </article>
      <article class="stat">
        <div class="stat__label">连续学习</div>
        <div class="stat__row">
          <span class="stat__value">{{ workbench.streak_days }}</span>
          <span class="stat__delta stat__delta--soft">天</span>
        </div>
      </article>
      <article class="stat">
        <div class="stat__label">今日 XP</div>
        <div class="stat__row">
          <span class="stat__value">{{ today?.total_xp ?? 0 }}</span>
          <span class="stat__delta">上限 {{ today?.cap ?? 0 }}</span>
        </div>
        <div class="progress__bar" style="margin-top: 8px">
          <i :style="{ transform: `scaleX(${capPercent / 100})` }" />
        </div>
      </article>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>待办试卷</h2>
        <RouterLink class="card__link" to="/student/papers">查看全部</RouterLink>
      </header>
      <EmptyState
        v-if="pending.length === 0"
        title="暂无待办"
        action-label="去练习"
        @action="$router.push('/student/papers')"
      />
      <div v-else class="table" style="margin-top: 10px">
        <div class="table__head" aria-hidden="true"><span>试卷</span><span>用途</span><span>截止</span></div>
        <RouterLink
          v-for="paper in pending"
          :key="paper.id"
          class="table__row"
          :to="`/student/papers?paper=${paper.id}`"
        >
          <span class="table__main">
            <strong>{{ paper.title }}</strong>
            <em>{{ paper.question_count }} 题 · {{ paper.duration_minutes > 0 ? `${paper.duration_minutes} 分钟` : '不限时' }}</em>
          </span>
          <span class="table__meta" style="text-align: left">
            {{ paper.kind === 'practice' ? '练习' : paper.kind === 'homework' ? '作业' : '考试' }}
          </span>
          <span class="table__meta">{{ paper.due_at ? `截止 ${formatDateTime(paper.due_at)}` : '不限时' }}</span>
        </RouterLink>
      </div>
    </section>

    <section class="card card--heat">
      <header class="card__head">
        <h2>学习热力</h2>
        <span class="card__meta">最近 52 周</span>
      </header>
      <HeatDots :days="activity" :weeks="52" role="student" />
    </section>

    <section class="card">
      <header class="card__head">
        <h2>最近成绩</h2>
        <RouterLink class="card__link" to="/student/growth">成长记录</RouterLink>
      </header>
      <EmptyState
        v-if="recent.length === 0"
        title="还没有已完成的练习"
        action-label="去练习"
        @action="$router.push('/student/papers')"
      />
      <div v-else class="table" style="margin-top: 10px">
        <div class="table__head" aria-hidden="true"><span>试卷</span><span>得分</span><span>状态</span></div>
        <RouterLink
          v-for="item in recent"
          :key="item.attempt_id"
          class="table__row"
          :to="`/student/attempts/${item.attempt_id}/result`"
        >
          <span class="table__main">
            <strong>{{ item.paper_title }}</strong>
            <em>{{ formatDateTime(item.submitted_at) }}</em>
          </span>
          <span class="table__meta">{{ formatScore(item.total_score) }} / {{ formatScore(item.full_score) }}</span>
          <BaseBadge :tone="item.needs_review ? 'amber' : 'lime'">
            {{ item.needs_review ? '待复核' : ATTEMPT_STATUS_LABEL[item.status] }}
          </BaseBadge>
        </RouterLink>
      </div>
    </section>
  </template>
</template>
