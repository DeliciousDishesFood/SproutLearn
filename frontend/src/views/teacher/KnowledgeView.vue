<!-- 知识库：班级切换、批量拖拽上传、上传进度与成功/失败清单、文档表格。 -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  FileText,
  Layers3,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import UploadDropzone from '@/components/business/UploadDropzone.vue'
import UploadResultList from '@/components/business/UploadResultList.vue'
import { knowledgeApi } from '@/api/knowledge'
import { toUserMessage } from '@/api/client'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import { useUpload } from '@/composables/useUpload'
import type { KnowledgeDocListItem } from '@/api/types'
import type { DocStatusValue, TableColumn } from '@/types'
import {
  DOC_STATUS_META,
  PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
} from '@/utils/constants'
import { formatDateTime, formatFileSize, formatNumber } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const {
  uploading,
  progress,
  result: uploadResult,
  error: uploadError,
  upload: runUpload,
  reset: resetUpload,
} = useUpload()

const selectedClassId = ref('')
const documents = ref<KnowledgeDocListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const statusFilter = ref('')
const docsLoading = ref(false)
const docsError = ref('')

const deleteTarget = ref<KnowledgeDocListItem | null>(null)
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const uploadSectionRef = ref<HTMLElement | null>(null)

const classOptions = computed(() =>
  classStore.classes.map((item) => ({
    label: `${item.class_name} · ${item.course_name}`,
    value: String(item.id),
  })),
)
const selectedClass = computed(
  () => classStore.classes.find((item) => String(item.id) === selectedClassId.value) ?? null,
)
const docStatusOptions = [
  { label: '全部状态', value: '' },
  ...Object.entries(DOC_STATUS_META).map(([value, meta]) => ({
    label: meta.label,
    value,
  })),
]

const columns: TableColumn[] = [
  { key: 'title', title: '文档' },
  { key: 'file_ext', title: '类型', width: '80px' },
  { key: 'file_size', title: '大小', width: '96px', align: 'right' },
  { key: 'status', title: '状态', width: '104px' },
  { key: 'chunk_count', title: '切片', width: '78px', align: 'right' },
  { key: 'page_count', title: '页数', width: '72px', align: 'right' },
  { key: 'created_at', title: '上传时间', width: '150px' },
  { key: 'actions', title: '操作', width: '132px', align: 'right' },
]

function docMeta(status: number): { label: string; tone: 'neutral' | 'warning' | 'success' | 'danger' } {
  return DOC_STATUS_META[status as DocStatusValue] ?? DOC_STATUS_META[0]
}

async function loadDocuments(nextPage = page.value): Promise<void> {
  if (!selectedClassId.value) return
  docsLoading.value = true
  docsError.value = ''
  try {
    const result = await knowledgeApi.listDocuments({
      class_id: Number(selectedClassId.value),
      status: statusFilter.value ? Number(statusFilter.value) : undefined,
      page: nextPage,
      page_size: pageSize.value,
    })
    documents.value = result.list
    total.value = result.total
    page.value = result.page
    pageSize.value = result.page_size
  } catch (err) {
    docsError.value = toUserMessage(err)
  } finally {
    docsLoading.value = false
  }
}

function syncClassQuery(): void {
  void router.replace({
    query: {
      ...route.query,
      class_id: selectedClassId.value,
    },
  })
}

async function handleClassChange(value: string): Promise<void> {
  if (value === selectedClassId.value) return
  selectedClassId.value = value
  statusFilter.value = ''
  page.value = 1
  documents.value = []
  total.value = 0
  docsError.value = ''
  resetUpload()
  syncClassQuery()
  await loadDocuments(1)
}

function handleStatusChange(value: string): void {
  statusFilter.value = value
  page.value = 1
  void loadDocuments(1)
}

function handlePagination(nextPage: number, size: number): void {
  pageSize.value = size
  void loadDocuments(nextPage)
}

async function handleFiles(files: File[]): Promise<void> {
  if (!selectedClassId.value || uploading.value) return
  const outcome = await runUpload(Number(selectedClassId.value), files)
  if (!outcome) return
  ui.success(`上传完成：成功 ${outcome.success_list.length} 份，失败 ${outcome.fail_list.length} 份`)
  await loadDocuments(1)
}

function openDoc(doc: KnowledgeDocListItem): void {
  void router.push({
    path: `/teacher/knowledge/${doc.id}`,
    query: { class_id: selectedClassId.value },
  })
}

function openDocById(docId: number): void {
  const doc = documents.value.find((item) => item.id === docId)
  if (doc) {
    openDoc(doc)
    return
  }
  void router.push({
    path: `/teacher/knowledge/${docId}`,
    query: { class_id: selectedClassId.value },
  })
}

function askDelete(doc: KnowledgeDocListItem): void {
  deleteTarget.value = doc
  deleteError.value = ''
  deleteOpen.value = true
}

