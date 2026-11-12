<!-- 教师试卷详情：试卷设置、题目清单、发布/撤回、成绩表与逐题复核入口。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  PencilLine,
  RefreshCw,
  Send,
  Undo2,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import ReviewDrawer from '@/components/business/ReviewDrawer.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { papersApi } from '@/api/papers'
import { useUiStore } from '@/stores/ui'
import {
  ATTEMPT_STATUS_META,
  BLANK_MODE_META,
  DIFFICULTY_META,
  PAGE_SIZE,
  PAPER_MODE_LABEL,
  PAPER_STATUS_META,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import { formatAnswer } from '@/utils/questions'
import { formatDateTime } from '@/utils/format'
import type {
  AttemptStatus,
  BlankMode,
  PaperAttemptItem,
  PaperDetail,
  PaperQuestion,
} from '@/api/types'
import type { SelectOption, TableColumn } from '@/types'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()

const paperId = Number(route.params.id)
const paper = ref<PaperDetail | null>(null)
const loading = ref(false)
const error = ref('')

const attempts = ref<PaperAttemptItem[]>([])
const attemptsTotal = ref(0)
const attemptsPage = ref(1)
const attemptsPageSize = ref(PAGE_SIZE)
const attemptsLoading = ref(false)
const attemptsError = ref('')

const reviewOpen = ref(false)
const reviewAttemptId = ref<number | null>(null)
const reviewStudent = ref('')

const actionOpen = ref(false)
const actionKind = ref<'publish' | 'withdraw'>('publish')
const actioning = ref(false)
const actionError = ref('')

const editOpen = ref(false)
const editTitle = ref('')
const editDuration = ref(0)
const editBlankMode = ref<BlankMode>('smart')
const savingEdit = ref(false)
const editError = ref('')

const columns: TableColumn[] = [
  { key: 'student', title: '学生', width: '180px' },
  { key: 'student_no', title: '学号', width: '120px' },
  { key: 'status', title: '状态', width: '100px' },
  { key: 'score', title: '得分', width: '100px', align: 'right' },
  { key: 'needs_review', title: '待复核', width: '90px', align: 'right' },
  { key: 'submitted_at', title: '提交时间', width: '160px' },
  { key: 'actions', title: '操作', width: '88px', align: 'right' },
]

const blankModeOptions: SelectOption[] = (
  Object.keys(BLANK_MODE_META) as BlankMode[]
).map((value) => ({ value, label: BLANK_MODE_META[value].label }))

const statusMeta = computed(() =>
  paper.value ? PAPER_STATUS_META[paper.value.status] : null,
)
const blankMeta = computed(() =>
  paper.value ? BLANK_MODE_META[paper.value.blank_mode] : null,
)
const canEdit = computed(() => Boolean(paper.value && paper.value.status !== 'published'))
const canPublish = computed(() => Boolean(paper.value && paper.value.status !== 'published'))
const canWithdraw = computed(() => paper.value?.status === 'published')

const actionTitle = computed(() =>
  actionKind.value === 'publish' ? '发布这份试卷？' : '撤回这份试卷？',
)
const actionDescription = computed(() =>
  actionKind.value === 'publish'
    ? '发布后学生可在试卷列表中看到并开始作答；已作答的学生不受影响。'
    : '撤回后学生列表立即隐藏；已完成的历史成绩仍保留，可继续打开查看。',
)
const actionConfirmText = computed(() =>
  actionKind.value === 'publish' ? '确认发布' : '确认撤回',
)

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  if (isApiError(err) && err.code === 40401) return '试卷不存在或已被删除'
  return toUserMessage(err)
}

function attemptMeta(status: AttemptStatus) {
  return ATTEMPT_STATUS_META[status] ?? ATTEMPT_STATUS_META.doing
}

function answerText(question: PaperQuestion): string {
  return formatAnswer(question.answer, question.type, question.options)
}

