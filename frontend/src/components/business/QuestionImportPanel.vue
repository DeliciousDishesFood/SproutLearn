<!-- 题库导入：JSON/XLSX/XLS/CSV 拖拽预览、列映射、逐行编辑、二次确认与结果汇总。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileJson,
  UploadCloud,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { questionsApi } from '@/api/questions'
import { QUESTION_IMPORT_ACCEPT, QUESTION_IMPORT_MAX_MB } from '@/utils/constants'
import { formatFileSize } from '@/utils/format'
import type {
  QuestionBank,
  QuestionImportError,
  QuestionImportPreview,
  QuestionType,
} from '@/api/types'
import type { SelectOption, TableColumn } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    classId: number | null
    /** M3.1：默认导入到当前题库；为空时后端自动建「导入题库-日期」。 */
    bankId?: number | null
    banks?: QuestionBank[]
  }>(),
  {
    bankId: null,
    banks: () => [],
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'imported', count: number): void
}>()

interface EditableRow {
  key: number
  index: number
  stem: string
  type: QuestionType | ''
  answerText: string
  source: Record<string, unknown>
  serverErrors: string[]
  removed: boolean
}

const SUPPORTED_EXT = ['json', 'xlsx', 'xls', 'csv']
const QUESTION_TYPES: QuestionType[] = ['single', 'multiple', 'judge', 'blank']

const TYPE_OPTIONS: SelectOption[] = [
  { value: 'single', label: '单选' },
  { value: 'multiple', label: '多选' },
  { value: 'judge', label: '判断' },
  { value: 'blank', label: '填空' },
]

const FIELD_OPTIONS: SelectOption[] = [
  { value: '', label: '忽略此列' },
  { value: 'type', label: '题型' },
  { value: 'stem', label: '题干' },
  { value: 'options', label: '选项（整列）' },
  { value: 'optionA', label: '选项 A' },
  { value: 'optionB', label: '选项 B' },
  { value: 'optionC', label: '选项 C' },
  { value: 'optionD', label: '选项 D' },
  { value: 'optionE', label: '选项 E' },
  { value: 'optionF', label: '选项 F' },
  { value: 'answer', label: '答案' },
  { value: 'analysis', label: '解析' },
  { value: 'knowledge_tag', label: '知识点' },
  { value: 'difficulty', label: '难度' },
]

const TYPE_LABELS: Record<QuestionType, string> = {
  single: '单选',
  multiple: '多选',
  judge: '判断',
  blank: '填空',
}

const inputRef = ref<HTMLInputElement | null>(null)
const dragDepth = ref(0)
const dragActive = ref(false)
const file = ref<File | null>(null)
const previewing = ref(false)
const committing = ref(false)
const preview = ref<QuestionImportPreview | null>(null)
const inserted = ref<number | null>(null)
const error = ref('')
const columnMap = ref<Record<string, string>>({})
const editableRows = ref<EditableRow[]>([])
const confirming = ref(false)
const targetBankId = ref<number | null>(props.bankId)

const targetBankOptions = computed<SelectOption[]>(() => [
  { value: '', label: '自动创建「导入题库-日期」' },
  ...props.banks.map((bank) => ({
    value: String(bank.id),
    label: `${bank.name}（${bank.question_count} 题）`,
  })),
])
const targetBankName = computed(() => {
  if (targetBankId.value === null) return ''
  return props.banks.find((bank) => bank.id === targetBankId.value)?.name ?? ''
})

const errorColumns: TableColumn[] = [
  { key: 'row', title: '行号', width: '76px' },
  { key: 'column', title: '字段', width: '120px' },
  { key: 'message', title: '原因' },
]

const rowColumns: TableColumn[] = [
  { key: 'index', title: '行号', width: '56px' },
  { key: 'type', title: '题型', width: '104px' },
  { key: 'stem', title: '题干' },
  { key: 'answer', title: '答案', width: '200px' },
  { key: 'state', title: '状态', width: '200px' },
  { key: 'actions', title: '操作', width: '72px' },
]

