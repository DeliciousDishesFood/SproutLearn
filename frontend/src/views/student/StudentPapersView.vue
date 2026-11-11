<!-- 学生试卷列表：可作答试卷 + 历史成绩；撤回后的卷仍可从历史结果打开。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowRight,
  CirclePlay,
  Clock3,
  History,
  RefreshCw,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppCard from '@/components/base/AppCard.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { papersApi } from '@/api/papers'
import { attemptsApi } from '@/api/attempts'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { ATTEMPT_STATUS_META, PAGE_SIZE } from '@/utils/constants'
import type { TagTone } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import type { AttemptStatus, MyAttemptItem, PaperItem } from '@/api/types'
import type { TableColumn } from '@/types'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const papers = ref<PaperItem[]>([])
const papersTotal = ref(0)
const papersPage = ref(1)
const papersPageSize = ref(PAGE_SIZE)
const papersLoading = ref(false)
const papersError = ref('')

const attempts = ref<MyAttemptItem[]>([])
const attemptsLoading = ref(false)
const attemptsError = ref('')

const startingPaperId = ref<number | null>(null)
const allPublishedIds = ref<Set<number>>(new Set())
const publishedIndexLoaded = ref(false)
const publishedIndexComplete = ref(false)

const student = computed(() => (auth.user?.role === 'student' ? auth.user : null))
const classId = computed(() => student.value?.class_id ?? null)
const attemptsByPaper = computed(() => {
  const map = new Map<number, MyAttemptItem>()
  for (const attempt of attempts.value) map.set(attempt.paper_id, attempt)
  return map
})

const historyColumns: TableColumn[] = [
  { key: 'paper_title', title: '试卷' },
  { key: 'status', title: '状态', width: '96px' },
  { key: 'score', title: '得分', width: '108px', align: 'right' },
  { key: 'submitted_at', title: '提交时间', width: '170px' },
  { key: 'actions', title: '操作', width: '120px', align: 'right' },
]

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

function attemptOf(paperId: number): MyAttemptItem | undefined {
  return attemptsByPaper.value.get(paperId)
}

function isWithdrawn(attempt: MyAttemptItem): boolean {
  return (
    publishedIndexLoaded.value &&
    publishedIndexComplete.value &&
    !allPublishedIds.value.has(attempt.paper_id) &&
    attempt.status !== 'doing'
  )
}

function paperState(paper: PaperItem): {
  label: string
  tone: TagTone
} {
  const attempt = attemptOf(paper.id)
  if (!attempt) return { label: '未作答', tone: 'neutral' }
  const meta = ATTEMPT_STATUS_META[attempt.status]
  return { label: meta?.label ?? '进行中', tone: meta?.tone ?? 'neutral' }
}

function attemptMeta(status: AttemptStatus): (typeof ATTEMPT_STATUS_META)[AttemptStatus] {
  return ATTEMPT_STATUS_META[status]
}

function openResult(attemptId: number): void {
  void router.push({
    name: 'student-attempt-result',
    params: { id: String(attemptId) },
  })
}

function openAttempt(attemptId: number, paperId: number): void {
  void router.push({
    name: 'student-attempt',
    params: { id: String(attemptId) },
    query: { paper_id: String(paperId) },
  })
}

async function startPaper(paper: PaperItem): Promise<void> {
  if (startingPaperId.value !== null) return
  const existing = attemptOf(paper.id)
  if (existing) {
    if (existing.status === 'doing') openAttempt(existing.attempt_id, paper.id)
    else openResult(existing.attempt_id)
    return
  }
  startingPaperId.value = paper.id
  try {
    const attempt = await papersApi.startAttempt(paper.id)
    if (attempt.status === 'doing') {
      openAttempt(attempt.id, paper.id)
    } else {
      openResult(attempt.id)
    }
  } catch (err) {
    ui.error(mapError(err))
  } finally {
    startingPaperId.value = null
  }
}

async function loadHistory(): Promise<void> {
  attemptsLoading.value = true
  attemptsError.value = ''
  try {
    const result = await attemptsApi.mine({ page: 1, page_size: 50 })
    attempts.value = result.list
  } catch (err) {
    attempts.value = []
    attemptsError.value = mapError(err)
  } finally {
    attemptsLoading.value = false
  }
}

async function loadPapers(nextPage = papersPage.value): Promise<void> {
  if (classId.value === null) {
    papers.value = []
    papersTotal.value = 0
    return
  }
  papersLoading.value = true
  papersError.value = ''
  try {
    const result = await papersApi.list(classId.value, {
      page: nextPage,
      page_size: papersPageSize.value,
    })
    papers.value = result.list
    papersTotal.value = result.total
    papersPage.value = result.page
    papersPageSize.value = result.page_size
  } catch (err) {
    papers.value = []
    papersTotal.value = 0
    papersError.value = mapError(err)
  } finally {
    papersLoading.value = false
  }
}

