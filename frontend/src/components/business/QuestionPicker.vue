<!-- 选题器：M3.1 支持按题库多选范围、整库加入或逐题勾选，跨页保留已选题目。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  AlertCircle,
  Check,
  FolderPlus,
  ListChecks,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppCard from '@/components/base/AppCard.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { questionsApi } from '@/api/questions'
import {
  DIFFICULTY_META,
  PAGE_SIZE,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import type {
  QuestionBank,
  QuestionDifficulty,
  QuestionItem,
  QuestionType,
} from '@/api/types'
import type { SelectOption } from '@/types'

const props = defineProps<{
  classId: number | null
  modelValue: number[]
  banks: QuestionBank[]
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: number[]): void
  (event: 'update:items', value: QuestionItem[]): void
}>()

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

const questions = ref<QuestionItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const loading = ref(false)
const loadError = ref('')
const chosen = ref<Map<number, QuestionItem>>(new Map())
const selectedBankIds = ref<number[]>([])
const bankAddingId = ref<number | null>(null)

const typeFilter = ref('')
const difficultyFilter = ref('')
const tagFilter = ref('')
const keywordDraft = ref('')
const keyword = ref('')

const selectedIds = computed(() => new Set(props.modelValue))
const selectedItems = computed(() => Array.from(chosen.value.values()))
const selectedCount = computed(() => props.modelValue.length)
const selectedScore = computed(() => selectedCount.value)
const pageAllSelected = computed(
  () => questions.value.length > 0 && questions.value.every((item) => selectedIds.value.has(item.id)),
)
const hasFilters = computed(
  () => Boolean(typeFilter.value || difficultyFilter.value || tagFilter.value || keyword.value),
)
const bankScopeCount = computed(() => {
  const scoped = selectedBankIds.value.length
    ? props.banks.filter((bank) => selectedBankIds.value.includes(bank.id))
    : props.banks
  return scoped.reduce((sum, bank) => sum + bank.question_count, 0)
})
/** 后端列表只支持单个 bank_id；多选时列全部题目，并在行内标注所属题库。 */
const listBankId = computed(() =>
  selectedBankIds.value.length === 1 ? selectedBankIds.value[0] : undefined,
)

function toggleBank(bankId: number): void {
  const index = selectedBankIds.value.indexOf(bankId)
  if (index >= 0) selectedBankIds.value = selectedBankIds.value.filter((id) => id !== bankId)
  else selectedBankIds.value = [...selectedBankIds.value, bankId]
  page.value = 1
  void loadQuestions(1)
}

/** 整库加入：分页拉齐库内有效题后并入已选，保持旧 question_ids 组卷路径。 */
async function addWholeBank(bank: QuestionBank): Promise<void> {
  if (props.classId === null || bankAddingId.value !== null) return
  bankAddingId.value = bank.id
  try {
    const next = new Map(chosen.value)
    let nextPage = 1
    const size = 50
    while (nextPage <= 20) {
      const result = await questionsApi.list(props.classId, {
        bank_id: bank.id,
        page: nextPage,
        page_size: size,
      })
      for (const question of result.list) next.set(question.id, question)
      if (result.list.length === 0 || nextPage * size >= result.total) break
      nextPage += 1
    }
    emitSelected(next)
  } catch (err) {
    loadError.value = mapError(err)
  } finally {
    bankAddingId.value = null
  }
}

function emitSelected(next: Map<number, QuestionItem>): void {
  chosen.value = next
  emit('update:modelValue', Array.from(next.keys()))
  emit('update:items', Array.from(next.values()))
}

function toggle(question: QuestionItem): void {
  const next = new Map(chosen.value)
  if (next.has(question.id)) next.delete(question.id)
  else next.set(question.id, question)
  emitSelected(next)
}

function togglePage(): void {
  const next = new Map(chosen.value)
  if (pageAllSelected.value) {
    for (const question of questions.value) next.delete(question.id)
  } else {
    for (const question of questions.value) next.set(question.id, question)
  }
  emitSelected(next)
}

