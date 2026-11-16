<script setup lang="ts">
// 工作台「学生状态」：用现有 papers/students/attempts 前端聚合，不新增接口。
import { computed, ref, watch } from 'vue'
import { FileText, Filter } from 'lucide-vue-next'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { classesApi } from '@/api/classes'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { PaperAttemptItem, PaperItem, StudentListItem } from '@/api/contract'
import { formatDateTime, formatScore } from '@/utils/format'

const props = defineProps<{ classId: number | null }>()

type StatusKey = 'not_started' | 'doing' | 'submitted' | 'graded'

interface StatusRow {
  student: StudentListItem
  attempt: PaperAttemptItem | null
  status: StatusKey
}

const STATUS_LABEL: Record<StatusKey, string> = {
  not_started: '未开始',
  doing: '进行中',
  submitted: '待复核',
  graded: '已复核',
}

const STATUS_TONE: Record<StatusKey, 'plain' | 'lime' | 'amber'> = {
  not_started: 'plain',
  doing: 'plain',
  submitted: 'amber',
  graded: 'lime',
}

const exams = ref<PaperItem[]>([])
const selectedExamId = ref('')
const statusFilter = ref<'' | StatusKey>('')
const students = ref<StudentListItem[]>([])
const attempts = ref<PaperAttemptItem[]>([])
const loadingExams = ref(false)
const loadingRows = ref(false)
const loadError = ref('')
const page = ref(1)
const PAGE_SIZE = 10

let examsSeq = 0
let rowsSeq = 0

const examOptions = computed(() =>
  exams.value.map((paper) => ({ label: paper.title, value: String(paper.id) })),
)

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '未开始', value: 'not_started' },
  { label: '进行中', value: 'doing' },
  { label: '待复核', value: 'submitted' },
  { label: '已复核', value: 'graded' },
]

const loading = computed(() => loadingExams.value || loadingRows.value)

/** 同一学生多次作答时取最新一次（attempt_id 最大）。 */
const rows = computed<StatusRow[]>(() => {
  const byStudent = new Map<number, PaperAttemptItem>()
  attempts.value.forEach((attempt) => {
    const previous = byStudent.get(attempt.student_id)
    if (!previous || attempt.attempt_id > previous.attempt_id) byStudent.set(attempt.student_id, attempt)
  })
  return students.value.map((student) => {
    const attempt = byStudent.get(student.id) ?? null
    const status: StatusKey = !attempt
      ? 'not_started'
      : attempt.status === 'doing'
        ? 'doing'
        : attempt.status === 'submitted'
          ? 'submitted'
          : 'graded'
    return { student, attempt, status }
  })
})

const filteredRows = computed(() =>
  statusFilter.value ? rows.value.filter((row) => row.status === statusFilter.value) : rows.value,
)

const pagedRows = computed(() =>
  filteredRows.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
)

const emptyText = computed(() => {
  if (exams.value.length === 0) return '还没有考试；发布一场考试后这里会出现学生状态。'
  if (students.value.length === 0) return '这个班级还没有学生。'
  if (filteredRows.value.length === 0 && statusFilter.value) {
    return `没有符合「${STATUS_LABEL[statusFilter.value]}」的学生。`
  }
  return ''
})

async function fetchAllStudents(classId: number, token: number): Promise<StudentListItem[]> {
  const result: StudentListItem[] = []
  for (let current = 1; current <= 10; current += 1) {
    const pageResult = await classesApi.students(classId, { page: current, page_size: 50 })
    if (token !== rowsSeq) return result
    result.push(...pageResult.list)
    if (result.length >= pageResult.total || pageResult.list.length === 0) break
  }
  return result
}

async function fetchAllAttempts(paperId: number, token: number): Promise<PaperAttemptItem[]> {
  const result: PaperAttemptItem[] = []
  for (let current = 1; current <= 10; current += 1) {
    const pageResult = await papersApi.attempts(paperId, { page: current, page_size: 50 })
    if (token !== rowsSeq) return result
    result.push(...pageResult.list)
    if (result.length >= pageResult.total || pageResult.list.length === 0) break
  }
  return result
}

async function loadRows(): Promise<void> {
  const classId = props.classId
  const paperId = Number(selectedExamId.value)
  const token = ++rowsSeq
  students.value = []
  attempts.value = []
  page.value = 1
  loadError.value = ''
  if (!classId || !paperId) return
  loadingRows.value = true
  try {
    const [studentList, attemptList] = await Promise.all([
      fetchAllStudents(classId, token),
      fetchAllAttempts(paperId, token),
    ])
    if (token !== rowsSeq) return
    students.value = studentList
    attempts.value = attemptList
  } catch (error) {
    if (token === rowsSeq) loadError.value = toUserMessage(error)
  } finally {
    if (token === rowsSeq) loadingRows.value = false
  }
}

