<!-- 文档详情：元信息 + 切片预览（分页），展示解析失败原因并支持删除重传。 -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  FileText,
  Layers3,
  RefreshCw,
  Trash2,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import ChunkPreviewList from '@/components/business/ChunkPreviewList.vue'
import { knowledgeApi } from '@/api/knowledge'
import { toUserMessage } from '@/api/client'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import type { KnowledgeChunk, KnowledgeDocDetail } from '@/api/types'
import type { DocStatusValue } from '@/types'
import { DOC_STATUS_META, PAGE_SIZE } from '@/utils/constants'
import { formatDateTime, formatFileSize, formatNumber } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const doc = ref<KnowledgeDocDetail | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')

const chunks = ref<KnowledgeChunk[]>([])
const chunkTotal = ref(0)
const chunkPage = ref(1)
const chunkPageSize = ref(PAGE_SIZE)
const chunksLoading = ref(false)
const chunksError = ref('')

const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const docId = computed(() => Number(route.params.docId))
const classId = computed(() => {
  const raw = route.query.class_id
  const value = Array.isArray(raw) ? raw[0] : raw
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
})
const statusMeta = computed(() => {
  if (!doc.value) return DOC_STATUS_META[0]
  return DOC_STATUS_META[doc.value.status as DocStatusValue] ?? DOC_STATUS_META[0]
})
const isReady = computed(() => doc.value?.status === 2)
const isFailed = computed(() => doc.value?.status === 3)
const knowledgeLink = computed(() => ({
  path: '/teacher/knowledge',
  query: classId.value ? { class_id: String(classId.value) } : {},
}))