/**
 * 撤回标记要按“全部已发布试卷”判断，不能只看当前分页。
 * 后端 page_size 上限 100；若还有更多页，则不冒险标记已撤回。
 */
async function loadPublishedIndex(): Promise<void> {
  publishedIndexLoaded.value = false
  publishedIndexComplete.value = false
  allPublishedIds.value = new Set()
  if (classId.value === null) {
    publishedIndexLoaded.value = true
    publishedIndexComplete.value = true
    return
  }
  try {
    const result = await papersApi.list(classId.value, { page: 1, page_size: 100 })
    allPublishedIds.value = new Set(result.list.map((paper) => paper.id))
    publishedIndexComplete.value = result.list.length >= result.total
  } catch {
    // 索引失败不把历史成绩误标为“已撤回”；列表本身仍有自己的错误态。
    publishedIndexComplete.value = false
  } finally {
    publishedIndexLoaded.value = true
  }
}

async function reloadAll(): Promise<void> {
  await Promise.all([loadPapers(1), loadHistory(), loadPublishedIndex()])
}

function handlePageChange(nextPage: number, nextSize: number): void {
  papersPageSize.value = nextSize
  papersPage.value = nextPage
  void loadPapers(nextPage)
}

onMounted(reloadAll)
</script>

<template>
  <div class="page student-papers">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">MY PAPERS</p>
        <h1 class="page-title">试卷</h1>
        <p class="page-subtitle">
          老师发布后即可作答。倒计时以服务端截止时间为准，提交后答案不可修改；
          被撤回的试卷会从上方消失，但历史成绩仍保留在下方。
        </p>
      </div>
      <AppButton variant="ghost" :loading="papersLoading || attemptsLoading" @click="reloadAll">
        <RefreshCw v-if="!papersLoading && !attemptsLoading" :size="15" :stroke-width="1.8" />
        刷新
      </AppButton>
    </header>

    <section v-if="student" class="class-banner panel panel-body">
      <div>
        <p class="class-banner__label">当前班级</p>
        <h2 class="class-banner__name">{{ student.class_name || '我的班级' }}</h2>
      </div>
      <dl class="class-banner__meta">
        <div>
          <dt>班级编号</dt>
          <dd class="mono">{{ student.class_code }}</dd>
        </div>
        <div>
          <dt>学号</dt>
          <dd class="mono">{{ student.student_no }}</dd>
        </div>
      </dl>
    </section>

    <section class="paper-section">
      <div class="section-head">
        <div>
          <h2 class="section-title">可作答试卷</h2>
          <p class="section-note">发布中的试卷会出现在这里；点击继续未完成的作答。</p>
        </div>
        <AppTag v-if="papersTotal > 0" tone="primary" dot>{{ papersTotal }} 份</AppTag>
      </div>

      <section v-if="papersLoading" class="student-paper-grid" aria-busy="true">
        <article v-for="index in 3" :key="index" class="panel panel-body">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="4" />
        </article>
      </section>

      <section v-else-if="papersError" class="panel">
        <AppEmpty error title="试卷暂时无法加载" :description="papersError">
          <template #action>
            <AppButton variant="secondary" @click="loadPapers(1)">
              <RefreshCw :size="15" :stroke-width="1.8" />
              重新加载
            </AppButton>
          </template>
        </AppEmpty>
      </section>

      <section v-else-if="papers.length === 0" class="panel">
        <AppEmpty
          title="暂时没有已发布的试卷"
          description="老师发布试卷后会出现在这里；已完成的成绩仍可在下方历史区查看。"
        />
      </section>

      <section v-else class="student-paper-grid">
        <AppCard v-for="paper in papers" :key="paper.id" class="student-paper" padding="md" interactive>
          <header class="student-paper__head">
            <AppTag :tone="paperState(paper).tone" dot>{{ paperState(paper).label }}</AppTag>
            <AppTag v-if="paper.blank_mode === 'strict'" tone="warning">严格判分</AppTag>
            <AppTag v-else tone="neutral">智能判分</AppTag>
          </header>

          <h3 class="student-paper__title">{{ paper.title }}</h3>
          <p class="student-paper__meta">
            {{ paper.question_count }} 题 · {{ paper.total_score }} 分
          </p>

          <dl class="student-paper__info">
            <div>
              <dt><Clock3 :size="13" :stroke-width="1.8" aria-hidden="true" /> 时长</dt>
              <dd class="tabular">
                {{ paper.duration_minutes > 0 ? `${paper.duration_minutes} 分钟` : '不限时' }}
              </dd>
            </div>
            <div>
              <dt>发布</dt>
              <dd>{{ formatDateTime(paper.published_at) }}</dd>
            </div>
          </dl>

          <footer class="student-paper__foot">
            <AppButton
              variant="primary"
              block
              :loading="startingPaperId === paper.id"
              :disabled="startingPaperId !== null"
              @click="startPaper(paper)"
            >
              <CirclePlay v-if="startingPaperId !== paper.id" :size="15" :stroke-width="1.8" />
              {{ attemptOf(paper.id)?.status === 'doing' ? '继续作答' : attemptOf(paper.id) ? '查看成绩' : '开始作答' }}
              <ArrowRight :size="14" :stroke-width="1.9" />
            </AppButton>
          </footer>
        </AppCard>
      </section>

      <AppPagination
        v-if="papersTotal > 0"
        :total="papersTotal"
        :page="papersPage"
        :page-size="papersPageSize"
        @change="handlePageChange"
      />
    </section>

    <section class="history-panel panel">
      <header class="panel-head">
        <div class="split-title">
          <History :size="17" :stroke-width="1.8" aria-hidden="true" />
          <h2 class="section-title">历史成绩</h2>
          <span class="muted text-xs">近 50 份 · 含已撤回试卷</span>
        </div>
        <AppButton variant="ghost" size="sm" :loading="attemptsLoading" @click="loadHistory">
          <RefreshCw v-if="!attemptsLoading" :size="14" :stroke-width="1.8" />
          刷新
        </AppButton>
      </header>

      <p v-if="attemptsError" class="form-error history-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ attemptsError }}</span>
      </p>

      <AppTable
        v-else
        :columns="historyColumns"
        :rows="attempts"
        :loading="attemptsLoading"
        :skeleton-rows="3"
        empty-title="还没有作答记录"
        empty-description="完成第一份试卷后，成绩会在这里留下记录。"
        min-width="640px"
      >
        <template #cell-paper_title="{ row }">
          <div class="history-title">
            <span>{{ row.paper_title || '已删除的试卷' }}</span>
            <AppTag v-if="isWithdrawn(row)" tone="warning">已撤回</AppTag>
          </div>
        </template>
        <template #cell-status="{ row }">
          <AppTag :tone="attemptMeta(row.status).tone" dot>
            {{ attemptMeta(row.status).label }}
          </AppTag>
        </template>
        <template #cell-score="{ row }">
          <span class="tabular history-score">
            {{ row.status === 'doing' ? '—' : `${row.total_score} / ${row.full_score}` }}
          </span>
        </template>
        <template #cell-submitted_at="{ row }">
          <span class="text-sm">{{ formatDateTime(row.submitted_at) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <AppButton
            v-if="row.status === 'doing'"
            variant="secondary"
            size="sm"
            :loading="startingPaperId === row.paper_id"
            @click="openAttempt(row.attempt_id, row.paper_id)"
          >
            继续
          </AppButton>
          <AppButton v-else variant="ghost" size="sm" @click="openResult(row.attempt_id)">
            查看结果
          </AppButton>
        </template>
      </AppTable>
    </section>
  </div>
</template>

<style scoped>
.class-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
  border-color: color-mix(in srgb, var(--color-primary) 22%, var(--color-border));
  background:
    linear-gradient(
      120deg,
      color-mix(in srgb, var(--color-primary-soft) 74%, var(--color-surface)),
      var(--color-surface) 62%);
  flex-wrap: wrap;
}

.class-banner__label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.class-banner__name {
  margin-top: 2px;
  font-size: var(--fs-xl);
  color: var(--color-primary);
}

.class-banner__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
}

.class-banner__meta dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.class-banner__meta dd {
  margin-top: 2px;
  font-size: var(--fs-sm);
}

.paper-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin-bottom: var(--sp-5);
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.section-note {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.student-paper-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-4);
}

.student-paper {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.student-paper__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.student-paper__title {
  font-size: var(--fs-lg);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.student-paper__meta {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.student-paper__info {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.student-paper__info dt {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.student-paper__info dd {
  margin-top: 5px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.student-paper__foot {
  margin-top: auto;
  padding-top: var(--sp-2);
}

.student-paper__foot :deep(.app-button) {
  justify-content: space-between;
}

.history-panel {
  overflow: hidden;
}

.history-error {
  margin: var(--sp-4) var(--sp-5);
}

.history-title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
  font-weight: 600;
}

.history-score {
  font-weight: 600;
}

.history-panel :deep(.app-pagination) {
  border-top: 1px solid var(--color-border);
}

@media (max-width: 1023px) {
  .student-paper-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .student-paper-grid {
    grid-template-columns: 1fr;
  }
}
</style>
