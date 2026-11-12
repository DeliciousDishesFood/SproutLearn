<!-- 教师「教学工作台」：班级切换、四张今日卡、最近试卷、班级热力图与前 5 榜单（M3.2 §5.2）。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  ClipboardCheck,
  Files,
  Gauge,
  RefreshCw,
  Send,
  Trophy,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import ActivityHeatmap, {
  type HeatmapDay,
} from '@/components/business/ActivityHeatmap.vue'
import QuoteTypewriter from '@/components/business/QuoteTypewriter.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { workbenchApi } from '@/api/workbench'
import { useAuthStore } from '@/stores/auth'
import { useClassStore } from '@/stores/class'
import { PAPER_KIND_META, PAPER_STATUS_META } from '@/utils/constants'
import { formatDateTime, formatNumber } from '@/utils/format'
import type { PaperItem, TeacherWorkbench } from '@/api/types'
import type { SelectOption } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const classStore = useClassStore()

const selectedClassId = ref('')
const classesError = ref('')
const loading = ref(false)
const error = ref('')
const workbench = ref<TeacherWorkbench | null>(null)

const classOptions = computed<SelectOption[]>(() =>
  classStore.classes.map((item) => ({
    label: `${item.class_name} · ${item.course_name}`,
    value: String(item.id),
  })),
)

const currentClass = computed(
  () => classStore.classes.find((item) => String(item.id) === selectedClassId.value) ?? null,
)

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

const averageScore = computed(() => {
  const value = workbench.value?.average_score
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return String(Math.round(value * 100) / 100)
})

const statCards = computed(() => [
  {
    key: 'needs_review',
    label: '待复核',
    value: workbench.value ? formatNumber(workbench.value.pending_review) : '—',
    hint: workbench.value?.pending_review ? '主观题等待教师确认' : '没有待复核的作答',
    icon: ClipboardCheck,
    tone: 'warning',
  },
  {
    key: 'submitted_today',
    label: '今日提交',
    value: workbench.value ? formatNumber(workbench.value.today_submissions) : '—',
    hint: '按自然日统计',
    icon: Send,
    tone: 'primary',
  },
  {
    key: 'active_students',
    label: '活跃学生',
    value: workbench.value ? formatNumber(workbench.value.active_students) : '—',
    hint: '今日有答题记录',
    icon: UsersRound,
    tone: 'success',
  },
  {
    key: 'average_score',
    label: '班级平均分',
    value: averageScore.value,
    hint: '已提交作答的平均得分',
    icon: Gauge,
    tone: 'accent',
  },
])

const recentPapers = computed(() => (workbench.value?.recent_papers ?? []).slice(0, 6))
const rankStudents = computed(() =>
  (workbench.value?.top_students ?? workbench.value?.top5 ?? []).slice(0, 5),
)
const heatmapDays = computed<HeatmapDay[]>(() =>
  (workbench.value?.activity ?? []).map((day) => ({
    date: day.date,
    count: day.answers,
    xp: day.active_students,
  })),
)

function kindMeta(kind: PaperItem['kind']) {
  return PAPER_KIND_META[kind ?? 'practice']
}

function statusMeta(paper: PaperItem) {
  return PAPER_STATUS_META[paper.status] ?? PAPER_STATUS_META.draft
}

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

function syncClassQuery(): void {
  void router.replace({
    query: {
      ...route.query,
      class_id: selectedClassId.value,
    },
  })
}

async function loadWorkbench(): Promise<void> {
  if (!selectedClassId.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    workbench.value = await workbenchApi.teacher(Number(selectedClassId.value))
  } catch (err) {
    workbench.value = null
    error.value = mapError(err)
  } finally {
    loading.value = false
  }
}

async function bootstrap(): Promise<void> {
  classesError.value = ''
  try {
    await classStore.fetchAllClasses()
  } catch (err) {
    classesError.value = toUserMessage(err)
    return
  }
  if (classStore.classes.length === 0) return
  const queryId = Number(route.query.class_id)
  const matched = classStore.classes.find((item) => item.id === queryId)
  selectedClassId.value = String(matched ? matched.id : classStore.classes[0].id)
  if (!matched) syncClassQuery()
  await loadWorkbench()
}

function handleClassChange(value: string): void {
  if (value === selectedClassId.value) return
  selectedClassId.value = value
  workbench.value = null
  error.value = ''
  syncClassQuery()
  void loadWorkbench()
}

function openPaper(paper: PaperItem): void {
  void router.push({
    path: `/teacher/papers/${paper.id}`,
    query: { class_id: String(paper.class_id) },
  })
}

function gotoCreate(): void {
  void router.push({
    path: '/teacher/papers/new',
    query: selectedClassId.value ? { class_id: selectedClassId.value } : undefined,
  })
}

onMounted(bootstrap)
</script>