async function loadDetail(silent = false): Promise<void> {
  if (!Number.isFinite(docId.value) || docId.value <= 0) {
    error.value = '文档编号无效，请返回知识库重新选择'
    return
  }
  if (!silent && doc.value === null) loading.value = true
  if (silent) refreshing.value = true
  error.value = ''
  try {
    doc.value = await knowledgeApi.detail(docId.value)
  } catch (err) {
    error.value = toUserMessage(err)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function loadChunks(nextPage = chunkPage.value): Promise<void> {
  if (!Number.isFinite(docId.value) || docId.value <= 0) return
  chunksLoading.value = true
  chunksError.value = ''
  try {
    const result = await knowledgeApi.chunks(docId.value, {
      page: nextPage,
      page_size: chunkPageSize.value,
    })
    chunks.value = result.list
    chunkTotal.value = result.total
    chunkPage.value = result.page
    chunkPageSize.value = result.page_size
  } catch (err) {
    chunksError.value = toUserMessage(err)
  } finally {
    chunksLoading.value = false
  }
}

function handleChunkPage(nextPage: number): void {
  chunkPage.value = nextPage
  void loadChunks(nextPage)
}

async function refreshAll(): Promise<void> {
  refreshing.value = true
  await loadDetail(true)
  if (doc.value) await loadChunks(chunkPage.value)
  else chunks.value = []
  refreshing.value = false
}

function goBack(): void {
  void router.push(knowledgeLink.value)
}

function openDelete(): void {
  deleteError.value = ''
  deleteOpen.value = true
}

async function confirmDelete(): Promise<void> {
  if (deleting.value || !doc.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await knowledgeApi.remove(doc.value.id)
    ui.success('文档已删除')
    deleteOpen.value = false
    await classStore.fetchAllClasses().catch(() => undefined)
    goBack()
  } catch (err) {
    deleteError.value = toUserMessage(err)
  } finally {
    deleting.value = false
  }
}

async function bootstrap(): Promise<void> {
  doc.value = null
  chunks.value = []
  chunkTotal.value = 0
  chunkPage.value = 1
  chunksError.value = ''
  error.value = ''
  await loadDetail()
  if (doc.value) await loadChunks(1)
}

watch(
  () => route.params.docId,
  (next, previous) => {
    if (next !== previous) void bootstrap()
  },
)

onMounted(bootstrap)
</script>

<template>
  <div class="page knowledge-detail-page">
    <button class="back-link" type="button" @click="goBack">
      <ArrowLeft :size="15" :stroke-width="1.9" aria-hidden="true" />
      返回知识库
    </button>

    <div v-if="loading" class="content-stack" aria-busy="true">
      <section class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="3" />
      </section>
      <section class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="table" :rows="5" />
      </section>
    </div>

    <div v-else-if="error" class="panel">
      <AppEmpty error title="文档详情暂时无法加载" :description="error">
        <template #action>
          <div class="row">
            <AppButton variant="secondary" @click="loadDetail()">
              <RefreshCw :size="15" :stroke-width="1.8" />
              重新加载
            </AppButton>
            <AppButton variant="ghost" @click="goBack">返回知识库</AppButton>
          </div>
        </template>
      </AppEmpty>
    </div>

    <template v-else-if="doc">
      <header class="page-head detail-head">
        <div class="page-head__text">
          <p class="eyebrow">DOCUMENT DETAIL</p>
          <div class="split-title">
            <h2 class="page-title">{{ doc.title }}</h2>
            <AppTag :tone="statusMeta.tone" dot>{{ statusMeta.label }}</AppTag>
          </div>
          <p class="page-subtitle">
            共 <span class="tabular">{{ formatNumber(doc.chunk_count) }}</span> 个知识切片，
            上传于 {{ formatDateTime(doc.created_at) }}。
          </p>
        </div>
        <div class="detail-actions">
          <AppButton variant="ghost" :loading="refreshing" @click="refreshAll">
            <RefreshCw v-if="!refreshing" :size="15" :stroke-width="1.8" />
            刷新
          </AppButton>
          <AppButton variant="danger-outline" @click="openDelete">
            <Trash2 :size="15" :stroke-width="1.8" />
            删除文档
          </AppButton>
        </div>
      </header>

      <section class="panel doc-meta" aria-labelledby="doc-meta-title">
        <header class="panel-head">
          <div>
            <h3 id="doc-meta-title" class="section-title">文档信息</h3>
            <p class="section-note">元信息用于核对入库内容，切片正文会在下方分页展示。</p>
          </div>
        </header>
        <div class="panel-body">
          <dl class="meta-grid">
            <div class="meta-item">
              <dt><BookOpen :size="14" :stroke-width="1.8" aria-hidden="true" /> 所属课程</dt>
              <dd>{{ doc.course_name || '—' }}</dd>
            </div>
            <div class="meta-item">
              <dt><FileText :size="14" :stroke-width="1.8" aria-hidden="true" /> 原始文件</dt>
              <dd class="meta-break" :title="doc.file_name">{{ doc.file_name }}</dd>
            </div>
            <div class="meta-item">
              <dt>文件格式</dt>
              <dd><span class="file-ext mono">{{ doc.file_ext.toUpperCase() }}</span></dd>
            </div>
            <div class="meta-item">
              <dt>文件大小</dt>
              <dd class="tabular">{{ formatFileSize(doc.file_size) }}</dd>
            </div>
            <div class="meta-item">
              <dt>页数</dt>
              <dd class="tabular">{{ doc.page_count ?? '—' }}</dd>
            </div>
            <div class="meta-item">
              <dt><Layers3 :size="14" :stroke-width="1.8" aria-hidden="true" /> 切片数量</dt>
              <dd class="tabular">{{ formatNumber(doc.chunk_count) }}</dd>
            </div>
          </dl>
        </div>
      </section>

      <div v-if="isFailed" class="parse-alert parse-alert--danger" role="alert">
        <span class="parse-alert__icon">
          <AlertCircle :size="18" :stroke-width="1.8" aria-hidden="true" />
        </span>
        <div class="parse-alert__copy">
          <strong>文档解析失败</strong>
          <p>{{ doc.error_message || '请检查文件内容后删除重传。' }}</p>
        </div>
        <AppButton variant="danger-outline" size="sm" @click="openDelete">删除重传</AppButton>
      </div>

      <div v-else-if="!isReady" class="parse-alert" role="status">
        <span class="parse-alert__icon">
          <RefreshCw :size="17" :stroke-width="1.8" aria-hidden="true" />
        </span>
        <div class="parse-alert__copy">
          <strong>{{ statusMeta.label }}</strong>
          <p>解析在服务端进行，完成后刷新本页即可查看切片。</p>
        </div>
        <AppButton variant="ghost" size="sm" @click="refreshAll">刷新状态</AppButton>
      </div>

      <section class="panel chunks-panel" aria-labelledby="chunks-title">
        <header class="panel-head">
          <div>
            <h3 id="chunks-title" class="section-title">知识切片</h3>
            <p class="section-note">正文超过 400 字符时默认折叠，可展开逐段核对切分质量。</p>
          </div>
          <AppTag tone="neutral">第 {{ chunkPage }} 页</AppTag>
        </header>
        <div class="panel-body">
          <ChunkPreviewList
            :chunks="chunks"
            :loading="chunksLoading"
            :total="chunkTotal"
            :page="chunkPage"
            :page-size="chunkPageSize"
            :error="chunksError"
            @update:page="handleChunkPage"
            @retry="loadChunks(chunkPage)"
          />
        </div>
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
      <p class="delete-target">{{ doc?.title || '未选择文档' }}</p>
      <p v-if="deleteError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ deleteError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.knowledge-detail-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.back-link:hover {
  color: var(--color-primary);
}

.detail-head {
  align-items: flex-end;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.doc-meta,
.chunks-panel {
  overflow: hidden;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-4);
}

.meta-item {
  min-width: 0;
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.meta-item dt {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.meta-item dd {
  color: var(--color-text);
  font-size: var(--fs-sm);
  font-weight: 600;
  line-height: 1.6;
}

.meta-break {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.file-ext {
  display: inline-block;
  padding: 1px 6px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 10px;
  letter-spacing: 0.04em;
}

.parse-alert {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-warning) 28%, transparent);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-warning) 6%, var(--color-surface));
}

.parse-alert--danger {
  border-color: color-mix(in srgb, var(--color-danger) 28%, transparent);
  background: color-mix(in srgb, var(--color-danger) 6%, var(--color-surface));
}

.parse-alert__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
}

.parse-alert--danger .parse-alert__icon {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
}

.parse-alert__copy {
  min-width: 0;
  flex: 1;
  line-height: 1.6;
}

.parse-alert__copy strong {
  font-size: var(--fs-sm);
}

.parse-alert__copy p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.parse-alert > .app-button {
  flex-shrink: 0;
}

.chunks-panel :deep(.chunk-preview__foot) {
  padding-bottom: var(--sp-1);
}

.delete-target {
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}

@media (max-width: 1023px) {
  .meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .detail-head {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--sp-4);
  }

  .detail-actions {
    width: 100%;
  }

  .detail-actions :deep(.app-button) {
    flex: 1;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }

  .parse-alert {
    flex-wrap: wrap;
  }

  .parse-alert > :deep(.app-button) {
    width: 100%;
  }
}
</style>