/** 后端返回 mapping/rows 时启用映射与行编辑；旧响应自动退回原有错误列表模式。 */
const hasRowModel = computed(() => (preview.value?.rows?.length ?? 0) > 0)
const sourceColumns = computed(() => Object.keys(columnMap.value))
const activeRows = computed(() => editableRows.value.filter((row) => !row.removed))
const importableRows = computed(() =>
  activeRows.value.filter((row) => rowProblems(row).length === 0 && row.serverErrors.length === 0),
)
const skippedCount = computed(() => Math.max(0, (preview.value?.total ?? 0) - importableRows.value.length))
const failures = computed<QuestionImportError[]>(() => preview.value?.errors ?? [])

const canCommit = computed(() => {
  if (!preview.value) return false
  if (hasRowModel.value) return importableRows.value.length > 0
  return preview.value.error_count === 0 && preview.value.valid_count > 0
})

function reset(): void {
  file.value = null
  preview.value = null
  inserted.value = null
  error.value = ''
  previewing.value = false
  committing.value = false
  dragDepth.value = 0
  dragActive.value = false
  columnMap.value = {}
  editableRows.value = []
  confirming.value = false
  targetBankId.value = props.bankId
  if (inputRef.value) inputRef.value.value = ''
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) targetBankId.value = props.bankId
    else reset()
  },
)

function close(): void {
  emit('update:modelValue', false)
}

function chooseFile(): void {
  if (previewing.value || committing.value) return
  inputRef.value?.click()
}

function onInputChange(event: Event): void {
  const input = event.target as HTMLInputElement
  handleFile(input.files?.[0] ?? null)
}

function onDragEnter(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value += 1
  dragActive.value = true
}

function onDragOver(event: DragEvent): void {
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (dragDepth.value === 0) dragActive.value = false
}

function onDrop(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = 0
  dragActive.value = false
  if (previewing.value || committing.value) return
  handleFile(event.dataTransfer?.files?.[0] ?? null)
}

function extensionOf(name: string): string {
  const index = name.lastIndexOf('.')
  return index >= 0 ? name.slice(index + 1).toLowerCase() : ''
}

function normalizeType(value: unknown): QuestionType | '' {
  const text = typeof value === 'string' ? value.trim() : ''
  return QUESTION_TYPES.includes(text as QuestionType) ? (text as QuestionType) : ''
}

function answerToText(type: QuestionType | '', value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.map((item) => String(item)).join(',')
  if (typeof value === 'boolean') return value ? '对' : '错'
  if (type === 'judge') {
    if (value === 1 || value === '1') return '对'
    if (value === 0 || value === '0') return '错'
  }
  return String(value)
}

