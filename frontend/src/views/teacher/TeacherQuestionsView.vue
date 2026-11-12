<!-- 教师题库：班级切换、导入预览、四维筛选、题目卡片、编辑/删除/讲评。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  PencilLine,
  Plus,
  RefreshCw,
  Search,
  Trash2,
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
import { questionsApi, banksApi } from '@/api/questions'
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
  QuestionBank,
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

const banks = ref<QuestionBank[]>([])
const banksLoading = ref(false)
const banksError = ref('')
const activeBankId = ref<number | null>(null)

const bankModalOpen = ref(false)
const bankModalMode = ref<'create' | 'rename'>('create')
const bankNameDraft = ref('')
const bankTarget = ref<QuestionBank | null>(null)
const bankSaving = ref(false)
const bankError = ref('')

const bankDeleteOpen = ref(false)
const bankDeleteTarget = ref<QuestionBank | null>(null)
const bankDeleting = ref(false)
const bankDeleteError = ref('')

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
const activeBank = computed(
  () => banks.value.find((item) => item.id === activeBankId.value) ?? null,
)
const allQuestionCount = computed(() =>
  banks.value.reduce((sum, bank) => sum + bank.question_count, 0),
)
const bankListEmpty = computed(
  () => !banksLoading.value && !banksError.value && banks.value.length === 0,
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
      bank_id: activeBankId.value ?? undefined,
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

async function loadBanks(): Promise<void> {
  if (!selectedClassId.value) return
  banksLoading.value = true
  banksError.value = ''
  try {
    const result = await banksApi.list(Number(selectedClassId.value))
    banks.value = result
    if (
      activeBankId.value !== null &&
      !result.some((bank) => bank.id === activeBankId.value)
    ) {
      activeBankId.value = null
    }
  } catch (err) {
    banks.value = []
    banksError.value = mapError(err)
  } finally {
    banksLoading.value = false
  }
}

function selectBank(bankId: number | null): void {
  if (bankId === activeBankId.value) return
  activeBankId.value = bankId
  page.value = 1
  void loadQuestions(1)
}

function openCreateBank(): void {
  if (!selectedClassId.value) return
  bankModalMode.value = 'create'
  bankTarget.value = null
  bankNameDraft.value = ''
  bankError.value = ''
  bankModalOpen.value = true
}

function openRenameBank(bank: QuestionBank): void {
  bankModalMode.value = 'rename'
  bankTarget.value = bank
  bankNameDraft.value = bank.name
  bankError.value = ''
  bankModalOpen.value = true
}

async function submitBank(): Promise<void> {
  const name = bankNameDraft.value.trim()
  if (!name) {
    bankError.value = '请填写题库名称'
    return
  }
  if (name.length > 60) {
    bankError.value = '题库名称不能超过 60 字'
    return
  }
  if (!selectedClassId.value || bankSaving.value) return
  bankSaving.value = true
  bankError.value = ''
  try {
    if (bankModalMode.value === 'create') {
      const created = await banksApi.create(Number(selectedClassId.value), { name })
      ui.success('题库已创建')
      await loadBanks()
      activeBankId.value = created.id
      page.value = 1
      await loadQuestions(1)
    } else if (bankTarget.value) {
      await banksApi.update(bankTarget.value.id, { name })
      ui.success('题库已改名')
      await loadBanks()
      await loadQuestions(page.value)
    }
    bankModalOpen.value = false
    bankTarget.value = null
  } catch (err) {
    if (isApiError(err) && err.code === 40913) bankError.value = '题库名称已存在，请换一个名称'
    else bankError.value = mapError(err)
  } finally {
    bankSaving.value = false
  }
}

function askDeleteBank(bank: QuestionBank): void {
  if (bank.question_count > 0) return
  bankDeleteTarget.value = bank
  bankDeleteError.value = ''
  bankDeleteOpen.value = true
}

async function confirmDeleteBank(): Promise<void> {
  if (!bankDeleteTarget.value || bankDeleting.value) return
  bankDeleting.value = true
  bankDeleteError.value = ''
  try {
    await banksApi.remove(bankDeleteTarget.value.id)
    ui.success('题库已删除')
    bankDeleteOpen.value = false
    bankDeleteTarget.value = null
    await loadBanks()
    await loadQuestions(1)
  } catch (err) {
    if (isApiError(err) && err.code === 40912) {
      bankDeleteError.value = '题库内仍有题目，请先移出或删除题目后再删库'
    } else {
      bankDeleteError.value = mapError(err)
    }
  } finally {
    bankDeleting.value = false
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
  activeBankId.value = null
  await loadBanks()
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
  activeBankId.value = null
  banks.value = []
  banksError.value = ''
  syncClassQuery()
  void loadBanks()
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
  await loadBanks()
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

      <div class="bank-layout">
        <aside class="bank-sidebar panel" aria-label="题库分类">
          <header class="bank-sidebar__head">
            <div>
              <p class="eyebrow">BANKS</p>
              <h2 class="bank-sidebar__title">题库分类</h2>
            </div>
            <AppButton
              variant="secondary"
              size="sm"
              :disabled="!selectedClassId || banksLoading"
              @click="openCreateBank"
            >
              <Plus :size="14" :stroke-width="2" />
              新建
            </AppButton>
          </header>

          <p v-if="banksError" class="bank-sidebar__error" role="alert">
            <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ banksError }}</span>
            <button class="bank-sidebar__retry" type="button" @click="loadBanks">重试</button>
          </p>

          <ul v-else class="bank-list">
            <li>
              <button
                class="bank-row"
                :class="{ 'bank-row--active': activeBankId === null }"
                type="button"
                @click="selectBank(null)"
              >
                <span class="bank-row__name">全部题库</span>
                <span class="bank-row__count tabular">{{ allQuestionCount }}</span>
              </button>
            </li>
            <li v-for="bank in banks" :key="bank.id">
              <div class="bank-row" :class="{ 'bank-row--active': activeBankId === bank.id }">
                <button class="bank-row__main" type="button" @click="selectBank(bank.id)">
                  <span class="bank-row__name truncate" :title="bank.name">{{ bank.name }}</span>
                  <span class="bank-row__count tabular">{{ bank.question_count }}</span>
                </button>
                <span class="bank-row__actions">
                  <button
                    class="bank-row__action"
                    type="button"
                    :aria-label="`重命名题库 ${bank.name}`"
                    title="重命名"
                    @click.stop="openRenameBank(bank)"
                  >
                    <PencilLine :size="13" :stroke-width="1.9" />
                  </button>
                  <button
                    class="bank-row__action"
                    type="button"
                    :aria-label="`删除题库 ${bank.name}`"
                    :title="
                      bank.question_count > 0
                        ? `题库内还有 ${bank.question_count} 道题，先移出或删除题目后再删库`
                        : '删除题库'
                    "
                    :disabled="bank.question_count > 0"
                    @click.stop="askDeleteBank(bank)"
                  >
                    <Trash2 :size="13" :stroke-width="1.9" />
                  </button>
                </span>
              </div>
            </li>
          </ul>

          <p v-if="bankListEmpty" class="bank-sidebar__empty">
            还没有题库。导入题目时可在导入面板新建，或点右上角「新建」。
          </p>
        </aside>

        <div class="bank-main">
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
          :title="
            hasFilters
              ? '没有符合条件的题目'
              : activeBank
                ? `${activeBank.name} 还没有题目`
                : '题库还是空的'
          "
          :description="
            hasFilters
              ? '换一个题型、难度或关键词试试，或清除筛选。'
              : activeBank
                ? '导入题目会默认归入当前题库，也可在导入面板切换目标题库。'
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
        </div>
      </div>
    </template>

    <QuestionImportPanel
      v-model="importOpen"
      :class-id="selectedClassId ? Number(selectedClassId) : null"
      :bank-id="activeBankId"
      :banks="banks"
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
      v-model="bankModalOpen"
      :title="bankModalMode === 'create' ? '新建题库' : '重命名题库'"
      :description="
        bankModalMode === 'create'
          ? '题库按班级隔离，名称在班内唯一；题目必须归属于一个题库。'
          : '改名只影响分类展示，不影响已有试卷与作答记录。'
      "
      :confirm-text="bankModalMode === 'create' ? '创建题库' : '保存名称'"
      :confirm-loading="bankSaving"
      @confirm="submitBank"
    >
      <div class="edit-form">
        <AppInput
          v-model="bankNameDraft"
          label="题库名称"
          placeholder="如：第5章 网络基础"
          :maxlength="60"
          :disabled="bankSaving"
        />
        <p v-if="bankError" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ bankError }}</span>
        </p>
      </div>
    </AppModal>

    <AppModal
      v-model="bankDeleteOpen"
      title="删除这个题库？"
      description="仅空题库可以删除；题库内有题目时请先逐题移动或删除。"
      confirm-text="删除题库"
      confirm-variant="danger"
      :confirm-loading="bankDeleting"
      @confirm="confirmDeleteBank"
    >
      <div class="delete-preview">
        <AppTag tone="danger" dot>不可撤销</AppTag>
        <p>{{ bankDeleteTarget?.name }}</p>
      </div>
      <p v-if="bankDeleteError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ bankDeleteError }}</span>
      </p>
    </AppModal>

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
.bank-layout {
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  gap: var(--sp-4);
  align-items: start;
}