async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await knowledgeApi.remove(deleteTarget.value.id)
    ui.success('文档已删除')
    deleteOpen.value = false
    deleteTarget.value = null
    if (documents.value.length === 1 && page.value > 1) page.value -= 1
    await loadDocuments(page.value)
    await classStore.fetchAllClasses().catch(() => undefined)
  } catch (err) {
    deleteError.value = toUserMessage(err)
  } finally {
    deleting.value = false
  }
}

function scrollToUpload(): void {
  uploadSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function retryUpload(): void {
  resetUpload()
  scrollToUpload()
}

async function bootstrap(): Promise<void> {
  try {
    await classStore.fetchAllClasses()
  } catch {
    return
  }
  if (classStore.classes.length === 0) return

  const queryId = Number(route.query.class_id)
  const matched = classStore.classes.find((item) => item.id === queryId)
  selectedClassId.value = String(matched ? matched.id : classStore.classes[0].id)
  if (!matched) syncClassQuery()
  await loadDocuments(1)
}

watch(selectedClassId, () => {
  resetUpload()
})

onMounted(bootstrap)
</script>

<template>
  <div class="page knowledge-page">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">KNOWLEDGE BASE</p>
        <h2 class="page-title">知识库</h2>
        <p class="page-subtitle">把课件、讲义与课程文档交给青芽，解析为可以逐段回看的知识切片。</p>
      </div>
    </header>

    <div v-if="classStore.loading" class="content-stack">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="3" />
      </div>
      <div class="panel panel-body">
        <AppSkeleton variant="table" :rows="5" />
      </div>
    </div>

    <div v-else-if="classStore.error" class="panel">
      <AppEmpty error title="班级数据暂时无法加载" :description="classStore.error">
        <template #action>
          <AppButton variant="secondary" @click="bootstrap">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </div>

    <div v-else-if="classStore.classes.length === 0" class="panel">
      <AppEmpty
        title="还没有可以上传资料的班级"
        description="知识库按班级归档。先创建一个班级，再邀请学生一起开始。"
      >
        <template #action>
          <router-link to="/teacher/classes">
            <AppButton variant="primary">
              <Plus :size="16" :stroke-width="2" />
              创建班级
            </AppButton>
          </router-link>
        </template>
      </AppEmpty>
    </div>

    <template v-else>
      <section ref="uploadSectionRef" class="panel upload-panel">
        <header class="panel-head upload-panel__head">
          <div>
            <h3 class="section-title">上传课程文档</h3>
            <p class="section-note">单个文件独立解析，部分失败不会影响其他文档入库。</p>
          </div>
          <div class="class-picker">
            <AppSelect
              :model-value="selectedClassId"
              label="接收班级"
              :options="classOptions"
              :disabled="uploading"
              @update:model-value="handleClassChange"
            />
          </div>
        </header>

        <div class="panel-body upload-panel__body">
          <UploadDropzone
            :disabled="uploading"
            :hint="selectedClass ? `将归档到「${selectedClass.class_name}」· ${selectedClass.course_name}` : ''"
            @files="handleFiles"
          />

          <div v-if="uploading" class="upload-progress" aria-live="polite">
            <div class="upload-progress__head">
              <span class="upload-progress__label">
                <UploadCloud :size="15" :stroke-width="1.9" aria-hidden="true" />
                正在上传并解析
              </span>
              <span class="upload-progress__percent tabular">{{ progress }}%</span>
            </div>
            <div
              class="upload-progress__track"
              role="progressbar"
              :aria-valuenow="progress"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <span class="upload-progress__bar" :style="{ width: `${progress}%` }" />
            </div>
            <p class="upload-progress__note">解析会在服务端完成，请保持页面打开。</p>
          </div>

          <p v-if="uploadError" class="form-error" role="alert">
            <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ uploadError }}</span>
          </p>

          <UploadResultList
            v-if="uploadResult"
            :result="uploadResult"
            @open-doc="openDocById"
            @retry="retryUpload"
          />
        </div>
      </section>

      <section class="panel docs-panel">
        <header class="panel-head docs-panel__head">
          <div>
            <h3 class="section-title">课程文档</h3>
            <p class="section-note">
              共 <span class="tabular">{{ formatNumber(total) }}</span> 份 · 按上传时间倒序
            </p>
          </div>
          <div class="docs-panel__tools">
            <AppSelect
              :model-value="statusFilter"
              :options="docStatusOptions"
              id="docs-status-filter"
              @update:model-value="handleStatusChange"
            />
            <AppButton variant="ghost" size="sm" @click="loadDocuments(page)">
              <RefreshCw :size="14" :stroke-width="1.8" />
              刷新
            </AppButton>
          </div>
        </header>

        <div v-if="docsError" class="docs-error">
          <AppEmpty error title="文档列表暂时无法加载" :description="docsError">
            <template #action>
              <AppButton variant="secondary" size="sm" @click="loadDocuments(page)">
                <RefreshCw :size="14" :stroke-width="1.8" />
                重新加载
              </AppButton>
            </template>
          </AppEmpty>
        </div>

        <template v-else>
          <AppTable
            :columns="columns"
            :rows="documents"
            :loading="docsLoading"
            :skeleton-rows="6"
            empty-title="这个班级还没有文档"
            empty-description="上传第一份课件后，解析完成的切片会出现在这里。"
          >
            <template #cell-title="{ row }">
              <button class="doc-title" type="button" @click="openDoc(row)">
                <span class="doc-title__icon">
                  <FileText :size="15" :stroke-width="1.7" aria-hidden="true" />
                </span>
                <span class="doc-title__copy">
                  <span class="truncate">{{ row.title }}</span>
                  <small v-if="row.error_message" class="doc-title__error truncate" :title="row.error_message">
                    {{ row.error_message }}
                  </small>
                </span>
              </button>
            </template>
            <template #cell-file_ext="{ row }">
              <span class="file-ext mono">{{ row.file_ext.toUpperCase() }}</span>
            </template>
            <template #cell-file_size="{ row }">
              <span class="muted tabular">{{ formatFileSize(row.file_size) }}</span>
            </template>
            <template #cell-status="{ row }">
              <AppTag :tone="docMeta(row.status).tone" dot>{{ docMeta(row.status).label }}</AppTag>
            </template>
            <template #cell-chunk_count="{ row }">
              <span class="tabular">{{ row.chunk_count }}</span>
            </template>
            <template #cell-page_count="{ row }">
              <span class="muted tabular">{{ row.page_count ?? '—' }}</span>
            </template>
            <template #cell-created_at="{ row }">
              <span class="muted">{{ formatDateTime(row.created_at) }}</span>
            </template>
            <template #cell-actions="{ row }">
              <div class="row-actions">
                <button class="text-action" type="button" @click="openDoc(row)">
                  <Layers3 :size="14" :stroke-width="1.8" />
                  切片
                </button>
                <button class="text-action text-action--danger" type="button" @click="askDelete(row)">
                  <Trash2 :size="14" :stroke-width="1.8" />
                  删除
                </button>
              </div>
            </template>
            <template #empty-action>
              <AppButton variant="secondary" size="sm" @click="scrollToUpload">
                <UploadCloud :size="15" :stroke-width="1.9" />
                上传第一份文档
              </AppButton>
            </template>
          </AppTable>

          <AppPagination
            v-if="total > 0"
            :total="total"
            :page="page"
            :page-size="pageSize"
            :page-size-options="PAGE_SIZE_OPTIONS"
            @change="handlePagination"
          />
        </template>
      </section>
    </template>

    <AppModal
      v-model="deleteOpen"
      title="删除这份文档？"
      description="文档及其全部切片会被一并删除，磁盘文件也会清理；此操作不可撤销。"
      confirm-text="删除文档"
      confirm-variant="danger"
      :confirm-loading="deleting"
      width="440px"
      @confirm="confirmDelete"
    >
      <p class="delete-target">{{ deleteTarget?.title || '未选择文档' }}</p>
      <p v-if="deleteError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ deleteError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.upload-panel,