async function loadExams(): Promise<void> {
  const classId = props.classId
  const token = ++examsSeq
  exams.value = []
  selectedExamId.value = ''
  students.value = []
  attempts.value = []
  loadError.value = ''
  page.value = 1
  if (!classId) return
  loadingExams.value = true
  try {
    const result = await papersApi.list(classId, { page: 1, page_size: 50 })
    if (token !== examsSeq) return
    exams.value = result.list
      .filter((paper) => paper.kind === 'exam' && paper.status !== 'draft')
      .sort(
        (a, b) =>
          new Date(b.published_at ?? b.created_at).getTime() -
          new Date(a.published_at ?? a.created_at).getTime(),
      )
    if (exams.value.length > 0) selectedExamId.value = String(exams.value[0].id)
  } catch (error) {
    if (token === examsSeq) loadError.value = toUserMessage(error)
  } finally {
    if (token === examsSeq) loadingExams.value = false
  }
}

function retry(): void {
  if (exams.value.length === 0) void loadExams()
  else void loadRows()
}

watch(
  () => props.classId,
  () => {
    ++rowsSeq
    void loadExams()
  },
  { immediate: true },
)

watch(selectedExamId, () => {
  void loadRows()
})

watch(statusFilter, () => {
  page.value = 1
})
</script>

<template>
  <section class="card">
    <header class="card__head">
      <div class="status-head">
        <h2>学生状态</h2>
        <span class="card__meta">共 {{ students.length }} 人</span>
      </div>
      <div v-if="exams.length > 0" class="status-filters">
        <BaseSelect
          v-model="selectedExamId"
          class="status-select"
          :options="examOptions"
          :icon="FileText"
          size="sm"
          aria-label="选择考试"
        />
        <BaseSelect
          v-model="statusFilter"
          class="status-select"
          :options="statusOptions"
          :icon="Filter"
          size="sm"
          aria-label="按状态筛选"
        />
      </div>
    </header>

    <BaseSkeleton v-if="loading" class="stack" :count="3" height="30px" />

    <div v-else-if="loadError" class="notice notice--danger">
      {{ loadError }}
      <BaseButton size="sm" style="margin-left: 8px" @click="retry">重试</BaseButton>
    </div>

    <p v-else-if="filteredRows.length === 0" class="empty-block">
      <span>{{ emptyText }}</span>
    </p>

    <template v-else>
      <div class="table-wrap">
        <table class="table status-table">
          <thead>
            <tr>
              <th>学生</th>
              <th>学号</th>
              <th>状态</th>
              <th class="num">得分</th>
              <th>提交时间</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pagedRows" :key="row.student.id">
              <td><strong>{{ row.student.name }}</strong></td>
              <td class="tertiary">{{ row.student.student_no }}</td>
              <td>
                <BaseBadge :tone="STATUS_TONE[row.status]">{{ STATUS_LABEL[row.status] }}</BaseBadge>
              </td>
              <td class="num">
                {{
                  row.attempt
                    ? `${formatScore(row.attempt.total_score)} / ${formatScore(row.attempt.full_score)}`
                    : '—'
                }}
              </td>
              <td class="tertiary">
                {{ row.attempt ? formatDateTime(row.attempt.submitted_at) : '—' }}
              </td>
              <td>
                <div class="actions">
                  <RouterLink
                    v-if="row.status === 'submitted'"
                    class="btn btn--sm"
                    :to="`/teacher/attempts/${row.attempt?.attempt_id}/result`"
                  >
                    去批改
                  </RouterLink>
                  <RouterLink
                    v-else-if="row.status === 'graded'"
                    class="btn btn--sm"
                    :to="`/teacher/attempts/${row.attempt?.attempt_id}/result`"
                  >
                    查看
                  </RouterLink>
                  <span v-else-if="row.status === 'doing'" class="small tertiary">作答中</span>
                  <span v-else class="tertiary">—</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        :page="page"
        :page-size="PAGE_SIZE"
        :total="filteredRows.length"
        @change="page = $event"
      />
    </template>
  </section>
</template>

<style scoped>
.status-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.status-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-select {
  width: 172px;
  max-width: 100%;
}

/* 375 窄屏：表格保持可读宽度，在 table-wrap 内横向滚动。 */
.status-table {
  min-width: 620px;
}

@media (max-width: 640px) {
  .status-select {
    width: 100%;
  }
}
</style>