async function loadAttemptsPage(nextPage: number, silent = false): Promise<void> {
  if (!paper.value) return
  if (!silent) attemptsLoading.value = true
  attemptsError.value = ''
  try {
    const result = await papersApi.attempts(paper.value.id, {
      page: nextPage,
      page_size: attemptsPageSize.value,
    })
    attempts.value = result.list
    attemptsTotal.value = result.total
    attemptsPage.value = result.page
    attemptsPageSize.value = result.page_size
  } catch (err) {
    attempts.value = []
    attemptsTotal.value = 0
    attemptsError.value = toUserMessage(err)
  } finally {
    attemptsLoading.value = false
  }
}

async function loadPaper(): Promise<void> {
  loading.value = true
  error.value = ''
  paper.value = null
  attempts.value = []
  attemptsTotal.value = 0
  if (!Number.isFinite(paperId) || paperId <= 0) {
    error.value = '试卷地址无效'
    loading.value = false
    return
  }
  try {
    paper.value = await papersApi.detail(paperId)
    await loadAttemptsPage(1)
  } catch (err) {
    paper.value = null
    error.value = mapError(err)
  } finally {
    loading.value = false
  }
}

function backToPapers(): void {
  void router.push({
    path: '/teacher/papers',
    query: paper.value ? { class_id: String(paper.value.class_id) } : undefined,
  })
}

function handleAttemptsPage(nextPage: number, nextSize: number): void {
  attemptsPageSize.value = nextSize
  attemptsPage.value = nextPage
  void loadAttemptsPage(nextPage)
}

function askAction(kind: 'publish' | 'withdraw'): void {
  actionKind.value = kind
  actionError.value = ''
  actionOpen.value = true
}

async function confirmAction(): Promise<void> {
  if (!paper.value || actioning.value) return
  actioning.value = true
  actionError.value = ''
  try {
    if (actionKind.value === 'publish') {
      paper.value = await papersApi.publish(paper.value.id)
      ui.success('试卷已发布，学生现在可以作答')
    } else {
      paper.value = await papersApi.withdraw(paper.value.id)
      ui.success('试卷已撤回')
    }
    actionOpen.value = false
  } catch (err) {
    actionError.value = mapError(err)
  } finally {
    actioning.value = false
  }
}

function openEdit(): void {
  if (!paper.value) return
  editTitle.value = paper.value.title
  editDuration.value = paper.value.duration_minutes
  editBlankMode.value = paper.value.blank_mode
  editError.value = ''
  editOpen.value = true
}

async function saveEdit(): Promise<void> {
  if (!paper.value || savingEdit.value) return
  const title = editTitle.value.trim()
  const duration = Number(editDuration.value)
  if (!title) {
    editError.value = '试卷标题不能为空'
    return
  }
  if (title.length > 200) {
    editError.value = '试卷标题不能超过 200 字'
    return
  }
  if (!Number.isFinite(duration) || duration < 0) {
    editError.value = '作答时长需为不小于 0 的整数'
    return
  }
  savingEdit.value = true
  editError.value = ''
  try {
    paper.value = await papersApi.update(paper.value.id, {
      title,
      duration_minutes: Math.floor(duration),
      blank_mode: editBlankMode.value,
    })
    editOpen.value = false
    ui.success('试卷设置已更新')
  } catch (err) {
    editError.value = mapError(err)
  } finally {
    savingEdit.value = false
  }
}

function openReview(attempt: PaperAttemptItem): void {
  reviewAttemptId.value = attempt.attempt_id
  reviewStudent.value = attempt.student_name || attempt.student_no || '学生'
  reviewOpen.value = true
}

async function handleReviewed(): Promise<void> {
  ui.success('复核分数已保存')
  await loadAttemptsPage(attemptsPage.value, true)
}

onMounted(loadPaper)
</script>