.docs-panel {
  overflow: hidden;
}

.upload-panel__head {
  flex-wrap: wrap;
}

.upload-panel__body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.class-picker {
  width: 290px;
}

.upload-progress {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-border));
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
}

.upload-progress__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  margin-bottom: var(--sp-2);
}

.upload-progress__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.upload-progress__percent {
  color: var(--color-primary);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.upload-progress__track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.upload-progress__bar {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width 160ms ease-out;
}

.upload-progress__note {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.docs-panel__head {
  flex-wrap: wrap;
  gap: var(--sp-3);
}

.docs-panel__tools {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.docs-panel__tools :deep(.app-select) {
  min-width: 136px;
  gap: var(--sp-1);
}

.docs-panel__tools :deep(.app-select__element) {
  min-height: 34px;
  padding-top: 5px;
  padding-bottom: 5px;
  font-size: var(--fs-sm);
}

.docs-error {
  min-height: 260px;
}

.doc-title {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  color: var(--color-text);
}

.doc-title:hover {
  color: var(--color-primary);
}

.doc-title__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.doc-title__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.4;
}

.doc-title__error {
  max-width: 320px;
  color: var(--color-danger);
  font-size: 11px;
}

.file-ext {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-border);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: 10px;
  letter-spacing: 0.04em;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-2);
  flex-wrap: nowrap;
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.text-action:hover {
  background: var(--color-primary-soft);
}

.text-action--danger {
  color: var(--color-danger);
}

.text-action--danger:hover {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}

.delete-target {
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text);
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}

@media (max-width: 720px) {
  .class-picker {
    width: 100%;
  }

  .docs-panel__tools {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
