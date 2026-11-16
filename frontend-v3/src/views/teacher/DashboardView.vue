<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ClipboardList, Users, BarChart3, FileText } from 'lucide-vue-next'
import StatCard from '@/components/ui/StatCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import HeatDots from '@/components/ui/HeatDots.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { classesApi } from '@/api/classes'
import { workbenchApi } from '@/api/workbench'
import { notificationsApi } from '@/api/notifications'
import { toUserMessage } from '@/api/client'
import type { ActivityDay, ClassListItem, QuoteResult, TeacherWorkbench } from '@/api/contract'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import {
  PAPER_STATUS_LABEL,
  formatDateTime,
  formatPercent,
  greeting,
  paperStatusTone,
  todayLabel,
} from '@/utils/format'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const classes = ref<ClassListItem[]>([])
const workbench = ref<TeacherWorkbench | null>(null)
const activity = ref<ActivityDay[]>([])
const quote = ref<QuoteResult | null>(null)
const loadingClasses = ref(true)
const loadingWorkbench = ref(false)
const errorText = ref('')

const currentClassId = computed(() => {
  if (ui.currentClassId && classes.value.some((item) => item.id === ui.currentClassId)) {
    return ui.currentClassId
  }
  return classes.value[0]?.id ?? null
})

const currentClass = computed(
  () => classes.value.find((item) => item.id === currentClassId.value) ?? null,
)

const reviewHref = computed(() =>
  currentClassId.value
    ? `/teacher/classes/${currentClassId.value}/review`
    : '/teacher/classes',
)