function textToAnswer(type: QuestionType | '', text: string): unknown {
  const trimmed = text.trim()
  if (!trimmed) return ''
  if (type === 'multiple') {
    return trimmed
      .split(/[,，、;；\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
  }
  if (type === 'judge') {
    const normalized = trimmed.toLowerCase()
    if (['对', '正确', 'true', 't', '是', '1', '√'].includes(normalized)) return true
    if (['错', '错误', 'false', 'f', '否', '0', '×'].includes(normalized)) return false
  }
  return trimmed
}

function rowProblems(row: EditableRow): string[] {
  const problems: string[] = []
  if (!row.stem.trim()) problems.push('题干为空')
  if (!row.type) problems.push('未识别题型')
  if (!row.answerText.trim()) problems.push('答案为空')
  return problems
}

function rowStateText(row: EditableRow): string {
  const problems = rowProblems(row)
  if (problems.length > 0) return problems.join('、')
  if (row.serverErrors.length > 0) return row.serverErrors.join('；')
  return '待导入'
}

function isGuessed(column: string): boolean {
  return preview.value?.mapping_meta?.[column] === 'fuzzy'
}

function buildRows(data: QuestionImportPreview): EditableRow[] {
  return (data.rows ?? []).map((row, position) => {
    const source = row.normalized ? { ...row.normalized } : {}
    const type = normalizeType(source.type)
    return {
      key: row.index ?? position + 1,
      index: row.index ?? position + 1,
      stem: typeof source.stem === 'string' ? source.stem : '',
      type,
      answerText: answerToText(type, source.answer),
      source,
      serverErrors: (row.errors ?? []).map((issue) => issue.message),
      removed: false,
    }
  })
}

function buildColumnMap(data: QuestionImportPreview): Record<string, string> {
  const map: Record<string, string> = {}
  for (const [column, field] of Object.entries(data.mapping ?? {})) map[column] = field
  for (const column of data.unmapped_columns ?? []) {
    if (!(column in map)) map[column] = ''
  }
  return map
}

function refreshRow(row: EditableRow): void {
  row.type = normalizeType(row.source.type)
  row.stem = typeof row.source.stem === 'string' ? row.source.stem : ''
  row.answerText = answerToText(row.type, row.source.answer)
}

/**
 * 改列映射：把该列已识别的值从旧标准字段移到新标准字段，并同步行内展示。
 * 服务端 normalized 只保留标准字段，因此按字段搬移而不是重读原始单元格。
 */
function updateMapping(column: string, field: string): void {
  const previous = columnMap.value[column] ?? ''
  columnMap.value = { ...columnMap.value, [column]: field }
  if (previous && previous !== field) {
    for (const row of editableRows.value) {
      const value = row.source[previous]
      if (value === undefined) continue
      delete row.source[previous]
      if (field) row.source[field] = value
      refreshRow(row)
    }
  }
  confirming.value = false
}

function removeRow(row: EditableRow): void {
  row.removed = true
  confirming.value = false
}

function restoreRow(row: EditableRow): void {
  row.removed = false
  confirming.value = false
}

function handleTargetBank(value: string): void {
  targetBankId.value = value ? Number(value) : null
}

async function handleFile(next: File | null): Promise<void> {
  if (!next) return
  const ext = extensionOf(next.name)
  if (!SUPPORTED_EXT.includes(ext)) {
    error.value = '只支持 .json / .xlsx / .xls / .csv 题库文件'
    return
  }
  if (next.size > QUESTION_IMPORT_MAX_MB * 1024 * 1024) {
    error.value = `文件超过 ${QUESTION_IMPORT_MAX_MB}MB 上限，请拆分后重试`
    return
  }
  if (!props.classId) {
    error.value = '请先选择接收题库的班级'
    return
  }

  file.value = next
  preview.value = null
  inserted.value = null
  error.value = ''
  columnMap.value = {}
  editableRows.value = []
  confirming.value = false
  previewing.value = true
  try {
    const data = await questionsApi.previewImport(props.classId, next, targetBankId.value)
    preview.value = data
    columnMap.value = buildColumnMap(data)
    editableRows.value = buildRows(data)
  } catch (err) {
    error.value = importErrorMessage(err)
  } finally {
    previewing.value = false
  }
}

function importErrorMessage(err: unknown): string {
  if (isApiError(err) && err.code === 42203) {
    return err.message || '题库文件格式错误，请按模板修正后重试'
  }
  return toUserMessage(err)
}

function rowPayload(row: EditableRow): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    type: row.type,
    stem: row.stem.trim(),
    answer: textToAnswer(row.type, row.answerText),
  }
  for (const field of ['options', 'analysis', 'knowledge_tag', 'difficulty'] as const) {
    const value = row.source[field]
    if (value !== undefined) payload[field] = value
  }
  return payload
}

function startConfirm(): void {
  if (!canCommit.value) return
  error.value = ''
  confirming.value = true
}