<template>
  <div class="page paper-detail">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">PAPER DETAIL</p>
        <div class="split-title">
          <h1 class="page-title">{{ paper?.title || (loading ? '加载中…' : '试卷详情') }}</h1>
          <AppTag v-if="statusMeta" :tone="statusMeta.tone" dot>{{ statusMeta.label }}</AppTag>
        </div>
        <p class="page-subtitle">
          发布前可调整标题、时长与判分严格度；发布后内容锁定，学生作答与成绩会实时汇总到这里。
        </p>
        <div v-if="paper?.banks?.length" class="paper-banks" aria-label="来源题库">
          <span class="paper-banks__label">来源题库</span>
          <AppTag v-for="bank in paper.banks" :key="bank.id" tone="primary">{{ bank.name }}</AppTag>
        </div>
      </div>
      <div class="page-actions">
        <AppButton variant="ghost" @click="backToPapers">
          <ArrowLeft :size="15" :stroke-width="1.9" />
          返回试卷
        </AppButton>
        <AppButton v-if="canEdit" variant="secondary" @click="openEdit">
          <PencilLine :size="15" :stroke-width="1.8" />
          编辑设置
        </AppButton>
        <AppButton v-if="canPublish" variant="primary" @click="askAction('publish')">
          <Send :size="15" :stroke-width="1.9" />
          {{ paper?.status === 'closed' ? '重新发布' : '发布试卷' }}
        </AppButton>
        <AppButton v-if="canWithdraw" variant="danger-outline" @click="askAction('withdraw')">
          <Undo2 :size="15" :stroke-width="1.8" />
          撤回
        </AppButton>
      </div>
    </header>

    <section v-if="loading" class="content-stack" aria-busy="true">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="5" />
      </div>
    </section>

    <section v-else-if="error" class="panel">
      <AppEmpty error title="试卷暂时无法加载" :description="error">
        <template #action>
          <AppButton variant="secondary" @click="loadPaper">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <template v-else-if="paper">
      <section class="paper-overview panel panel-body">
        <dl class="overview-grid">
          <div>
            <dt>组卷方式</dt>
            <dd>{{ PAPER_MODE_LABEL[paper.mode] }}</dd>
          </div>
          <div>
            <dt>题量</dt>
            <dd class="tabular">{{ paper.question_count }} 题</dd>
          </div>
          <div>
            <dt>总分</dt>
            <dd class="tabular">{{ paper.total_score }} 分</dd>
          </div>
          <div>
            <dt>作答时长</dt>
            <dd class="tabular">
              <Clock3 :size="13" :stroke-width="1.8" aria-hidden="true" />
              {{ paper.duration_minutes > 0 ? `${paper.duration_minutes} 分钟` : '不限时' }}
            </dd>
          </div>
          <div>
            <dt>判分严格度</dt>
            <dd>{{ blankMeta?.label }}</dd>
          </div>
          <div>
            <dt>题目顺序</dt>
            <dd>{{ paper.shuffle ? '乱序' : '固定' }}</dd>
          </div>
          <div>
            <dt>创建时间</dt>
            <dd>{{ formatDateTime(paper.created_at) }}</dd>
          </div>
          <div>
            <dt>发布时间</dt>
            <dd>{{ formatDateTime(paper.published_at) }}</dd>
          </div>
        </dl>
        <p class="overview-note">
          <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
          学生开卷即开始计时；提交或倒计时归零后锁卷。待复核题不会向学生展示确定分数。
        </p>
      </section>

      <section class="panel">
        <header class="panel-head">
          <div class="split-title">
            <h2 class="section-title">试卷题目</h2>
            <span class="muted text-xs">{{ paper.questions.length }} 题 · 每题 1 分</span>
          </div>
          <AppTag tone="neutral" dot>教师视角 · 含标准答案</AppTag>
        </header>
        <div class="panel-body paper-questions">
          <AppEmpty
            v-if="paper.questions.length === 0"
            title="这份试卷还没有题目"
            description="返回试卷列表重新组卷。"
            compact
          />
          <details
            v-for="question in paper.questions"
            :key="question.id"
            class="paper-question"
          >
            <summary class="paper-question__summary">
              <span class="paper-question__seq mono tabular">{{ String(question.seq).padStart(2, '0') }}</span>
              <AppTag :tone="QUESTION_TYPE_META[question.type].tone">
                {{ QUESTION_TYPE_META[question.type].short }}
              </AppTag>
              <span class="paper-question__stem">{{ question.stem }}</span>
              <span class="paper-question__score tabular">{{ question.score }} 分</span>
            </summary>
            <div class="paper-question__body">
              <ol v-if="question.options?.length" class="paper-question__options">
                <li v-for="option in question.options" :key="option.key">
                  <span class="mono">{{ option.key }}</span>
                  {{ option.text }}
                </li>
              </ol>
              <dl class="paper-question__meta">
                <div>
                  <dt>标准答案</dt>
                  <dd>{{ answerText(question) }}</dd>
                </div>
                <div v-if="question.analysis">
                  <dt>解析</dt>
                  <dd>{{ question.analysis }}</dd>
                </div>
                <div>
                  <dt>知识点 / 难度</dt>
                  <dd>
                    {{ question.knowledge_tag }} ·
                    {{ DIFFICULTY_META[question.difficulty].label }}
                  </dd>
                </div>
              </dl>
            </div>
          </details>
        </div>
      </section>

      <section class="panel">
        <header class="panel-head">
          <div class="split-title">
            <h2 class="section-title">成绩表</h2>
            <span class="muted text-xs">共 {{ attemptsTotal }} 份作答</span>
          </div>
          <AppButton variant="ghost" size="sm" :loading="attemptsLoading" @click="loadAttemptsPage(attemptsPage)">
            <RefreshCw :size="14" :stroke-width="1.8" />
            刷新成绩
          </AppButton>
        </header>

        <p v-if="attemptsError" class="form-error attempts-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ attemptsError }}</span>
        </p>

        <AppTable
          class="attempts-table"
          :columns="columns"
          :rows="attempts"
          :loading="attemptsLoading"
          :skeleton-rows="4"
          empty-title="还没有学生作答"
          empty-description="试卷发布后，学生的提交会出现在这里。"
          min-width="840px"
        >
          <template #cell-student="{ row }">
            <div class="student-cell">
              <span class="student-cell__avatar">{{ (row.student_name || '?').slice(0, 1) }}</span>
              <strong>{{ row.student_name || '未知学生' }}</strong>
            </div>
          </template>
          <template #cell-student_no="{ row }">
            <span class="mono">{{ row.student_no || '—' }}</span>
          </template>
          <template #cell-status="{ row }">
            <AppTag :tone="attemptMeta(row.status).tone" dot>{{ attemptMeta(row.status).label }}</AppTag>
          </template>
          <template #cell-score="{ row }">
            <span class="tabular score-cell">{{ row.total_score }} / {{ row.full_score }}</span>
          </template>
          <template #cell-needs_review="{ row }">
            <AppTag v-if="row.needs_review_count > 0" tone="accent" dot class="tabular">
              {{ row.needs_review_count }} 题
            </AppTag>
            <span v-else class="muted text-xs tabular">—</span>
          </template>
          <template #cell-submitted_at="{ row }">
            <span class="text-sm time-cell">{{ formatDateTime(row.submitted_at) }}</span>
          </template>
          <template #cell-actions="{ row }">
            <AppButton
              v-if="row.status !== 'doing'"
              variant="secondary"
              size="sm"
              @click="openReview(row)"
            >
              <UsersRound :size="14" :stroke-width="1.8" />
              复核
            </AppButton>
            <span v-else class="muted text-xs">未提交</span>
          </template>
        </AppTable>

        <AppPagination
          v-if="attemptsTotal > 0"
          :total="attemptsTotal"
          :page="attemptsPage"
          :page-size="attemptsPageSize"
          @change="handleAttemptsPage"
        />
      </section>
    </template>

    <ReviewDrawer
      v-model="reviewOpen"
      :attempt-id="reviewAttemptId"
      :student-name="reviewStudent"
      @reviewed="handleReviewed"
    />

    <AppModal
      v-model="actionOpen"
      :title="actionTitle"
      :description="actionDescription"
      :confirm-text="actionConfirmText"
      :confirm-variant="actionKind === 'withdraw' ? 'danger' : 'primary'"
      :confirm-loading="actioning"
      @confirm="confirmAction"
    >
      <p v-if="paper" class="action-target">
        {{ paper.title }} · {{ paper.question_count }} 题 · {{ paper.total_score }} 分
      </p>
      <p v-if="actionKind === 'publish'" class="action-note">
        <CheckCircle2 :size="14" :stroke-width="1.9" aria-hidden="true" />
        发布后仍可撤回；已产生的成绩不会删除。
      </p>
      <p v-if="actionError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ actionError }}</span>
      </p>
    </AppModal>

    <AppModal
      v-model="editOpen"
      title="编辑试卷设置"
      description="仅草稿或已撤回的试卷可以修改；题目内容需重新组卷调整。"
      confirm-text="保存设置"
      :confirm-loading="savingEdit"
      @confirm="saveEdit"
    >
      <div class="edit-form">
        <label class="field">
          <span class="field__label">试卷标题</span>
          <input v-model="editTitle" class="field__input" type="text" maxlength="200" :disabled="savingEdit" />
        </label>
        <label class="field">
          <span class="field__label">作答时长（分钟，0 为不限时）</span>
          <input
            v-model.number="editDuration"
            class="field__input tabular"
            type="number"
            min="0"
            step="1"
            :disabled="savingEdit"
          />
        </label>
        <AppSelect
          v-model="editBlankMode"
          label="填空判分严格度"
          :options="blankModeOptions"
          :disabled="savingEdit"
        />
        <p v-if="editError" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ editError }}</span>
        </p>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.paper-banks {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  flex-wrap: wrap;
  margin-top: var(--sp-2);
}

