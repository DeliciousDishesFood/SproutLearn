<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Sparkles, Upload } from 'lucide-vue-next'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { questionsApi } from '@/api/questions'
import { banksApi } from '@/api/banks'
import { toUserMessage } from '@/api/client'
import type {
  QuestionBank,
  QuestionImportPreview,
  QuestionItem,
  QuestionOption,
  QuestionType,
  QuestionUpdatePayload,
} from '@/api/contract'
import {
  DIFFICULTY_LABEL,
  QUESTION_TYPE_LABEL,
  formatAnswer,
  formatDateTime,
} from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const ui = useUiStore()
const toast = useToast()
const classId = computed(() => Number(route.params.classId))

const banks = ref<QuestionBank[]>([])
const items = ref<QuestionItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(true)
const errorText = ref('')

const filters = reactive({
  bank_id: typeof route.query.bank_id === 'string' ? route.query.bank_id : '',
  type: '',
  difficulty: '',
  status: '',
  knowledge_tag: '',
  keyword: '',
})

const typeOptions: Array<{ value: QuestionType; label: string }> = [
  { value: 'single', label: '单选' },
  { value: 'multiple', label: '多选' },
  { value: 'judge', label: '判断' },
  { value: 'blank', label: '填空' },
]

const bankFilterOptions = computed(() => [
  { label: '全部题库', value: '' },
  ...banks.value.map((bank) => ({ label: `${bank.name}（${bank.question_count}）`, value: String(bank.id) })),
])
const typeFilterOptions = computed(() => [{ label: '全部题型', value: '' }, ...typeOptions])
const typeOnlyOptions = typeOptions.map((item) => ({ label: item.label, value: item.value }))
const statusFilterOptions = [
  { label: '全部状态', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
]
const difficultyFilterOptions = [
  { label: '全部难度', value: '' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]
const difficultyOptions = [
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]
const importBankOptions = computed(() => [
  { label: '自动创建', value: '' },
  ...banks.value.map((bank) => ({ label: bank.name, value: String(bank.id) })),
])

async function loadBanks(): Promise<void> {
  try {
    banks.value = await banksApi.list(classId.value)
    ui.setCurrentClassId(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
}

async function loadQuestions(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await questionsApi.list(classId.value, {
      bank_id: filters.bank_id ? Number(filters.bank_id) : undefined,
      type: (filters.type || undefined) as QuestionType | undefined,
      difficulty: (filters.difficulty || undefined) as 'easy' | 'medium' | 'hard' | undefined,
      status: (filters.status || undefined) as 'draft' | 'published' | undefined,
      knowledge_tag: filters.knowledge_tag.trim() || undefined,
      keyword: filters.keyword.trim() || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = result.list
    total.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  void loadQuestions()
}

/* ---------- 编辑题目 ---------- */
const editOpen = ref(false)
const editing = ref<QuestionItem | null>(null)
const saving = ref(false)
const editError = ref('')
const editForm = reactive({
  type: 'single' as QuestionType,
  bank_id: '',
  stem: '',
  knowledge_tag: '',
  difficulty: 'medium' as 'easy' | 'medium' | 'hard',
  analysis: '',
  answer: '',
  options: [] as QuestionOption[],
})

const bankEditOptions = computed(() =>
  banks.value.map((bank) => ({ label: bank.name, value: String(bank.id) })),
)

const answerHint = computed(() => {
  if (editForm.type === 'multiple') return '多选用逗号分隔，例如 A,B'
  if (editForm.type === 'judge') return '填 对 / 错 或 true / false'
  if (editForm.type === 'blank') return '填写填空题参考答案'
  return '按题型填写答案'
})

const CHOICE_TYPES: QuestionType[] = ['single', 'multiple', 'judge']
const OPTION_KEYS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

function optionKey(index: number): string {
  return OPTION_KEYS[index] ?? `选项${index + 1}`
}

function renumberOptions(): void {
  editForm.options.forEach((option, index) => {
    option.key = optionKey(index)
  })
}

function addOption(): void {
  editForm.options.push({ key: optionKey(editForm.options.length), text: '' })
}

function removeOption(index: number): void {
  editForm.options.splice(index, 1)
  renumberOptions()
}

function onEditTypeChange(type: QuestionType): void {
  if (CHOICE_TYPES.includes(type) && editForm.options.length === 0) {
    editForm.options.push({ key: 'A', text: '' }, { key: 'B', text: '' })
  }
}

function answerToText(answer: unknown): string {
  return formatAnswer(answer).replace(/^未作答$/, '')
}

function parseAnswer(type: QuestionType, text: string): unknown {
  const trimmed = text.trim()
  if (type === 'multiple') return trimmed.split(/[,，、\s]+/).filter(Boolean)
  if (type === 'judge') return /^(true|t|1|对|正确|yes|y)$/i.test(trimmed)
  if (type === 'single') return trimmed.toUpperCase()
  return trimmed
}

function openEdit(item: QuestionItem): void {
  editing.value = item
  editForm.type = item.type
  editForm.bank_id = String(item.bank_id ?? '')
  editForm.stem = item.stem
  editForm.knowledge_tag = item.knowledge_tag
  editForm.difficulty = item.difficulty
  editForm.analysis = item.analysis ?? ''
  editForm.answer = answerToText(item.answer)
  // 复制选项数组与对象，避免编辑弹窗引用原列表数据。
  editForm.options = item.options ? item.options.map((option) => ({ key: option.key, text: option.text })) : []
  editError.value = ''
  editOpen.value = true
}

async function saveEdit(): Promise<void> {
  if (!editing.value) return
  if (!editForm.stem.trim()) {
    editError.value = '题干不能为空'
    return
  }
  if (!editForm.bank_id) {
    editError.value = '请选择题库'
    return
  }
  if (CHOICE_TYPES.includes(editForm.type)) {
    if (editForm.options.some((option) => !option.text.trim())) {
      editError.value = '存在空白选项，请补全选项文本或删除该选项'
      return
    }
    const nonEmptyCount = editForm.options.filter((option) => option.text.trim()).length
    if ((editForm.type === 'single' || editForm.type === 'multiple') && nonEmptyCount < 2) {
      editError.value = `${editForm.type === 'single' ? '单选' : '多选'}题至少需要 2 个非空选项`
      return
    }
  }
  saving.value = true
  editError.value = ''
  try {
    const payload = {
      bank_id: Number(editForm.bank_id),
      type: editForm.type,
      stem: editForm.stem.trim(),
      options:
        editForm.type === 'blank'
          ? null
          : editForm.options.map((option) => ({ key: option.key, text: option.text.trim() })),
      answer: parseAnswer(editForm.type, editForm.answer),
      analysis: editForm.analysis.trim() || null,
      knowledge_tag: editForm.knowledge_tag.trim() || '未分类',
      difficulty: editForm.difficulty as 'easy' | 'medium' | 'hard',
    }
    await questionsApi.update(editing.value.id, payload as QuestionUpdatePayload)
    toast.success('题目已更新')
    editOpen.value = false
    await loadQuestions()
  } catch (error) {
    editError.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

async function remove(item: QuestionItem): Promise<void> {
  if (!window.confirm('确定删除这道题吗？删除后不可恢复。')) return
  try {
    await questionsApi.remove(item.id)
    toast.success('题目已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadQuestions()
  } catch (error) {
    toast.error(toUserMessage(error))
  }
}

/* ---------- 导入 ---------- */
const importOpen = ref(false)
const importFile = ref<File | null>(null)
const importBankId = ref('')
const preview = ref<QuestionImportPreview | null>(null)
const previewing = ref(false)
const committing = ref(false)
const importError = ref('')

function openImport(): void {
  importFile.value = null
  importBankId.value = filters.bank_id || ''
  preview.value = null
  importError.value = ''
  importOpen.value = true
}

function onImportFile(event: Event): void {
  const input = event.target as HTMLInputElement
  importFile.value = input.files?.[0] ?? null
  preview.value = null
  importError.value = ''
}

async function doPreview(): Promise<void> {
  if (!importFile.value) {
    importError.value = '请先选择导入文件'
    return
  }
  previewing.value = true
  importError.value = ''
  try {
    preview.value = await questionsApi.previewImport(
      classId.value,
      importFile.value,
      importBankId.value ? Number(importBankId.value) : null,
    )
  } catch (error) {
    importError.value = toUserMessage(error)
  } finally {
    previewing.value = false
  }
}

async function doCommit(): Promise<void> {
  if (!preview.value) return
  committing.value = true
  importError.value = ''
  try {
    const result = await questionsApi.commitImport(classId.value, {
      token: preview.value.token,
      bank_id: importBankId.value ? Number(importBankId.value) : null,
    })
    toast.success(`已导入 ${result.inserted} 道题目`)
    importOpen.value = false
    preview.value = null
    await Promise.all([loadBanks(), loadQuestions()])
  } catch (error) {
    importError.value = toUserMessage(error)
  } finally {
    committing.value = false
  }
}

/* ---------- 讲评 ---------- */
const explainOpen = ref(false)
const explainLoading = ref(false)
const explainText = ref('')
const explainError = ref('')
const explainTitle = ref('')

async function explain(item: QuestionItem): Promise<void> {
  explainOpen.value = true
  explainLoading.value = true
  explainText.value = ''
  explainError.value = ''
  explainTitle.value = item.stem
  try {
    const result = await questionsApi.explain(item.id)
    explainText.value = result.explanation ?? result.content ?? '本次讲评没有返回内容。'
  } catch (error) {
    explainError.value = toUserMessage(error)
  } finally {
    explainLoading.value = false
  }
}

watch(page, () => void loadQuestions())

onMounted(async () => {
  await Promise.all([loadBanks(), loadQuestions()])
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> ·
        <RouterLink :to="`/teacher/classes/${classId}/banks`">题库</RouterLink> · 题目
      </p>
      <h1>题目</h1>
      <p class="page-head__lede">筛选、编辑与导入题目；讲评会取用知识库内容。</p>
    </div>
    <div class="page-head__actions">
      <BaseButton @click="openImport"><Upload :size="14" aria-hidden="true" />导入题目</BaseButton>
      <RouterLink class="btn btn--primary" :to="`/teacher/classes/${classId}/banks`">
        <Plus :size="14" aria-hidden="true" />管理题库
      </RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="card stack">
    <form class="form-row" @submit.prevent="applyFilters">
      <BaseField label="题库">
        <BaseSelect v-model="filters.bank_id" :options="bankFilterOptions" aria-label="按题库筛选" />
      </BaseField>
      <BaseField label="题型">
        <BaseSelect v-model="filters.type" :options="typeFilterOptions" aria-label="按题型筛选" />
      </BaseField>
      <BaseField label="难度">
        <BaseSelect v-model="filters.difficulty" :options="difficultyFilterOptions" aria-label="按难度筛选" />
      </BaseField>
      <BaseField label="状态">
        <BaseSelect v-model="filters.status" :options="statusFilterOptions" aria-label="按状态筛选" />
      </BaseField>
      <BaseField label="知识点">
        <input v-model="filters.knowledge_tag" class="input" type="search" placeholder="例如 导数" />
      </BaseField>
      <BaseField label="关键词">
        <input v-model="filters.keyword" class="input" type="search" placeholder="搜索题干或知识点" />
      </BaseField>
    </form>
    <div class="row row--wrap">
      <BaseButton variant="primary" type="button" @click="applyFilters">筛选</BaseButton>
      <BaseButton
        type="button"
        @click="filters.bank_id = ''; filters.type = ''; filters.difficulty = ''; filters.status = ''; filters.knowledge_tag = ''; filters.keyword = ''; applyFilters()"
      >
        重置
      </BaseButton>
      <span class="small tertiary">共 {{ total }} 道题</span>
    </div>
  </section>

  <section class="card">
    <p v-if="loading" class="loading-line">正在读取题目…</p>
    <EmptyState
      v-else-if="items.length === 0"
      title="没有符合条件的题目"
      description="可以调整筛选条件，或从 Excel / CSV 导入一批题目。"
      action-label="导入题目"
      @action="openImport"
    />
    <template v-else>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>题干</th>
              <th>类型</th>
              <th>题库</th>
              <th>知识点</th>
              <th>难度</th>
              <th>更新时间</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td style="max-width: 360px">
                <span class="row-title">
                  <strong>{{ item.stem }}</strong>
                  <em>答案：{{ formatAnswer(item.answer, item.type) }}</em>
                </span>
              </td>
              <td>{{ QUESTION_TYPE_LABEL[item.type] }}</td>
              <td>{{ item.bank_name ?? '—' }}</td>
              <td>{{ item.knowledge_tag }}</td>
              <td>{{ DIFFICULTY_LABEL[item.difficulty] }}</td>
              <td class="tertiary">{{ formatDateTime(item.updated_at) }}</td>
              <td>
                <div class="actions">
                  <button class="btn btn--sm" type="button" @click="explain(item)">
                    <Sparkles :size="12" aria-hidden="true" />讲评
                  </button>
                  <button class="btn btn--sm" type="button" @click="openEdit(item)">编辑</button>
                  <button class="btn btn--sm btn--danger" type="button" @click="remove(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
    </template>
  </section>

  <BaseModal :open="editOpen" title="编辑题目" wide @close="editOpen = false">
    <div class="form">
      <div class="form-row">
        <BaseField label="题库" required>
          <BaseSelect v-model="editForm.bank_id" :options="bankEditOptions" aria-label="所属题库" />
        </BaseField>
        <BaseField label="题型">
          <BaseSelect
            v-model="editForm.type"
            :options="typeOnlyOptions"
            aria-label="题型"
            @update:model-value="onEditTypeChange(editForm.type)"
          />
        </BaseField>
      </div>
      <BaseField label="题干" required>
        <textarea v-model="editForm.stem" class="input" rows="4" />
      </BaseField>

      <BaseField
        v-if="CHOICE_TYPES.includes(editForm.type)"
        label="选项"
        hint="编号自动按 A/B/C/D 重排；空白选项不允许保存"
      >
        <div class="option-list">
          <div v-for="(option, index) in editForm.options" :key="index" class="option-row">
            <span class="option-row__key">{{ option.key }}</span>
            <input v-model="option.text" class="input" type="text" :aria-label="`选项 ${option.key}`" />
            <button
              class="btn btn--sm btn--danger"
              type="button"
              :aria-label="`删除选项 ${option.key}`"
              @click="removeOption(index)"
            >
              删除
            </button>
          </div>
        </div>
        <BaseButton type="button" @click="addOption">添加选项</BaseButton>
      </BaseField>

      <div class="form-row">
        <BaseField label="知识点">
          <input v-model="editForm.knowledge_tag" class="input" type="text" />
        </BaseField>
        <BaseField label="难度">
          <BaseSelect v-model="editForm.difficulty" :options="difficultyOptions" aria-label="难度" />
        </BaseField>
      </div>
      <BaseField label="答案" :hint="answerHint">
        <input v-model="editForm.answer" class="input" type="text" />
      </BaseField>
      <BaseField label="解析（选填）">
        <textarea v-model="editForm.analysis" class="input" rows="3" />
      </BaseField>
      <p v-if="editError" class="form-error">{{ editError }}</p>
    </div>
    <template #footer>
      <BaseButton @click="editOpen = false">取消</BaseButton>
      <BaseButton variant="primary" :loading="saving" @click="saveEdit">保存</BaseButton>
    </template>
  </BaseModal>

  <BaseModal
    :open="importOpen"
    title="导入题目"
    description="先预览校验，再确认入库；预览结果不会直接写入题库。"
    wide
    @close="importOpen = false"
  >
    <div class="form">
      <div class="form-row">
        <BaseField label="导入文件">
          <input class="input" type="file" accept=".xlsx,.xls,.csv,.json" @change="onImportFile" />
        </BaseField>
        <BaseField label="目标题库" hint="不选则导入后自动建「导入题库-日期」">
          <BaseSelect v-model="importBankId" :options="importBankOptions" aria-label="导入到题库" />
        </BaseField>
      </div>

      <div class="row">
        <BaseButton :loading="previewing" @click="doPreview">预览校验</BaseButton>
        <span v-if="importFile" class="small tertiary">{{ importFile.name }}</span>
      </div>

      <p v-if="importError" class="form-error">{{ importError }}</p>

      <template v-if="preview">
        <div class="notice notice--lime">
          共 {{ preview.total }} 行，可导入 {{ preview.valid_count }} 行，异常
          {{ preview.error_count }} 行。
          <template v-if="preview.bank_name">目标题库：{{ preview.bank_name }}</template>
          <template v-else-if="preview.suggested_bank_name">
            将自动创建题库：{{ preview.suggested_bank_name }}
          </template>
        </div>

        <div v-if="preview.mapping" class="table-wrap">
          <table class="table">
            <thead><tr><th>源列</th><th>标准字段</th><th>匹配方式</th></tr></thead>
            <tbody>
              <tr v-for="(field, source) in preview.mapping" :key="source">
                <td>{{ source }}</td>
                <td>{{ field }}</td>
                <td class="tertiary">{{ preview.mapping_meta?.[source] ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="preview.errors.length" class="notice notice--danger">
          <p class="strong">需要修正的行</p>
          <ul style="margin: 6px 0 0; padding-left: 18px">
            <li v-for="(error, index) in preview.errors.slice(0, 20)" :key="index">
              第 {{ error.row }} 行 · {{ error.column }}：{{ error.message }}
            </li>
          </ul>
        </div>
      </template>
    </div>
    <template #footer>
      <BaseButton @click="importOpen = false">取消</BaseButton>
      <BaseButton
        variant="primary"
        :loading="committing"
        :disabled="!preview || preview.valid_count === 0"
        @click="doCommit"
      >
        确认导入 {{ preview ? preview.valid_count : 0 }} 道
      </BaseButton>
    </template>
  </BaseModal>

  <BaseModal :open="explainOpen" title="题目讲评" wide @close="explainOpen = false">
    <p class="small muted" style="margin-bottom: 10px">{{ explainTitle }}</p>
    <p v-if="explainLoading" class="loading-line">正在生成讲评…</p>
    <p v-else-if="explainError" class="notice notice--danger">{{ explainError }}</p>
    <p v-else class="notice" style="white-space: pre-wrap; line-height: 1.75">{{ explainText }}</p>
    <template #footer>
      <BaseButton @click="explainOpen = false">关闭</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.option-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-row__key {
  flex: none;
  width: 30px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: var(--surface-sunken);
  font-size: 12px;
  font-weight: 600;
}

.option-row .input {
  flex: 1;
}
</style>