async function commit(): Promise<void> {
  if (!preview.value || !props.classId || committing.value || !canCommit.value) return
  committing.value = true
  error.value = ''
  try {
    const result = await questionsApi.commitImport(props.classId, {
      token: preview.value.token,
      rows: hasRowModel.value ? importableRows.value.map(rowPayload) : undefined,
      bank_id: targetBankId.value,
    })
    inserted.value = result.inserted
    confirming.value = false
    emit('imported', result.inserted)
  } catch (err) {
    confirming.value = false
    error.value = importErrorMessage(err)
  } finally {
    committing.value = false
  }
}

function downloadTemplate(): void {
  const sample = [
    {
      type: 'single',
      stem: 'TCP 建立连接需要几次握手？',
      options: [
        { key: 'A', text: '一次' },
        { key: 'B', text: '两次' },
        { key: 'C', text: '三次' },
        { key: 'D', text: '四次' },
      ],
      answer: 'C',
      analysis: 'TCP 通过三次握手确认双方收发能力。',
      knowledge_tag: '传输层',
      difficulty: 'easy',
    },
    {
      type: 'multiple',
      stem: '以下属于传输层协议的是？',
      options: [
        { key: 'A', text: 'TCP' },
        { key: 'B', text: 'IP' },
        { key: 'C', text: 'UDP' },
      ],
      answer: ['A', 'C'],
      analysis: 'IP 属于网络层。',
      knowledge_tag: '传输层',
      difficulty: 'medium',
    },
    {
      type: 'judge',
      stem: 'UDP 提供可靠传输。',
      answer: false,
      analysis: 'UDP 不保证可靠交付。',
      knowledge_tag: '传输层',
      difficulty: 'easy',
    },
  ]
  const blob = new Blob([JSON.stringify(sample, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '青芽题库导入模板.json'
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <AppModal
    :model-value="modelValue"
    title="导入题目"
    description="上传 JSON / XLSX / XLS / CSV；先预览校验，确认后再写入题库。"
    width="860px"
    hide-footer
    :close-on-overlay="!previewing && !committing"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="import">
      <input
        ref="inputRef"
        class="import__input"
        type="file"
        :accept="QUESTION_IMPORT_ACCEPT"
        @change="onInputChange"
      />

      <div class="import-target">
        <div class="import-target__text">
          <span class="muted text-xs">导入到</span>
          <strong>{{ targetBankId === null ? '自动创建「导入题库-日期」' : targetBankName }}</strong>
        </div>
        <div class="import-target__switch">
          <span class="muted text-xs">切换</span>
          <AppSelect
            :model-value="targetBankId === null ? '' : String(targetBankId)"
            :options="targetBankOptions"
            :disabled="previewing || committing"
            @update:model-value="handleTargetBank"
          />
        </div>
      </div>

      <template v-if="inserted !== null">
        <section class="import-result" aria-live="polite">
          <span class="import-result__icon"><CheckCircle2 :size="30" :stroke-width="1.7" /></span>
          <div>
            <h3 class="import-result__title">题目已写入题库</h3>
            <p class="import-result__text">
              成功 <strong class="tabular">{{ inserted }}</strong> 道 · 失败
              <strong class="tabular">0</strong> 道 · 均为草稿状态，可继续编辑后组卷。
            </p>
          </div>
        </section>
        <div class="import__actions">
          <AppButton variant="ghost" @click="reset">继续导入</AppButton>
          <AppButton variant="primary" @click="close">完成</AppButton>
        </div>
      </template>

      <template v-else-if="previewing || (preview && committing)">
        <div class="import-file">
          <span class="import-file__icon"><FileJson :size="18" :stroke-width="1.8" /></span>
          <div class="grow">
            <p class="import-file__name truncate">{{ file?.name }}</p>
            <p class="import-file__meta">{{ file ? formatFileSize(file.size) : '' }}</p>
          </div>
          <AppSkeleton variant="text" width="110px" />
        </div>
        <div class="import-loading">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="3" />
          <p class="muted text-sm">正在识别表头并逐行校验题型、选项、答案与难度…</p>
        </div>
      </template>

      <template v-else-if="preview">
        <div class="import-file">
          <span class="import-file__icon"><FileJson :size="18" :stroke-width="1.8" /></span>
          <div class="grow">
            <p class="import-file__name truncate">{{ file?.name }}</p>
            <p class="import-file__meta">
              {{ file ? formatFileSize(file.size) : '' }} · 已校验 {{ preview.total }} 条
            </p>
          </div>
          <AppButton variant="ghost" size="sm" :disabled="committing" @click="reset">重新选择</AppButton>
        </div>

        <dl class="import-stats">
          <div>
            <dt>总条数</dt>
            <dd class="tabular">{{ preview.total }}</dd>
          </div>
          <div class="import-stats__ok">
            <dt>可导入</dt>
            <dd class="tabular">{{ hasRowModel ? importableRows.length : preview.valid_count }}</dd>
          </div>
          <div :class="{ 'import-stats__fail': skippedCount > 0 || preview.error_count > 0 }">
            <dt>跳过</dt>
            <dd class="tabular">{{ hasRowModel ? skippedCount : preview.error_count }}</dd>
          </div>
        </dl>

        <section v-if="sourceColumns.length > 0" class="import-mapping">
          <header class="import-mapping__head">
            <h3 class="import-mapping__title">列映射</h3>
            <span class="muted text-xs">自动识别的列可直接修改，“推测”表示按同义词或近似匹配得出</span>
          </header>
          <div class="import-mapping__grid">
            <div v-for="column in sourceColumns" :key="column" class="import-mapping__item">
              <span class="import-mapping__column truncate" :title="column">{{ column }}</span>
              <AppSelect
                :model-value="columnMap[column]"
                :options="FIELD_OPTIONS"
                :disabled="committing"
                @update:model-value="updateMapping(column, $event)"
              />
              <AppTag v-if="isGuessed(column)" tone="warning">推测</AppTag>
            </div>
          </div>
        </section>

        <section v-if="hasRowModel" class="import-rows">
          <header class="import-rows__head">
            <h3 class="import-rows__title">逐行校验</h3>
            <span class="muted text-xs">可改题型与答案、删除整行；标红行不会被导入</span>
          </header>
          <AppTable :columns="rowColumns" :rows="editableRows" row-key="key" min-width="880px">
            <template #cell-index="{ row }">
              <span class="mono tabular">{{ row.index }}</span>
            </template>
            <template #cell-type="{ row }">
              <select
                v-model="row.type"
                class="import-cell__select"
                :disabled="committing || row.removed"
                @change="confirming = false"
              >
                <option value="">未识别</option>
                <option v-for="type in QUESTION_TYPES" :key="type" :value="type">
                  {{ TYPE_LABELS[type] }}
                </option>
              </select>
            </template>
            <template #cell-stem="{ row }">
              <span class="import-cell__stem" :class="{ 'import-cell--muted': row.removed }">
                {{ row.stem || '（无题干）' }}
              </span>
            </template>
            <template #cell-answer="{ row }">
              <input
                v-model="row.answerText"
                class="import-cell__input"
                type="text"
                :disabled="committing || row.removed"
                placeholder="多选用逗号分隔"
                @input="confirming = false"
              />
            </template>
            <template #cell-state="{ row }">
              <span
                class="import-cell__state"
                :class="{
                  'import-cell__state--error': rowProblems(row).length > 0 || row.serverErrors.length > 0,
                  'import-cell__state--muted': row.removed,
                }"
              >
                {{ row.removed ? '已删除' : rowStateText(row) }}
              </span>
            </template>
            <template #cell-actions="{ row }">
              <button
                v-if="!row.removed"
                class="import-cell__link"
                type="button"
                :disabled="committing"
                @click="removeRow(row)"
              >
                删除
              </button>
              <button
                v-else
                class="import-cell__link"
                type="button"
                :disabled="committing"
                @click="restoreRow(row)"
              >
                撤销
              </button>
            </template>
          </AppTable>
        </section>

        <section v-else-if="preview.error_count > 0" class="import-errors">
          <header class="import-errors__head">
            <AppTag tone="danger" dot>有 {{ preview.error_count }} 条需修正</AppTag>
            <span class="muted text-xs">存在错误时不会写入任何题目</span>
          </header>
          <AppTable
            :columns="errorColumns"
            :rows="failures"
            :skeleton-rows="2"
            empty-title="没有错误行"
            min-width="520px"
          >
            <template #cell-row="{ row }">
              <span class="mono tabular">第 {{ row.row }} 行</span>
            </template>
            <template #cell-column="{ row }">
              <code class="import-error-field">{{ row.column }}</code>
            </template>
            <template #cell-message="{ row }">
              <span class="import-error-message">{{ row.message }}</span>
            </template>
          </AppTable>
        </section>

        <p v-if="error" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ error }}</span>
        </p>

        <div v-if="confirming" class="import-confirm" role="alertdialog" aria-live="assertive">
          <strong class="import-confirm__title">
            将导入 {{ importableRows.length }} 题，跳过 {{ skippedCount }} 题
          </strong>
          <p class="import-confirm__text">
            跳过包含已删除行与校验未通过行；导入后可在题库继续编辑。
          </p>
        </div>

        <div class="import__actions">
          <AppButton variant="ghost" :disabled="committing" @click="reset">放弃</AppButton>
          <template v-if="!confirming">
            <AppButton variant="primary" :disabled="!canCommit" @click="startConfirm">
              {{ canCommit ? '确认导入' : '修正错误后再导入' }}
            </AppButton>
          </template>
          <template v-else>
            <AppButton variant="ghost" :disabled="committing" @click="confirming = false">取消</AppButton>
            <AppButton variant="primary" :loading="committing" @click="commit">确认写入</AppButton>
          </template>
        </div>
      </template>

      <template v-else>
        <div
          class="import-drop"
          :class="{ 'import-drop--active': dragActive }"
          role="button"
          tabindex="0"
          aria-label="上传题库文件：点击选择或拖拽到此处"
          @click="chooseFile"
          @keydown.enter.prevent="chooseFile"
          @keydown.space.prevent="chooseFile"
          @dragenter="onDragEnter"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
        >
          <span class="import-drop__icon"><UploadCloud :size="26" :stroke-width="1.7" /></span>
          <p class="import-drop__title">{{ dragActive ? '松开即可校验' : '拖拽题库文件到这里' }}</p>
          <p class="import-drop__sub">
            或 <span class="link">选择文件</span> · 支持 JSON / XLSX / XLS / CSV · 单文件不超过
            {{ QUESTION_IMPORT_MAX_MB }}MB · 单次最多 500 题
          </p>
          <p class="import-drop__hint">表头可用中文同义词；仅需「题干 + 答案」，其余列自动识别。</p>
          <button class="import-template" type="button" @click.stop="downloadTemplate">
            <Download :size="14" :stroke-width="1.8" />
            下载 JSON 示例模板
          </button>
        </div>

        <p v-if="error" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ error }}</span>
        </p>

        <div v-if="!classId" class="import-warn">
          <AlertCircle :size="16" :stroke-width="1.9" />
          请先在页面顶部选择要导入的班级
        </div>
      </template>

      <p v-if="inserted === null && preview && preview.error_count > 0 && !hasRowModel" class="import-note">
        修正文件中的行号与字段后重新上传，即可继续导入。
      </p>
      <p v-else-if="inserted === null && !preview && !previewing && file" class="import-note">
        正在等待预览结果。
      </p>
    </div>
  </AppModal>