.bank-main {
  min-width: 0;
}

.bank-sidebar {
  position: sticky;
  top: calc(var(--topbar-h) + var(--sp-4));
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  max-height: calc(100vh - var(--topbar-h) - var(--sp-6));
  padding: var(--sp-4);
  overflow-y: auto;
}

.bank-sidebar__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-2);
}

.bank-sidebar__title {
  font-size: var(--fs-base);
  line-height: 1.4;
}

.bank-sidebar__error {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--color-danger);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.bank-sidebar__retry {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.bank-sidebar__empty {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.bank-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bank-row {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  border-radius: var(--radius-xs);
  color: var(--color-text);
}

button.bank-row {
  gap: var(--sp-2);
  padding: 8px var(--sp-2);
  border: 0;
  background: transparent;
  text-align: left;
  font-size: var(--fs-sm);
}

.bank-row:hover {
  background: var(--color-surface-alt);
}

.bank-row--active,
.bank-row--active:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.bank-row__main {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 1;
  min-width: 0;
  padding: 8px var(--sp-2);
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.bank-row__name {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
}

.bank-row__count {
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bank-row--active .bank-row__count {
  color: var(--color-primary);
}

.bank-row__actions {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-right: 4px;
  opacity: 0.65;
  transition: opacity 140ms ease-out;
}

.bank-row:hover .bank-row__actions,
.bank-row--active .bank-row__actions {
  opacity: 1;
}

.bank-row__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
}

.bank-row__action:hover:not(:disabled) {
  background: var(--color-surface);
  color: var(--color-primary);
}

.bank-row__action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

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
  .bank-layout {
    grid-template-columns: 1fr;
  }

  .bank-sidebar {
    position: static;
    max-height: none;
  }

  .question-grid,
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