.paper-banks__label {
  margin-right: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-overview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-3);
}

.overview-grid dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.overview-grid dd {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.overview-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-top: var(--sp-3);
  border-top: 1px dashed var(--color-border);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.overview-note svg {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--color-warning);
}

.paper-questions {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.paper-question {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.paper-question[open] {
  border-color: var(--color-border-strong);
}

.paper-question__summary {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  cursor: pointer;
  list-style: none;
}

.paper-question__summary::-webkit-details-marker {
  display: none;
}

.paper-question__seq {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-question__stem {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.paper-question__score {
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.paper-question__body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: 0 var(--sp-4) var(--sp-4) 52px;
}

.paper-question__options {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.paper-question__options li {
  display: flex;
  gap: var(--sp-2);
}

.paper-question__meta {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3);
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
}

.paper-question__meta dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-question__meta dd {
  margin-top: 1px;
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.paper-question__meta > div:first-child dd {
  color: var(--color-success);
}

.attempts-table :deep(table) {
  table-layout: fixed;
}

.attempts-table :deep(td) {
  vertical-align: middle;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
}

.student-cell strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.student-cell__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.score-cell {
  font-weight: 600;
}

.time-cell {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.attempts-error {
  margin: var(--sp-3) var(--sp-5) 0;
}

.action-target {
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  font-size: var(--fs-sm);
}

.action-note {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: var(--sp-2);
  color: var(--color-success);
  font-size: var(--fs-xs);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field__label {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.field__input {
  width: 100%;
  min-height: 40px;
  padding: 9px var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
}

.field__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

@media (max-width: 1023px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