</template>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.import__input {
  display: none;
}

.import-target {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.import-target__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.import-target__text strong {
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}

.import-target__switch {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 280px;
  max-width: 100%;
}

.import-target__switch :deep(.app-select) {
  flex: 1;
}

.import-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-6) var(--sp-5);
  border: 2px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
  text-align: center;
  cursor: pointer;
  transition: border-color 170ms ease-out, background-color 170ms ease-out;
}

.import-drop:hover,
.import-drop--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.import-drop__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 22%, transparent);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-primary);
}

.import-drop__title {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.import-drop__sub {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.import-drop__hint {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.import-template {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: var(--sp-2);
  padding: 5px var(--sp-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.import-template:hover {
  border-color: var(--color-primary);
}

.import-file {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.import-file__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.import-file__name {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.import-file__meta {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.import-loading {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-2) 0;
}

.import-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-3);
}

.import-stats div {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.import-stats dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.import-stats dd {
  margin-top: 2px;
  font-size: var(--fs-xl);
  font-weight: 600;
}

.import-stats__ok dd {
  color: var(--color-success);
}

.import-stats__fail dd {
  color: var(--color-danger);
}

.import-mapping,
.import-rows {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.import-rows :deep(.app-table__scroll) {
  max-height: min(52vh, 460px);
  overflow: auto;
}

.import-rows :deep(table) {
  table-layout: fixed;
}

.import-rows :deep(tbody td) {
  height: 56px;
  vertical-align: middle;
}

.import-rows :deep(thead th) {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--color-surface);
}

.import-rows :deep(thead th:first-child),
.import-rows :deep(tbody td:first-child) {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--color-surface);
}

.import-rows :deep(thead th:first-child) {
  z-index: 3;
}

.import-rows :deep(tbody tr.app-table__row--striped td:first-child) {
  background: var(--color-surface-alt);
}

.import-rows :deep(tbody tr:has(.import-cell__state--error)) td {
  background: color-mix(in srgb, var(--color-danger) 5%, var(--color-surface));
}

.import-rows :deep(tbody tr:has(.import-cell__state--error)) td:first-child {
  background: color-mix(in srgb, var(--color-danger) 5%, var(--color-surface));
  box-shadow: inset 3px 0 0 var(--color-danger);
}

.import-rows :deep(tbody tr:has(.import-cell__state--error):hover td) {
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
}

.import-mapping__head,
.import-rows__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.import-mapping__title,
.import-rows__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.import-mapping__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: var(--sp-2) var(--sp-3);
  max-height: 180px;
  overflow-y: auto;
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.import-mapping__item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
}

.import-mapping__column {
  flex: 0 0 72px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.import-cell__select,
.import-cell__input {
  width: 100%;
  height: 30px;
  padding: 0 var(--sp-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-xs);
}

.import-cell__select:focus,
.import-cell__input:focus {
  border-color: var(--color-primary);
}

.import-cell__stem {
  display: block;
  font-size: var(--fs-sm);
  line-height: 1.5;
  white-space: normal;
  overflow-wrap: anywhere;
}

.import-cell--muted {
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.import-cell__state {
  display: block;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
  white-space: normal;
  word-break: break-word;
}

.import-cell__state--error {
  color: var(--color-danger);
}

.import-cell__state--muted {
  color: var(--color-text-muted);
}

.import-cell__link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.import-cell__link:disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.import-errors {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  border: 1px solid color-mix(in srgb, var(--color-danger) 24%, transparent);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.import-errors__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  background: color-mix(in srgb, var(--color-danger) 5%, var(--color-surface));
}

.import-error-field {
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
  color: var(--color-danger);
  font-family: var(--font-mono);
  font-size: 11px;
}

.import-error-message {
  color: var(--color-danger);
  font-size: var(--fs-sm);
}

.import-result {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-4);
  padding: var(--sp-5);
  border: 1px solid color-mix(in srgb, var(--color-success) 25%, transparent);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-success) 6%, var(--color-surface));
}

.import-result__icon {
  display: inline-flex;
  color: var(--color-success);
}

.import-result__title {
  font-size: var(--fs-lg);
}

.import-result__text {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.import-result__text strong {
  color: var(--color-success);
}

.import-confirm {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 7%, var(--color-surface));
}

.import-confirm__title {
  color: var(--color-warning);
  font-size: var(--fs-sm);
}

.import-confirm__text {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.import__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.import-note,
.import-warn {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.import-warn {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-warning);
}
</style>
