<!-- 题库导入：JSON/XLSX 拖拽预览、逐行错误、确认落库与结果汇总。 -->
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
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { questionsApi } from '@/api/questions'
import { QUESTION_IMPORT_ACCEPT, QUESTION_IMPORT_MAX_MB } from '@/utils/constants'
import { formatFileSize } from '@/utils/format'
import type { QuestionImportError, QuestionImportPreview } from '@/api/types'
import type { TableColumn } from '@/types'

const props = defineProps<{
  modelValue: boolean
  classId: number | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'imported', count: number): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragDepth = ref(0)
const dragActive = ref(false)
const file = ref<File | null>(null)
const previewing = ref(false)
const committing = ref(false)
const preview = ref<QuestionImportPreview | null>(null)
const inserted = ref<number | null>(null)
const error = ref('')

const errorColumns: TableColumn[] = [
  { key: 'row', title: '行号', width: '76px' },
  { key: 'column', title: '字段', width: '120px' },
  { key: 'message', title: '原因' },
]

const canCommit = computed(
  () => Boolean(preview.value && preview.value.error_count === 0 && preview.value.valid_count > 0),
)
const failures = computed<QuestionImportError[]>(() => preview.value?.errors ?? [])

function reset(): void {
  file.value = null
  preview.value = null
  inserted.value = null
  error.value = ''
  previewing.value = false
  committing.value = false
  dragDepth.value = 0
  dragActive.value = false
  if (inputRef.value) inputRef.value.value = ''
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) reset()
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

async function handleFile(next: File | null): Promise<void> {
  if (!next) return
  const ext = extensionOf(next.name)
  if (!['json', 'xlsx'].includes(ext)) {
    error.value = '只支持 .json 或 .xlsx 题库文件'
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
  previewing.value = true
  try {
    preview.value = await questionsApi.previewImport(props.classId, next)
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

async function commit(): Promise<void> {
  if (!preview.value || !props.classId || committing.value || !canCommit.value) return
  committing.value = true
  error.value = ''
  try {
    const result = await questionsApi.commitImport(props.classId, preview.value.token)
    inserted.value = result.inserted
    emit('imported', result.inserted)
  } catch (err) {
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
    description="上传 JSON 或 XLSX；先预览校验，确认后再写入题库。"
    width="780px"
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
          <p class="muted text-sm">正在逐行校验题型、选项、答案与难度…</p>
        </div>
      </template>

      <template v-else-if="preview">
        <div class="import-file">
          <span class="import-file__icon"><FileJson :size="18" :stroke-width="1.8" /></span>
          <div class="grow">
            <p class="import-file__name truncate">{{ file?.name }}</p>
            <p class="import-file__meta">{{ file ? formatFileSize(file.size) : '' }} · 已校验 {{ preview.total }} 条</p>
          </div>
          <AppButton variant="ghost" size="sm" :disabled="committing" @click="reset">重新选择</AppButton>
        </div>

        <dl class="import-stats">
          <div>
            <dt>总条数</dt>
            <dd class="tabular">{{ preview.total }}</dd>
          </div>
          <div class="import-stats__ok">
            <dt>成功</dt>
            <dd class="tabular">{{ preview.valid_count }}</dd>
          </div>
          <div :class="{ 'import-stats__fail': preview.error_count > 0 }">
            <dt>失败</dt>
            <dd class="tabular">{{ preview.error_count }}</dd>
          </div>
        </dl>

        <section v-if="preview.error_count > 0" class="import-errors">
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

        <div class="import__actions">
          <AppButton variant="ghost" :disabled="committing" @click="reset">放弃</AppButton>
          <AppButton
            variant="primary"
            :loading="committing"
            :disabled="!canCommit"
            @click="commit"
          >
            {{ canCommit ? `确认导入 ${preview.valid_count} 道题` : '修正错误后再导入' }}
          </AppButton>
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
            或 <span class="link">选择文件</span> · 支持 JSON / XLSX · 单文件不超过
            {{ QUESTION_IMPORT_MAX_MB }}MB · 单次最多 500 题
          </p>
          <p class="import-drop__hint">JSON 需为题目对象数组；XLSX 固定列见导入模板。</p>
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

      <p v-if="inserted === null && preview && preview.error_count > 0" class="import-note">
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