<template>
  <div class="page dashboard-page">
    <header class="page-head dashboard-head">
      <div class="page-head__text">
        <p class="eyebrow">TEACHING DESK</p>
        <h1 class="page-title">{{ greeting }}，{{ auth.displayName || '老师' }}</h1>
        <p class="page-subtitle">
          {{ currentClass ? `${currentClass.class_name} · ${currentClass.course_name}` : '先创建一个班级，再开始今天的教学。' }}
        </p>
      </div>
      <div class="dashboard-actions">
        <AppSelect
          :model-value="selectedClassId"
          label="当前班级"
          :options="classOptions"
          :disabled="classStore.classes.length === 0"
          class="class-select"
          @update:model-value="handleClassChange"
        />
        <span class="dashboard-date">{{ todayLabel }}</span>
        <button
          class="icon-btn"
          type="button"
          title="刷新工作台"
          aria-label="刷新工作台数据"
          :disabled="!selectedClassId || loading"
          @click="loadWorkbench"
        >
          <RefreshCw :size="16" :stroke-width="1.8" />
        </button>
      </div>
    </header>

    <section v-if="classesError" class="panel">
      <AppEmpty error title="班级列表暂时无法加载" :description="classesError">
        <template #action>
          <AppButton variant="secondary" @click="bootstrap">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <section v-else-if="classStore.classes.length === 0 && !classStore.loading" class="panel">
      <AppEmpty
        title="从第一个班级开始"
        description="创建班级后，学生的提交、成绩与活跃度会汇总到教学工作台。"
      >
        <template #action>
          <router-link to="/teacher/classes">
            <AppButton variant="primary">创建班级</AppButton>
          </router-link>
        </template>
      </AppEmpty>
    </section>

    <template v-else>
      <p v-if="error" class="soft-notice" role="status">
        {{ error }}，当前展示的是空工作台。
      </p>

      <div v-if="loading && !workbench" class="content-stack" aria-busy="true">
        <div class="stat-grid">
          <div v-for="index in 4" :key="index" class="panel panel-body">
            <AppSkeleton variant="stat" />
          </div>
        </div>
        <div class="panel panel-body">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="4" />
        </div>
      </div>

      <template v-else>
        <div class="stat-grid">
          <article
            v-for="card in statCards"
            :key="card.key"
            class="stat-card"
            :class="`stat-card--${card.tone}`"
          >
            <span class="stat-card__icon" aria-hidden="true">
              <component :is="card.icon" :size="19" :stroke-width="1.8" />
            </span>
            <p class="stat-card__label">{{ card.label }}</p>
            <p class="stat-card__value tabular">{{ card.value }}</p>
            <p class="stat-card__hint">{{ card.hint }}</p>
          </article>
        </div>

        <div class="workbench-grid">
          <section class="panel" aria-labelledby="papers-title">
            <header class="panel-head">
              <div>
                <h2 id="papers-title" class="section-title">最近试卷</h2>
                <p class="section-note">按创建时间排序，点击进入详情发布或查看成绩。</p>
              </div>
              <div class="panel-head__actions">
                <router-link
                  class="panel-link"
                  :to="{ path: '/teacher/papers', query: { class_id: selectedClassId } }"
                >
                  全部试卷
                  <ArrowRight :size="14" :stroke-width="1.9" />
                </router-link>
                <AppButton variant="secondary" size="sm" @click="gotoCreate">
                  新建试卷
                </AppButton>
              </div>
            </header>

            <div v-if="recentPapers.length > 0" class="paper-list">
              <button
                v-for="paper in recentPapers"
                :key="paper.id"
                class="paper-item"
                type="button"
                @click="openPaper(paper)"
              >
                <span class="paper-item__icon">
                  <Files :size="17" :stroke-width="1.7" aria-hidden="true" />
                </span>
                <span class="paper-item__main">
                  <span class="paper-item__title truncate">{{ paper.title }}</span>
                  <span class="paper-item__meta">
                    <AppTag :tone="kindMeta(paper.kind).tone">{{ kindMeta(paper.kind).label }}</AppTag>
                    <span>{{ paper.question_count }} 题 · {{ paper.total_score }} 分</span>
                    <span>
                      {{ paper.published_at ? `发布于 ${formatDateTime(paper.published_at)}` : `创建于 ${formatDateTime(paper.created_at)}` }}
                    </span>
                  </span>
                </span>
                <AppTag :tone="statusMeta(paper).tone" dot>{{ statusMeta(paper).label }}</AppTag>
                <ArrowRight class="paper-item__arrow" :size="15" :stroke-width="1.9" aria-hidden="true" />
              </button>
            </div>

            <AppEmpty
              v-else
              compact
              title="这个班还没有试卷"
              description="从题库组一份练习、作业或考试，发布后学生即可作答。"
            >
              <template #action>
                <AppButton variant="primary" size="sm" @click="gotoCreate">新建试卷</AppButton>
              </template>
            </AppEmpty>
          </section>

          <section class="panel" aria-labelledby="rank-title">
            <header class="panel-head">
              <div>
                <h2 id="rank-title" class="section-title">班级榜</h2>
                <p class="section-note">按累计经验排序，展示前 5 名。</p>
              </div>
              <Trophy :size="18" :stroke-width="1.7" aria-hidden="true" class="rank-icon" />
            </header>

            <ol v-if="rankStudents.length > 0" class="rank-list">
              <li
                v-for="(student, index) in rankStudents"
                :key="student.student_id"
                class="rank-item"
              >
                <span class="rank-item__index tabular" :class="`rank-item__index--${index + 1}`">
                  {{ index + 1 }}
                </span>
                <span class="rank-item__avatar">{{ student.name.trim().slice(0, 1) || '学' }}</span>
                <span class="rank-item__main">
                  <span class="rank-item__name truncate">{{ student.name }}</span>
                  <span class="rank-item__meta">
                    Lv.{{ student.level }}
                    <template v-if="student.title"> · {{ student.title }}</template>
                  </span>
                </span>
                <span class="rank-item__xp tabular">{{ formatNumber(student.xp_total) }}</span>
              </li>
            </ol>

            <AppEmpty
              v-else
              compact
              title="还没有经验数据"
              description="学生完成练习或提交作业后，榜单会逐步生成。"
            />
          </section>
        </div>

        <section class="panel" aria-labelledby="class-activity-title">
          <header class="panel-head">
            <div>
              <h2 id="class-activity-title" class="section-title">近 12 周班级活跃</h2>
              <p class="section-note">格子颜色按当日答题量分档；悬停可看当天题量与活跃人数。</p>
            </div>
          </header>
          <div class="panel-body">
            <ActivityHeatmap
              :days="heatmapDays"
              :weeks="12"
              count-label="答题"
              extra-label="活跃"
              empty-hint="本班还没有答题记录，发布第一份练习后这里就会亮起来。"
            />
          </div>
        </section>

        <section class="panel quote-panel" aria-labelledby="teacher-quote-title">
          <header class="panel-head">
            <div>
              <h2 id="teacher-quote-title" class="section-title">每日一句</h2>
              <p class="section-note">把今天的好句子，带进课堂。</p>
            </div>
          </header>
          <div class="panel-body">
            <QuoteTypewriter />
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.dashboard-head {
  align-items: flex-end;
}

