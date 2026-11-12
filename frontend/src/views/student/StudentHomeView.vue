<!-- 学生「学习台」：等级经验、待做练习、最近成绩、12 周热力图与金句打字机（M3.2 §5.1）。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  CalendarClock,
  Flame,
  RefreshCw,
  Sparkles,
  Target,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import ActivityHeatmap, {
  type HeatmapDay,
} from '@/components/business/ActivityHeatmap.vue'
import QuoteTypewriter from '@/components/business/QuoteTypewriter.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { workbenchApi } from '@/api/workbench'
import { useAuthStore } from '@/stores/auth'
import {
  ATTEMPT_STATUS_META,
  PAPER_KIND_META,
} from '@/utils/constants'
import { formatDateTime, formatNumber } from '@/utils/format'
import type {
  AttemptStatus,
  LevelInfo,
  StudentRecentAttempt,
  StudentWorkbench,
} from '@/api/types'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const error = ref('')
const workbench = ref<StudentWorkbench | null>(null)

const studentUser = computed(() => (auth.user?.role === 'student' ? auth.user : null))
const studentName = computed(() => studentUser.value?.name || '同学')
const initial = computed(() => studentName.value.trim().slice(0, 1) || '学')
const className = computed(() => studentUser.value?.class_name || '')

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const todayLabel = computed(() => {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    }).format(new Date())
  } catch {
    return ''
  }
})

const levelInfo = computed<LevelInfo | null>(() => workbench.value?.level ?? null)
const displayLevel = computed(() => levelInfo.value?.level ?? studentUser.value?.level ?? 1)
const levelTitle = computed(() => levelInfo.value?.title ?? '')
const xpTotal = computed(() => workbench.value?.xp_total ?? studentUser.value?.xp_total ?? 0)
const xpIntoLevel = computed(() =>
  levelInfo.value ? Math.max(0, xpTotal.value - levelInfo.value.min_xp) : 0,
)
const levelSpan = computed(() =>
  levelInfo.value ? Math.max(0, levelInfo.value.next_min_xp - levelInfo.value.min_xp) : 0,
)
const progressPercent = computed(() => {
  if (!levelInfo.value) return 0
  return Math.min(100, Math.max(0, levelInfo.value.progress_pct ?? 0))
})
const progressCaption = computed(() => {
  if (!levelInfo.value) return '完成一次练习，经验会在这里累积'
  return `再获得 ${levelInfo.value.xp_to_next ?? 0} 经验升到 Lv.${levelInfo.value.next_level}`
})

const streakDays = computed(() => workbench.value?.streak_days ?? 0)
const todayXp = computed(() => workbench.value?.today?.total_xp ?? 0)
const todayCap = computed(() => workbench.value?.today?.cap ?? 0)

const pendingPapers = computed(() =>
  (workbench.value?.pending_papers ?? workbench.value?.pending ?? []).slice(0, 5),
)
const recentAttempts = computed(() =>
  (workbench.value?.recent_scores ?? workbench.value?.recent ?? []).slice(0, 5),
)
const heatmapDays = computed<HeatmapDay[]>(() =>
  (workbench.value?.activity ?? []).map((day) => ({
    date: day.date,
    count: day.answers,
    xp: day.xp,
  })),
)

function kindMeta(kind?: keyof typeof PAPER_KIND_META) {
  return PAPER_KIND_META[kind ?? 'practice']
}

function attemptMeta(status: AttemptStatus) {
  return ATTEMPT_STATUS_META[status] ?? ATTEMPT_STATUS_META.doing
}

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

async function loadWorkbench(): Promise<void> {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    workbench.value = await workbenchApi.student()
    void auth.fetchMe().catch(() => undefined)
  } catch (err) {
    error.value = mapError(err)
  } finally {
    loading.value = false
  }
}

function openPaper(): void {
  void router.push('/student/papers')
}

function openAttempt(attempt: StudentRecentAttempt): void {
  void router.push(`/student/attempts/${attempt.attempt_id}/result`)
}

onMounted(loadWorkbench)
</script>

