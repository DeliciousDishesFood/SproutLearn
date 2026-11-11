<!-- 教师题库：班级切换、导入预览、四维筛选、题目卡片、编辑/删除/讲评。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  Plus,
  RefreshCw,
  Search,
  UploadCloud,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppCard from '@/components/base/AppCard.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import QuestionCard from '@/components/business/QuestionCard.vue'
import QuestionEditDrawer from '@/components/business/QuestionEditDrawer.vue'
import QuestionExplainModal from '@/components/business/QuestionExplainModal.vue'
import QuestionImportPanel from '@/components/business/QuestionImportPanel.vue'
import { questionsApi } from '@/api/questions'
import { isApiError, toUserMessage } from '@/api/client'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import {
  DIFFICULTY_META,
  PAGE_SIZE,
  QUESTION_STATUS_META,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import type {
  QuestionDifficulty,
  QuestionItem,
  QuestionStatus,
  QuestionType,
} from '@/api/types'
import type { SelectOption } from '@/types'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

interface QuestionFilters {
  type: string
  tag: string
  difficulty: string
  status: string
  keyword: string
}

function emptyFilters(): QuestionFilters {
  return { type: '', tag: '', difficulty: '', status: '', keyword: '' }
}

const selectedClassId = ref('')
const filters = ref<QuestionFilters>(emptyFilters())
const keywordDraft = ref('')
const questions = ref<QuestionItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const loading = ref(false)
const loadError = ref('')
const classErroring = ref(false)

const importOpen = ref(false)
const editOpen = ref(false)
const editTarget = ref<QuestionItem | null>(null)
const explainOpen = ref(false)
const explainTarget = ref<QuestionItem | null>(null)
const deleteOpen = ref(false)
const deleteTarget = ref<QuestionItem | null>(null)
const deleting = ref(false)
const deleteError = ref('')

const classOptions = computed(() =>
  classStore.classes.map((item) => ({
    label: `${item.class_name} · ${item.course_name}`,
    value: String(item.id),
  })),
)

const typeOptions: SelectOption[] = [
  { label: '全部题型', value: '' },
  ...(Object.keys(QUESTION_TYPE_META) as QuestionType[]).map((value) => ({
    label: QUESTION_TYPE_META[value].label,
    value,
  })),
]
const difficultyOptions: SelectOption[] = [
  { label: '全部难度', value: '' },
  ...(Object.keys(DIFFICULTY_META) as QuestionDifficulty[]).map((value) => ({
    label: DIFFICULTY_META[value].label,
    value,
  })),
]
const statusOptions: SelectOption[] = [
  { label: '全部状态', value: '' },
  ...(Object.keys(QUESTION_STATUS_META) as QuestionStatus[]).map((value) => ({
    label: QUESTION_STATUS_META[value].label,
    value,
  })),
]

const hasFilters = computed(() => {
  const current = filters.value
  return Boolean(
    current.type || current.tag || current.difficulty || current.status || current.keyword,
  )
})
const currentClass = computed(
  () => classStore.classes.find((item) => String(item.id) === selectedClassId.value) ?? null,
)
const questionBankEmpty = computed(
  () => !loading.value && !loadError.value && questions.value.length === 0,
)

function syncClassQuery(): void {
  void router.replace({
    query: {
      ...route.query,
      class_id: selectedClassId.value,
    },
  })
}

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

async function loadQuestions(nextPage = page.value, silent = false): Promise<void> {
  if (!selectedClassId.value) return
  if (!silent) loading.value = true
  loadError.value = ''
  try {
    const result = await questionsApi.list(Number(selectedClassId.value), {
      type: filters.value.type ? (filters.value.type as QuestionType) : undefined,
      knowledge_tag: filters.value.tag || undefined,
      difficulty: filters.value.difficulty
        ? (filters.value.difficulty as QuestionDifficulty)
        : undefined,
      status: filters.value.status ? (filters.value.status as QuestionStatus) : undefined,
      keyword: filters.value.keyword || undefined,
      page: nextPage,
      page_size: pageSize.value,
    })
    questions.value = result.list
    total.value = result.total
    page.value = result.page
    pageSize.value = result.page_size
  } catch (err) {
    loadError.value = mapError(err)
    questions.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function bootstrap(): Promise<void> {
  classErroring.value = false
  try {
    await classStore.fetchAllClasses()
  } catch {
    classErroring.value = true
    return
  }
  if (classStore.classes.length === 0) return
  const queryId = Number(route.query.class_id)
  const matched = classStore.classes.find((item) => item.id === queryId)
  selectedClassId.value = String(matched ? matched.id : classStore.classes[0].id)
  if (!matched) syncClassQuery()
  await loadQuestions(1)
}

function handleClassChange(value: string): void {
  if (value === selectedClassId.value) return
  selectedClassId.value = value
  filters.value = emptyFilters()
  keywordDraft.value = ''
  questions.value = []
  total.value = 0
  page.value = 1
  loadError.value = ''
  syncClassQuery()
  void loadQuestions(1)
}

function applyFilter(patch: Partial<QuestionFilters>): void {
  filters.value = { ...filters.value, ...patch }
  page.value = 1
  void loadQuestions(1)
}

function applyKeyword(): void {
  const keyword = keywordDraft.value.trim()
  if (keyword === filters.value.keyword) return
  applyFilter({ keyword })
}

function resetFilters(): void {
  filters.value = emptyFilters()
  keywordDraft.value = ''
  page.value = 1
  void loadQuestions(1)
}

function handlePageChange(nextPage: number, nextSize: number): void {
  pageSize.value = nextSize
  page.value = nextPage
  void loadQuestions(nextPage)
}

function openImport(): void {
  if (!selectedClassId.value) return
  importOpen.value = true
}

async function handleImported(count: number): Promise<void> {
  ui.success(`已导入 ${count} 道题目，均为草稿状态`)
  filters.value = emptyFilters()
  keywordDraft.value = ''
  await loadQuestions(1)
}

function openEdit(question: QuestionItem): void {
  editTarget.value = question
  editOpen.value = true
}

async function handleEdited(): Promise<void> {
  editOpen.value = false
  editTarget.value = null
  ui.success('题目已更新')
  await loadQuestions(page.value)
}

function openExplain(question: QuestionItem): void {
  explainTarget.value = question
  explainOpen.value = true
}

function askDelete(question: QuestionItem): void {
  deleteTarget.value = question
  deleteError.value = ''
  deleteOpen.value = true
}

async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await questionsApi.remove(deleteTarget.value.id)
    ui.success('题目已删除')
    deleteOpen.value = false
    deleteTarget.value = null
    if (questions.value.length === 1 && page.value > 1) page.value -= 1
    await loadQuestions(page.value)
  } catch (err) {
    deleteError.value = mapError(err)
  } finally {
    deleting.value = false
  }
}

onMounted(bootstrap)
</script>

<template>
  <div class="page question-bank">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">QUESTION BANK</p>
        <h1 class="page-title">题库</h1>
        <p class="page-subtitle">
          导入题目、按知识点筛选，再从这里挑题组卷。导入的题目先以草稿保存，不会影响已发布试卷。
        </p>
      </div>
      <AppButton variant="primary" :disabled="!selectedClassId" @click="openImport">
        <UploadCloud :size="16" :stroke-width="1.9" />
        导入题目
      </AppButton>
    </header>

    <section v-if="classErroring" class="panel">
      <AppEmpty error title="班级列表暂时无法加载" description="请检查网络后重新加载页面">
        <template #action>
          <AppButton variant="secondary" @click="bootstrap">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重试
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <section v-else-if="classStore.classes.length === 0" class="panel">
      <AppEmpty
        title="还没有可维护的班级"
        description="题库按班级隔离。先创建班级，再导入本班题目。"
      >
        <template #action>
          <router-link to="/teacher/classes">
            <AppButton variant="primary">
              <Plus :size="15" :stroke-width="1.9" />
              去我的班级
            </AppButton>
          </router-link>
        </template>
      </AppEmpty>
    </section>

    <template v-else>
      <section class="question-toolbar panel">
        <div class="question-toolbar__row">
          <AppSelect
            :model-value="selectedClassId"
            label="当前班级"
            :options="classOptions"
            class="class-select"
            @update:model-value="handleClassChange"
          />
          <div class="question-toolbar__summary">
            <span class="muted text-xs">题库容量</span>
            <strong class="tabular">{{ total }}</strong>
            <span class="muted text-xs">道题</span>
          </div>
        </div>
      </section>

      <section class="filter-bar panel" aria-label="题库筛选">
        <div class="filter-grid">
          <AppSelect
            :model-value="filters.type"
            label="题型"
            :options="typeOptions"
            @update:model-value="(value) => applyFilter({ type: value })"
          />
          <AppSelect
            :model-value="filters.difficulty"
            label="难度"
            :options="difficultyOptions"
            @update:model-value="(value) => applyFilter({ difficulty: value })"
          />
          <AppSelect
            :model-value="filters.status"
            label="状态"
            :options="statusOptions"
            @update:model-value="(value) => applyFilter({ status: value })"
          />
          <AppInput
            :model-value="filters.tag"
            label="知识点标签"
            placeholder="精确匹配，如 传输层"
            @update:model-value="(value) => applyFilter({ tag: value })"
          />
        </div>

        <div class="filter-search">
          <AppInput
            v-model="keywordDraft"
            label="关键词"
            placeholder="搜索题干或解析"
            @keydown.enter.prevent="applyKeyword"
          />
          <AppButton variant="secondary" @click="applyKeyword">
            <Search :size="15" :stroke-width="1.9" />
            搜索
          </AppButton>
          <AppButton v-if="hasFilters" variant="ghost" @click="resetFilters">清除筛选</AppButton>
        </div>
      </section>

      <section v-if="loading" class="question-grid" aria-busy="true">
        <AppCard v-for="index in 4" :key="index" padding="md">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="4" />
        </AppCard>
      </section>

      <section v-else-if="loadError" class="panel">
        <AppEmpty error title="题库暂时无法加载" :description="loadError">
          <template #action>
            <AppButton variant="secondary" @click="loadQuestions(page, false)">
              <RefreshCw :size="15" :stroke-width="1.8" />
              重新加载
            </AppButton>
          </template>
        </AppEmpty>
      </section>

      <section v-else-if="questions.length === 0" class="panel">
        <AppEmpty
          :title="hasFilters ? '没有符合条件的题目' : '题库还是空的'"
          :description="
            hasFilters
              ? '换一个题型、难度或关键词试试，或清除筛选。'
              : '支持 JSON / XLSX 批量导入；也可以先导入模板里的示例题。'
          "
        >
          <template #action>
            <AppButton v-if="hasFilters" variant="ghost" @click="resetFilters">清除筛选</AppButton>
            <AppButton v-else variant="primary" @click="openImport">
              <UploadCloud :size="15" :stroke-width="1.9" />
              导入题目
            </AppButton>
          </template>
        </AppEmpty>
      </section>

      <template v-else>
        <section class="question-grid">
          <QuestionCard
            v-for="question in questions"
            :key="question.id"
            :question="question"
            @edit="openEdit"
            @remove="askDelete"
            @explain="openExplain"
          />
        </section>

        <section class="panel">
          <AppPagination
            :total="total"
            :page="page"
            :page-size="pageSize"
            @change="handlePageChange"
          />
        </section>
      </template>

      <p v-if="questionBankEmpty" class="sr-only" aria-live="polite">题库为空</p>
    </template>

    <QuestionImportPanel
      v-model="importOpen"
      :class-id="selectedClassId ? Number(selectedClassId) : null"
      @imported="handleImported"
    />

    <QuestionEditDrawer
      v-model="editOpen"
      :question="editTarget"
      @saved="handleEdited"
    />

    <QuestionExplainModal
      v-model="explainOpen"
      :question-id="explainTarget?.id ?? null"
      :question-stem="explainTarget?.stem"
    />

    <AppModal
      v-model="deleteOpen"
      title="删除这道题？"
      description="删除后不再出现在题库和组卷候选中；已被已发布试卷引用时无法删除。"
      confirm-text="删除"
      confirm-variant="danger"
      :confirm-loading="deleting"
      @confirm="confirmDelete"
    >
      <div class="delete-preview">
        <AppTag tone="danger" dot>不可撤销</AppTag>
        <p>{{ deleteTarget?.stem }}</p>
      </div>
      <p v-if="deleteError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ deleteError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.question-toolbar {
  margin-bottom: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
}

.question-toolbar__row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
}

.class-select {
  width: 320px;
  max-width: 100%;
}

.question-toolbar__summary {
  display: flex;
  align-items: baseline;
  gap: var(--sp-1);
  padding-bottom: 9px;
}

.question-toolbar__summary strong {
  color: var(--color-primary);
  font-size: var(--fs-xl);
}

.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin-bottom: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-3);
}

.filter-search {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.filter-search :deep(.app-input) {
  flex: 1;
  min-width: 220px;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4);
  margin-bottom: var(--sp-4);
}

.delete-preview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1023px) {
  .question-grid,
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