function removeSelected(id: number): void {
  const next = new Map(chosen.value)
  next.delete(id)
  emitSelected(next)
}

function clearSelected(): void {
  emitSelected(new Map())
}

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

async function loadQuestions(nextPage = page.value): Promise<void> {
  if (props.classId === null) {
    questions.value = []
    total.value = 0
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const result = await questionsApi.list(props.classId, {
      bank_id: listBankId.value,
      type: typeFilter.value ? (typeFilter.value as QuestionType) : undefined,
      knowledge_tag: tagFilter.value.trim() || undefined,
      difficulty: difficultyFilter.value
        ? (difficultyFilter.value as QuestionDifficulty)
        : undefined,
      keyword: keyword.value.trim() || undefined,
      page: nextPage,
      page_size: pageSize.value,
    })
    questions.value = result.list
    total.value = result.total
    page.value = result.page
    pageSize.value = result.page_size
    const next = new Map(chosen.value)
    for (const question of result.list) {
      if (next.has(question.id)) next.set(question.id, question)
    }
    chosen.value = next
    emit('update:items', Array.from(next.values()))
  } catch (err) {
    questions.value = []
    total.value = 0
    loadError.value = mapError(err)
  } finally {
    loading.value = false
  }
}

function applyFilter(): void {
  page.value = 1
  void loadQuestions(1)
}

function applyKeyword(): void {
  keyword.value = keywordDraft.value.trim()
  applyFilter()
}

function resetFilters(): void {
  typeFilter.value = ''
  difficultyFilter.value = ''
  tagFilter.value = ''
  keywordDraft.value = ''
  keyword.value = ''
  applyFilter()
}

function handlePageChange(nextPage: number, nextSize: number): void {
  pageSize.value = nextSize
  page.value = nextPage
  void loadQuestions(nextPage)
}

watch(
  () => props.classId,
  () => {
    questions.value = []
    total.value = 0
    page.value = 1
    selectedBankIds.value = []
    typeFilter.value = ''
    difficultyFilter.value = ''
    tagFilter.value = ''
    keywordDraft.value = ''
    keyword.value = ''
    loadError.value = ''
    emitSelected(new Map())
    void loadQuestions(1)
  },
  { immediate: true },
)
</script>