<template>
  <div class="page student-home">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">LEARNING DESK</p>
        <h1 class="page-title">{{ greeting }}，{{ studentName }}</h1>
        <p class="page-subtitle">
          {{ className || '你的学习空间' }} · 今天也给经验条添一点新的绿色。
        </p>
      </div>
      <div class="page-actions">
        <span class="muted text-xs">{{ todayLabel }}</span>
        <AppButton variant="ghost" :loading="loading" @click="loadWorkbench">
          <RefreshCw v-if="!loading" :size="15" :stroke-width="1.8" />
          刷新
        </AppButton>
      </div>
    </header>

    <p v-if="error" class="soft-notice" role="status">
      {{ error }}，当前展示的是本地缓存的成长信息。
    </p>

    <section v-if="loading && !workbench" class="content-stack" aria-busy="true">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="3" />
      </div>
      <div class="learn-grid">
        <div class="panel panel-body"><AppSkeleton variant="text" :rows="5" /></div>
        <div class="panel panel-body"><AppSkeleton variant="text" :rows="5" /></div>
      </div>
    </section>

    <template v-else>
      <section class="level-panel panel" aria-label="等级与今日经验">
        <div class="level-panel__identity">
          <span class="level-panel__avatar">{{ initial }}</span>
          <div class="level-panel__identity-copy">
            <p class="level-panel__label">当前等级</p>
            <p class="level-panel__level">
              <span class="tabular">Lv.{{ displayLevel }}</span>
              <span v-if="levelTitle" class="level-panel__title">{{ levelTitle }}</span>
            </p>
            <p class="level-panel__xp tabular">累计 {{ formatNumber(xpTotal) }} 经验</p>
          </div>
        </div>

        <div class="level-panel__progress">
          <div class="level-panel__progress-head">
            <span>本级进度</span>
            <strong class="tabular">
              {{ levelSpan > 0 ? `${xpIntoLevel} / ${levelSpan}` : 'MAX' }}
            </strong>
          </div>
          <div class="level-panel__track" aria-hidden="true">
            <span class="level-panel__fill" :style="{ width: `${progressPercent}%` }" />
          </div>
          <p class="level-panel__caption">{{ progressCaption }}</p>
        </div>

        <dl class="level-panel__stats">
          <div>
            <dt><Flame :size="14" :stroke-width="1.8" aria-hidden="true" />连续学习</dt>
            <dd class="tabular">{{ streakDays }} 天</dd>
          </div>
          <div>
            <dt><Sparkles :size="14" :stroke-width="1.8" aria-hidden="true" />今日经验</dt>
            <dd class="tabular">{{ todayXp }} / {{ todayCap }}</dd>
          </div>
          <div>
            <dt><Target :size="14" :stroke-width="1.8" aria-hidden="true" />待做练习</dt>
            <dd class="tabular">{{ pendingPapers.length }} 份</dd>
          </div>
        </dl>
      </section>

      <div class="learn-grid">
        <section class="panel" aria-labelledby="pending-title">
          <header class="panel-head">
            <div>
              <h2 id="pending-title" class="section-title">待完成</h2>
              <p class="section-note">已发布、还没提交的练习、作业与考试。</p>
            </div>
            <router-link class="panel-link" to="/student/papers">
              全部练习
              <ArrowRight :size="14" :stroke-width="1.9" />
            </router-link>
          </header>

          <div v-if="pendingPapers.length > 0" class="pending-list">
            <button
              v-for="paper in pendingPapers"
              :key="paper.id"
              class="pending-item"
              type="button"
              @click="openPaper"
            >
              <span class="pending-item__main">
                <span class="pending-item__title truncate">{{ paper.title }}</span>
                <span class="pending-item__meta">
                  <AppTag :tone="kindMeta(paper.kind).tone">{{ kindMeta(paper.kind).label }}</AppTag>
                  <span>{{ paper.question_count }} 题 · {{ paper.total_score }} 分</span>
                  <span v-if="paper.deadline_at" class="pending-item__deadline">
                    <CalendarClock :size="12" :stroke-width="1.8" aria-hidden="true" />
                    {{ formatDateTime(paper.deadline_at) }} 截止
                  </span>
                  <span v-else>不限时</span>
                </span>
              </span>
              <AppTag tone="neutral">待作答</AppTag>
              <ArrowRight class="pending-item__arrow" :size="15" :stroke-width="1.9" aria-hidden="true" />
            </button>
          </div>

          <AppEmpty
            v-else
            compact
            title="暂时没有待做练习"
            description="老师发布练习后，会第一时间出现在这里。"
          >
            <template #action>
              <router-link to="/student/papers">
                <AppButton variant="secondary" size="sm">去练习</AppButton>
              </router-link>
            </template>
          </AppEmpty>
        </section>

        <section class="panel" aria-labelledby="scores-title">
          <header class="panel-head">
            <div>
              <h2 id="scores-title" class="section-title">最近成绩</h2>
              <p class="section-note">最新 5 次提交，含教师复核状态。</p>
            </div>
          </header>

          <div v-if="recentAttempts.length > 0" class="score-list">
            <button
              v-for="attempt in recentAttempts"
              :key="attempt.attempt_id"
              class="score-item"
              type="button"
              @click="openAttempt(attempt)"
            >
              <span class="score-item__main">
                <span class="score-item__title truncate">{{ attempt.paper_title }}</span>
                <span class="score-item__meta">
                  <AppTag :tone="kindMeta(attempt.kind).tone">{{ kindMeta(attempt.kind).label }}</AppTag>
                  <span>{{ formatDateTime(attempt.submitted_at) }}</span>
                </span>
              </span>
              <span class="score-item__score tabular">
                {{ attempt.total_score }}<small>/{{ attempt.full_score }}</small>
              </span>
              <AppTag :tone="attempt.needs_review ? 'accent' : attemptMeta(attempt.status).tone">
                {{ attempt.needs_review ? '待复核' : attemptMeta(attempt.status).label }}
              </AppTag>
            </button>
          </div>

          <AppEmpty
            v-else
            compact
            title="还没有提交记录"
            description="完成第一份练习后，成绩会出现在这里。"
          />
        </section>
      </div>

      <section class="panel" aria-labelledby="activity-title">
        <header class="panel-head">
          <div>
            <h2 id="activity-title" class="section-title">近 12 周活跃</h2>
            <p class="section-note">每天答题越多，格子颜色越深；悬停可看当天题数与经验。</p>
          </div>
        </header>
        <div class="panel-body">
          <ActivityHeatmap
            :days="heatmapDays"
            :weeks="12"
            count-label="答题"
            extra-label="经验"
            empty-hint="还没有答题记录，完成一次练习后这里就会亮起来。"
          />
        </div>
      </section>

      <section class="panel quote-panel" aria-labelledby="quote-title">
        <header class="panel-head">
          <div>
            <h2 id="quote-title" class="section-title">每日一句</h2>
            <p class="section-note">读一句，再出发。</p>
          </div>
        </header>
        <div class="panel-body">
          <QuoteTypewriter />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.student-home {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1040px;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.soft-notice {
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, var(--color-border));
  border-radius: var(--radius-xs);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.level-panel {
  display: grid;
  grid-template-columns: minmax(230px, 0.9fr) minmax(240px, 1.2fr) minmax(240px, 0.9fr);
  gap: var(--sp-5);
  align-items: center;
  padding: var(--sp-5);
  background:
    radial-gradient(circle at 92% 0, color-mix(in srgb, var(--color-accent) 12%, transparent) 0, transparent 42%),
    linear-gradient(150deg, var(--color-surface) 0%, var(--color-surface-alt) 100%);
}

.level-panel__identity {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}

.level-panel__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 999px;
  color: var(--color-accent);
  background: var(--color-primary);
  font-size: var(--fs-xl);
  font-weight: 600;
}