async function loadClasses(): Promise<void> {
  loadingClasses.value = true
  errorText.value = ''
  try {
    const result = await classesApi.list({ page: 1, page_size: 50 })
    classes.value = result.list
    if (currentClassId.value) ui.setCurrentClassId(currentClassId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loadingClasses.value = false
  }
}

async function loadWorkbench(): Promise<void> {
  if (!currentClassId.value) return
  loadingWorkbench.value = true
  errorText.value = ''
  try {
    const [summary, activityResult] = await Promise.all([
      workbenchApi.teacher(currentClassId.value),
      workbenchApi.classActivity(currentClassId.value, 12),
    ])
    workbench.value = summary
    activity.value = activityResult.items ?? activityResult.activity ?? []
  } catch (error) {
    workbench.value = null
    activity.value = []
    errorText.value = toUserMessage(error)
  } finally {
    loadingWorkbench.value = false
  }
}

async function loadExtras(): Promise<void> {
  try {
    quote.value = await workbenchApi.quote()
  } catch {
    quote.value = null
  }
  try {
    const unread = await notificationsApi.unreadCount()
    ui.setUnreadCount(unread.count)
  } catch {
    // 未读数失败不影响工作台
  }
}

function switchClass(value: unknown): void {
  const next = Number(value)
  if (!Number.isFinite(next) || next <= 0) return
  ui.setCurrentClassId(next)
}

function goCreatePaper(): void {
  if (!currentClassId.value) return
  void router.push(`/teacher/classes/${currentClassId.value}/papers/new`)
}

watch(currentClassId, () => {
  void loadWorkbench()
})

onMounted(async () => {
  await loadClasses()
  await loadWorkbench()
  void loadExtras()
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        {{ todayLabel() }}<span v-if="currentClass"> · {{ currentClass.class_name }}</span>
      </p>
      <h1>{{ greeting() }}，{{ auth.displayName }}</h1>
      <p class="page-head__lede">今天也和学生一起，把每个知识点讲清楚。</p>
    </div>
    <div class="page-head__actions">
      <div v-if="classes.length" class="class-switch">
        <BaseSelect
          :model-value="currentClassId ? String(currentClassId) : ''"
          :options="classes.map((item) => ({ label: item.class_name, value: String(item.id) }))"
          size="sm"
          aria-label="切换班级"
          @update:model-value="switchClass"
        />
      </div>
      <RouterLink class="btn" to="/teacher/notifications">发通知</RouterLink>
      <RouterLink class="btn btn--primary" :to="reviewHref">去批改</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <div v-if="loadingClasses" class="stats">
    <div v-for="index in 4" :key="index" class="skeleton stat-skeleton" />
  </div>

  <EmptyState
    v-else-if="classes.length === 0"
    title="还没有创建班级"
    description="创建第一个班级后，就能上传资料、组卷并把练习发给学生。"
    action-label="创建班级"
    @action="router.push('/teacher/classes')"
  />

  <template v-else>
    <section class="stats" aria-label="班级指标">
      <StatCard
        label="待复核题目"
        :value="workbench?.pending_review ?? 0"
        :tag="(workbench?.pending_review ?? 0) > 0 ? '需处理' : '已清空'"
        :tag-tone="(workbench?.pending_review ?? 0) > 0 ? 'warn' : 'soft'"
        hint="按题目计数，不是作业份数"
      >
        <template #icon><ClipboardList :size="15" /></template>
      </StatCard>
      <StatCard
        label="今日提交"
        :value="workbench?.today_submissions ?? 0"
        hint="今天提交的作答数"
      >
        <template #icon><FileText :size="15" /></template>
      </StatCard>
      <StatCard
        label="平均得分率"
        :value="formatPercent(workbench?.average_score_rate ?? 0, 0)"
        :hint="`原始平均分 ${workbench?.average_score ?? 0}`"
      >
        <template #icon><BarChart3 :size="15" /></template>
      </StatCard>
      <StatCard
        label="今日活跃学生"
        :value="workbench?.active_students ?? 0"
        hint="今天有答题记录的去重学生"
      >
        <template #icon><Users :size="15" /></template>
      </StatCard>
    </section>

    <div class="columns">
      <section class="card">
        <header class="card__head">
          <h2>最近试卷</h2>
          <RouterLink
            class="card__link"
            :to="currentClassId ? `/teacher/classes/${currentClassId}/papers` : '/teacher/classes'"
          >
            查看全部
          </RouterLink>
        </header>

        <BaseSkeleton v-if="loadingWorkbench" class="stack" :count="4" />
        <p v-else-if="!workbench || workbench.recent_papers.length === 0" class="empty-block">
          <span>最近还没有试卷。</span>
        </p>
        <div v-else class="table" style="margin-top: 10px">
          <div class="table__head" aria-hidden="true">
            <span>试卷</span><span>状态</span><span>题量</span>
          </div>
          <RouterLink
            v-for="paper in workbench.recent_papers"
            :key="paper.id"
            class="table__row"
            :to="`/teacher/papers/${paper.id}`"
          >
            <span class="table__main">
              <strong>{{ paper.title }}</strong>
              <em>
                {{ paper.kind === 'practice' ? '练习' : paper.kind === 'homework' ? '作业' : '考试' }}
                · {{ paper.due_at ? `截止 ${formatDateTime(paper.due_at)}` : '未设置截止' }}
              </em>
            </span>
            <BaseBadge :tone="paperStatusTone(paper.status)">
              {{ PAPER_STATUS_LABEL[paper.status] }}
            </BaseBadge>
            <span class="table__meta">{{ paper.question_count }} 题</span>
          </RouterLink>
        </div>
      </section>

      <section class="card card--heat">
        <header class="card__head">
          <h2>学习热力</h2>
          <span class="card__meta">最近 12 周</span>
        </header>
        <HeatDots :days="activity" :weeks="12" role="teacher" />
      </section>
    </div>

    <div class="columns columns--even">
      <blockquote class="card quote-card">
        <p>“{{ quote?.text ?? '把复杂讲简单，把简单讲深刻。' }}”</p>
        <cite>{{ quote?.from ?? '青芽教学手记' }}</cite>
      </blockquote>

      <section v-if="(workbench?.pending_review ?? 0) > 0" class="card stack">
        <header class="card__head">
          <h2>待复核题目</h2>
          <span class="card__meta">{{ workbench?.pending_review }} 道</span>
        </header>
        <p class="small tertiary">顶部统计按题目计数；进入批改页逐题复核。</p>
        <RouterLink class="btn btn--primary" :to="reviewHref">去批改</RouterLink>
      </section>

      <EmptyState
        v-else
        title="暂无待复核题目"
        description="提交并完成复核后，这里会清零。"
        action-label="去组卷"
        @action="goCreatePaper"
      />
    </div>

    <footer class="foot">青芽 SproutLearn · 教师工作台</footer>
  </template>
</template>