<template>
  <section class="picker">
    <header class="picker__head">
      <div class="split-title">
        <h3 class="section-title">从题库选题</h3>
        <span class="muted text-sm">
          已选 <strong class="text-primary tabular">{{ selectedCount }}</strong> 题 ·
          合计 <strong class="text-primary tabular">{{ selectedScore }}</strong> 分
        </span>
      </div>
      <div class="picker__head-actions">
        <AppButton variant="ghost" size="sm" :disabled="questions.length === 0" @click="togglePage">
          {{ pageAllSelected ? '取消本页' : '全选本页' }}
        </AppButton>
        <AppButton
          v-if="selectedCount > 0"
          variant="ghost"
          size="sm"
          @click="clearSelected"
        >
          <Trash2 :size="14" :stroke-width="1.8" />
          清空已选
        </AppButton>
      </div>
    </header>

    <section v-if="props.banks.length > 0" class="bank-scope" aria-label="题库范围">
      <div class="bank-scope__head">
        <span class="bank-scope__title">题库范围</span>
        <span class="muted text-xs">
          可多选；仅选 1 个库时只列出该库题目，多选时列出全部题目并在行内标注所属库
        </span>
      </div>
      <div class="bank-scope__chips">
        <span
          v-for="bank in props.banks"
          :key="bank.id"
          class="bank-chip"
          :class="{ 'bank-chip--active': selectedBankIds.includes(bank.id) }"
        >
          <button class="bank-chip__toggle" type="button" @click="toggleBank(bank.id)">
            <Check
              v-if="selectedBankIds.includes(bank.id)"
              :size="12"
              :stroke-width="2.6"
              aria-hidden="true"
            />
            <span class="truncate" :title="bank.name">{{ bank.name }}</span>
            <span class="bank-chip__count tabular">{{ bank.question_count }}</span>
          </button>
          <button
            class="bank-chip__add"
            type="button"
            :disabled="bankAddingId !== null || bank.question_count === 0"
            :title="`把「${bank.name}」的 ${bank.question_count} 道题全部加入`"
            @click="addWholeBank(bank)"
          >
            <FolderPlus :size="12" :stroke-width="1.9" />
            {{ bankAddingId === bank.id ? '加入中…' : '整库加入' }}
          </button>
        </span>
      </div>
      <p class="bank-scope__summary">
        共 <strong class="tabular">{{ bankScopeCount }}</strong> 题
        <template v-if="selectedBankIds.length > 0"> · 已选 {{ selectedBankIds.length }} 个库</template>
      </p>
    </section>

    <section v-if="selectedItems.length > 0" class="picked" aria-label="已选题目">
      <div class="picked__head">
        <ListChecks :size="14" :stroke-width="1.9" />
        <span>已选题目</span>
        <span class="muted text-xs">按每题 1 分计</span>
      </div>
      <ul class="picked__list">
        <li v-for="item in selectedItems" :key="item.id" class="picked__item">
          <button
            class="picked__remove"
            type="button"
            :aria-label="`从试卷移除第 ${item.id} 题`"
            @click="removeSelected(item.id)"
          >
            <span class="picked__stem truncate">{{ item.stem }}</span>
            <span class="picked__x" aria-hidden="true">×</span>
          </button>
        </li>
      </ul>
    </section>

    <section class="picker-filters" aria-label="题库筛选">
      <AppSelect
        v-model="typeFilter"
        label="题型"
        :options="typeOptions"
        @change="applyFilter"
      />
      <AppSelect
        v-model="difficultyFilter"
        label="难度"
        :options="difficultyOptions"
        @change="applyFilter"
      />
      <AppInput
        v-model="tagFilter"
        label="知识点标签"
        placeholder="精确匹配，如 传输层"
        @blur="applyFilter"
      />
      <div class="picker-keyword">
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
      </div>
      <AppButton v-if="hasFilters" variant="ghost" @click="resetFilters">清除筛选</AppButton>
    </section>

    <div v-if="props.classId === null" class="picker-empty">
      <AppEmpty title="请先选择班级" description="题库按班级隔离，选择班级后才能选题。" />
    </div>

    <section v-else-if="loading" class="bank-list" aria-busy="true">
      <AppCard v-for="index in 4" :key="index" padding="sm">
        <AppSkeleton variant="text" :rows="3" />
      </AppCard>
    </section>

    <section v-else-if="loadError" class="pickable-error">
      <AppEmpty error title="题库暂时无法加载" :description="loadError">
        <template #action>
          <AppButton variant="secondary" @click="loadQuestions(page)">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <section v-else-if="questions.length === 0" class="picker-empty">
      <AppEmpty
        :title="hasFilters ? '没有符合条件的题目' : '题库还是空的'"
        :description="
          hasFilters
            ? '调整筛选条件，或清除筛选后查看全部题目。'
            : '请先在题库页导入题目，再回来组卷。'
        "
      >
        <template v-if="hasFilters" #action>
          <AppButton variant="ghost" @click="resetFilters">清除筛选</AppButton>
        </template>
      </AppEmpty>
    </section>

    <template v-else>
      <ul class="bank-list">
        <li v-for="question in questions" :key="question.id">
          <label class="bank-item" :class="{ 'bank-item--active': selectedIds.has(question.id) }">
            <input
              class="visually-hidden"
              type="checkbox"
              :checked="selectedIds.has(question.id)"
              @change="toggle(question)"
            />
            <span class="bank-item__check" aria-hidden="true">
              <Check v-if="selectedIds.has(question.id)" :size="14" :stroke-width="2.4" />
            </span>
            <span class="bank-item__body">
              <span class="bank-item__tags">
                <AppTag :tone="QUESTION_TYPE_META[question.type].tone">
                  {{ QUESTION_TYPE_META[question.type].short }}
                </AppTag>
                <AppTag :tone="DIFFICULTY_META[question.difficulty].tone">
                  {{ DIFFICULTY_META[question.difficulty].label }}
                </AppTag>
                <AppTag tone="neutral">{{ question.knowledge_tag }}</AppTag>
                <AppTag v-if="question.bank_name" tone="primary">{{ question.bank_name }}</AppTag>
                <span class="bank-item__id mono">Q-{{ question.id }}</span>
              </span>
              <span class="bank-item__stem">{{ question.stem }}</span>
              <span v-if="question.options?.length" class="bank-item__options">
                {{ question.options.map((item) => `${item.key}. ${item.text}`).join('　') }}
              </span>
            </span>
            <span class="bank-item__score tabular">1 分</span>
          </label>
        </li>
      </ul>

      <section class="panel">
        <AppPagination
          :total="total"
          :page="page"
          :page-size="pageSize"
          @change="handlePageChange"
        />
      </section>
    </template>

    <p v-if="loadError" class="picker-note" role="alert">
      <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
      {{ loadError }}
    </p>
  </section>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.picker__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.picker__head-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.bank-scope {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.bank-scope__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.bank-scope__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bank-scope__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.bank-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  overflow: hidden;
}