.level-panel__identity-copy {
  min-width: 0;
}

.level-panel__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  letter-spacing: 0.06em;
}

.level-panel__level {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin-top: 2px;
  font-size: var(--fs-2xl);
  font-weight: 700;
  line-height: 1.2;
}

.level-panel__title {
  padding: 1px 8px;
  border-radius: 999px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.level-panel__xp {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.level-panel__progress {
  min-width: 0;
}

.level-panel__progress-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.level-panel__progress-head strong {
  color: var(--color-text);
  font-size: var(--fs-sm);
}

.level-panel__track {
  height: 8px;
  margin-top: var(--sp-2);
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface-alt));
}

.level-panel__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    var(--color-primary) 0%,
    color-mix(in srgb, var(--color-primary) 62%, var(--color-accent)) 100%
  );
  transition: width 240ms ease-out;
}

.level-panel__caption {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.level-panel__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

.level-panel__stats div {
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.level-panel__stats dt {
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--color-text-muted);
  font-size: 10px;
  white-space: nowrap;
}

.level-panel__stats dd {
  margin-top: 2px;
  font-size: var(--fs-lg);
  font-weight: 700;
  color: var(--color-primary);
  white-space: nowrap;
}

.learn-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: var(--sp-5);
  align-items: start;
}

.panel-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.pending-list,
.score-list {
  display: flex;
  flex-direction: column;
}

.pending-item,
.score-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  width: 100%;
  padding: var(--sp-3) var(--sp-5);
  border: 0;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  text-align: left;
  transition: background-color 160ms ease-out;
}

.pending-item:last-child,
.score-item:last-child {
  border-bottom: 0;
}

.pending-item:hover,
.score-item:hover {
  background: var(--color-surface-alt);
}

.pending-item:hover .pending-item__arrow {
  color: var(--color-primary);
  transform: translateX(2px);
}

.pending-item__main,
.score-item__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.pending-item__title,
.score-item__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.pending-item__meta,
.score-item__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.pending-item__deadline {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.pending-item__arrow {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: color 160ms ease-out, transform 160ms ease-out;
}

.score-item__score {
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: var(--fs-xl);
  font-weight: 700;
  white-space: nowrap;
}

.score-item__score small {
  margin-left: 1px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-weight: 500;
}

.quote-panel {
  max-width: 640px;
}

@media (max-width: 1023px) {
  .level-panel {
    grid-template-columns: 1fr;
    gap: var(--sp-4);
  }

  .learn-grid {
    grid-template-columns: 1fr;
  }

  .quote-panel {
    max-width: none;
  }
}

@media (max-width: 560px) {
  .level-panel__stats {
    grid-template-columns: 1fr;
  }
}
</style>