.dashboard-actions {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.class-select {
  width: 260px;
}

.dashboard-date {
  padding-bottom: 10px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  white-space: nowrap;
}

.dashboard-actions .icon-btn {
  margin-bottom: 2px;
}

.soft-notice {
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, var(--color-border));
  border-radius: var(--radius-xs);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}

.stat-card {
  position: relative;
  padding: var(--sp-4);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.stat-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: var(--sp-4);
  right: var(--sp-4);
  height: 2px;
  border-radius: 0 0 999px 999px;
  background: var(--color-primary);
  opacity: 0.55;
}

.stat-card--warning::after {
  background: var(--color-warning);
}

.stat-card--success::after {
  background: var(--color-success);
}

.stat-card--accent::after {
  background: var(--color-accent);
}

.stat-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-bottom: var(--sp-3);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.stat-card--warning .stat-card__icon {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-surface));
}

.stat-card--success .stat-card__icon {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
}

.stat-card--accent .stat-card__icon {
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
  background: color-mix(in srgb, var(--color-accent) 12%, var(--color-surface));
}

.stat-card__label {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.stat-card__value {
  margin-top: 2px;
  font-size: 30px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.stat-card__hint {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr);
  gap: var(--sp-5);
  align-items: start;
  margin-bottom: var(--sp-5);
}

.panel-head__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.panel-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.paper-list {
  display: flex;
  flex-direction: column;
}

.paper-item {
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

.paper-item:last-child {
  border-bottom: 0;
}

.paper-item:hover {
  background: var(--color-surface-alt);
}

.paper-item:hover .paper-item__arrow {
  color: var(--color-primary);
  transform: translateX(2px);
}

.paper-item__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.paper-item__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.paper-item__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.paper-item__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-item__arrow {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: color 160ms ease-out, transform 160ms ease-out;
}

.rank-icon {
  color: var(--color-accent);
}

.rank-list {
  display: flex;
  flex-direction: column;
  padding: var(--sp-2) var(--sp-5) var(--sp-3);
}

.rank-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-2) 0;
  border-bottom: 1px solid var(--color-border);
}

.rank-item:last-child {
  border-bottom: 0;
}

.rank-item__index {
  width: 22px;
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  font-weight: 700;
  text-align: center;
}

.rank-item__index--1,
.rank-item__index--2,
.rank-item__index--3 {
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
}

.rank-item__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 999px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.rank-item__main {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}

.rank-item__name {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.rank-item__meta {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.rank-item__xp {
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: var(--fs-sm);
  font-weight: 700;
}

.quote-panel {
  max-width: 640px;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1023px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .quote-panel {
    max-width: none;
  }
}

@media (max-width: 560px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }

  .class-select {
    width: 100%;
  }
}
</style>