.bank-chip--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.bank-chip__toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 220px;
  padding: 5px var(--sp-2);
  border: 0;
  background: transparent;
  color: inherit;
  font-size: var(--fs-xs);
  font-weight: 600;
}

.bank-chip__count {
  color: var(--color-text-muted);
  font-weight: 500;
}

.bank-chip--active .bank-chip__count {
  color: var(--color-primary);
}

.bank-chip__add {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 5px var(--sp-2);
  border: 0;
  border-left: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.bank-chip__add:hover:not(:disabled) {
  color: var(--color-primary);
  background: var(--color-surface);
}

.bank-chip__add:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.bank-scope__summary {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bank-scope__summary strong {
  color: var(--color-primary);
}

.picked {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-primary) 24%, transparent);
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
}

.picked__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.picked__list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  max-height: 118px;
  margin-top: var(--sp-2);
  overflow-y: auto;
}

.picked__item {
  max-width: 100%;
}

.picked__remove {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 260px;
  padding: 3px 8px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 22%, transparent);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.picked__remove:hover {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.picked__x {
  font-size: var(--fs-base);
  line-height: 1;
}

.picker-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) 1.4fr auto;
  align-items: end;
  gap: var(--sp-2);
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.picker-keyword {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-2);
  min-width: 0;
}

.picker-keyword :deep(.app-input) {
  flex: 1;
  min-width: 0;
}

.bank-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  max-height: 520px;
  overflow-y: auto;
  padding-right: 2px;
}

.bank-item {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  transition: border-color 160ms ease-out, background-color 160ms ease-out;
}

.bank-item:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-alt);
}

.bank-item--active {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary-soft) 46%, var(--color-surface));
}

.bank-item__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-top: 2px;
  flex-shrink: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-inverse);
}

.bank-item--active .bank-item__check {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.bank-item__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.bank-item__tags {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.bank-item__id {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bank-item__stem {
  font-size: var(--fs-sm);
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.bank-item__options {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.bank-item__score {
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.picker-empty,
.pickable-error {
  padding: var(--sp-3) 0;
}

.picker-note {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-danger);
  font-size: var(--fs-xs);
}

@media (max-width: 1023px) {
  .picker-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .picker-filters {
    grid-template-columns: 1fr;
  }

  .bank-item__score {
    display: none;
  }
}
</style>
