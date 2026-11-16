<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Users, BarChart3, FileText } from 'lucide-vue-next'
import StatCard from '@/components/ui/StatCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import HeatDots from '@/components/ui/HeatDots.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import TypewriterText from '@/components/ui/TypewriterText.vue'
import StudentStatusTable from '@/components/business/StudentStatusTable.vue'
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

const createPaperHref = computed(() =>
  currentClassId.value
    ? `/teacher/classes/${currentClassId.value}/papers/new`
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
      workbenchApi.classActivity(currentClassId.value, 52),
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
    // 接口失败就不显示金句，不用本地文案兜底。
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
      <p v-if="quote?.text" class="page-head__typing">
        <TypewriterText :text="quote.text" />
        <span class="page-head__typing-from">{{ quote.from }}</span>
      </p>
    </div>
    <div class="page-head__actions">
      <div v-if="classes.length" class="class-switch">
        <BaseSelect
          :model-value="currentClassId ? String(currentClassId) : ''"
          :options="classes.map((item) => ({ label: item.class_name, value: String(item.id) }))"
          :icon="Users"
          size="sm"
          aria-label="切换班级"
          @update:model-value="switchClass"
        />
      </div>
      <RouterLink class="btn" to="/teacher/notifications">发通知</RouterLink>
      <RouterLink class="btn btn--primary" :to="createPaperHref">组卷</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <div v-if="loadingClasses" class="stats">
    <div v-for="index in 4" :key="index" class="skeleton stat-skeleton" />
  </div>

  <EmptyState
    v-else-if="classes.length === 0"
    title="还没有创建班级"
    action-label="创建班级"
    @action="router.push('/teacher/classes')"
  />

  <template v-else>
    <section class="stats" aria-label="班级指标">
      <StatCard label="今日提交" :value="workbench?.today_submissions ?? 0">
        <template #icon><FileText :size="15" /></template>
      </StatCard>
      <StatCard
        label="平均得分率"
        :value="formatPercent(workbench?.average_score_rate ?? 0, 0)"
      >
        <template #icon><BarChart3 :size="15" /></template>
      </StatCard>
      <StatCard label="今日活跃学生" :value="workbench?.active_students ?? 0">
        <template #icon><Users :size="15" /></template>
      </StatCard>
      <StatCard label="班级人数" :value="currentClass?.student_count ?? 0">
        <template #icon><Users :size="15" /></template>
      </StatCard>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>最近试卷</h2>
        <RouterLink class="card__link" :to="`/teacher/classes/${currentClassId}/papers`">
          查看全部
        </RouterLink>
      </header>

      <BaseSkeleton v-if="loadingWorkbench" class="stack" :count="4" />
      <EmptyState
        v-else-if="!workbench || workbench.recent_papers.length === 0"
        title="最近还没有试卷"
        action-label="去组卷"
        @action="router.push(createPaperHref)"
      />
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
        <span class="card__meta">最近 52 周</span>
      </header>
      <HeatDots :days="activity" :weeks="52" role="teacher" />
    </section>

    <StudentStatusTable :class-id="currentClassId" />
  </template>
</template>

<style scoped>
.page-head__typing {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.6;
}

.page-head__typing-from {
  color: var(--text-3);
  font-size: 12px;
}
</style>
