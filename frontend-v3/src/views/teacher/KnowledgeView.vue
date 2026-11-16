<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, X } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import DocCard from '@/components/business/DocCard.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { knowledgeApi } from '@/api/knowledge'
import { toUserMessage } from '@/api/client'
import { formatFileSize } from '@/utils/format'
import { UPLOAD_ACCEPT, UPLOAD_MAX_MB } from '@/utils/constants'
import type { KnowledgeDocListItem, UploadResult } from '@/api/contract'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const ui = useUiStore()
const toast = useToast()

const classId = computed(() => Number(route.params.classId))
const docs = ref<KnowledgeDocListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const status = ref<number | null>(null)
const loading = ref(true)
const errorText = ref('')

const files = ref<File[]>([])
const courseName = ref('')
const uploading = ref(false)
const progress = ref(0)
const uploadResult = ref<UploadResult | null>(null)
const uploadError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

const statusChips = [
  { key: 'all', label: '全部', value: null },
  { key: '0', label: '待处理', value: 0 },
  { key: '1', label: '解析中', value: 1 },
  { key: '2', label: '可预览', value: 2 },
  { key: '3', label: '解析失败', value: 3 },
]

const activeChip = computed(() => (status.value === null ? 'all' : String(status.value)))

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await knowledgeApi.listDocuments({
      class_id: classId.value,
      status: status.value ?? undefined,
      page: page.value,
      page_size: pageSize,
    })
    docs.value = result.list
    total.value = result.total
    ui.setCurrentClassId(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

function selectStatus(value: number | null): void {
  status.value = value
  page.value = 1
  void load()
}

function addFiles(list: FileList | File[] | null): void {
  if (!list) return
  const incoming = Array.from(list)
  const maxBytes = UPLOAD_MAX_MB * 1024 * 1024
  const tooLarge = incoming.filter((file) => file.size > maxBytes)
  const exists = new Set(files.value.map((file) => `${file.name}-${file.size}`))
  const accepted = incoming.filter(
    (file) => file.size <= maxBytes && !exists.has(`${file.name}-${file.size}`),
  )
  files.value = [...files.value, ...accepted]
  uploadResult.value = null
  uploadError.value = tooLarge.length
    ? `以下文件超过 ${UPLOAD_MAX_MB}MB，已跳过：${tooLarge.map((file) => file.name).join('、')}`
    : ''
}

function pickFiles(): void {
  fileInput.value?.click()
}

function onFiles(event: Event): void {
  const input = event.target as HTMLInputElement
  addFiles(input.files)
  input.value = ''
}

function onDragOver(): void {
  dragging.value = true
}

function dropFiles(event: DragEvent): void {
  dragging.value = false
  addFiles(event.dataTransfer?.files ?? null)
}

function removeFile(index: number): void {
  files.value.splice(index, 1)
}

async function upload(): Promise<void> {
  if (files.value.length === 0) {
    uploadError.value = '请先选择要上传的文件'
    return
  }
  uploading.value = true
  progress.value = 0
  uploadResult.value = null
  uploadError.value = ''
  try {
    const result = await knowledgeApi.upload(
      {
        class_id: classId.value,
        course_name: courseName.value.trim() || undefined,
        files: files.value,
      },
      (percent) => {
        progress.value = percent
      },
    )
    uploadResult.value = result
    files.value = []
    if (fileInput.value) fileInput.value.value = ''
    if (result.success_list.length > 0) toast.success(`成功上传 ${result.success_list.length} 个文件`)
    await load()
  } catch (error) {
    uploadError.value = toUserMessage(error)
  } finally {
    uploading.value = false
  }
}

async function removeDoc(item: KnowledgeDocListItem): Promise<void> {
  if (!window.confirm(`确定删除《${item.title}》吗？切片会一并删除。`)) return
  try {
    await knowledgeApi.remove(item.id)
    toast.success('文档已删除')
    if (docs.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (error) {
    toast.error(toUserMessage(error))
  }
}

watch(page, () => void load())

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> · 知识库
      </p>
      <h1>知识库</h1>
      <p class="page-head__lede">上传课程资料，系统会解析并切片，讲评与问答都会引用这里的内容。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/classes/${classId}/banks`">去题库</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <BaseCard title="上传资料" meta="支持多文件，部分失败不影响其余文件">
    <div class="form" style="margin-top: 12px">
      <BaseField label="课程名称（选填）" hint="不填则使用班级课程名称">
        <input v-model="courseName" class="input" type="text" placeholder="例如 Python 程序设计" />
      </BaseField>

      <input
        ref="fileInput"
        class="upload-input"
        type="file"
        multiple
        :accept="UPLOAD_ACCEPT"
        @change="onFiles"
      />

      <div class="stack" style="gap: 10px">
        <button
          class="upload-zone"
          :class="{ 'is-dragging': dragging }"
          type="button"
          @click="pickFiles"
          @dragover.prevent="onDragOver"
          @dragleave.prevent="dragging = false"
          @drop.prevent="dropFiles"
        >
          <Upload :size="20" aria-hidden="true" />
          <strong>点击选择文件，或把资料拖到这里</strong>
          <p class="small tertiary">支持 PDF / Word / PPT / Markdown / TXT，单个不超过 {{ UPLOAD_MAX_MB }}MB。</p>
          <p class="small tertiary">扫描件无文字层会解析失败。</p>
          <span v-if="files.length" class="badge badge--lime">已选 {{ files.length }} 个文件</span>
        </button>

        <div v-if="files.length" class="upload-files">
          <div v-for="(file, index) in files" :key="`${file.name}-${file.size}-${index}`" class="upload-file">
            <span class="upload-file__name">{{ file.name }} · {{ formatFileSize(file.size) }}</span>
            <button
              class="upload-file__remove"
              type="button"
              :aria-label="`移除 ${file.name}`"
              @click="removeFile(index)"
            >
              <X :size="14" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="uploading" class="stack" style="gap: 6px">
        <div class="progress__bar"><i :style="{ width: `${progress}%` }" /></div>
        <span class="small tertiary">上传中 {{ progress }}%</span>
      </div>
      <p v-if="uploadError" class="form-error">{{ uploadError }}</p>

      <div v-if="uploadResult" class="stack" style="gap: 8px">
        <p class="notice notice--lime">
          本次共 {{ uploadResult.total }} 个文件，成功 {{ uploadResult.success_list.length }} 个，失败
          {{ uploadResult.fail_list.length }} 个。
        </p>
        <div v-if="uploadResult.fail_list.length" class="notice notice--danger">
          <p class="strong">失败清单</p>
          <ul style="margin: 6px 0 0; padding-left: 18px">
            <li v-for="fail in uploadResult.fail_list" :key="fail.file_name">
              {{ fail.file_name }}：{{ fail.error_message }}（{{ fail.error_code }}）
            </li>
          </ul>
        </div>
        <ul v-if="uploadResult.success_list.length" class="small muted" style="margin: 0; padding-left: 18px">
          <li v-for="ok in uploadResult.success_list" :key="ok.doc_id">
            {{ ok.file_name }} · {{ ok.chunk_count }} 个切片
          </li>
        </ul>
      </div>

      <div class="row">
        <BaseButton variant="primary" :loading="uploading" @click="upload">上传并解析</BaseButton>
        <span class="small tertiary">部分失败会逐个列出原因，不会整批回滚。</span>
      </div>
    </div>
  </BaseCard>

  <section class="card">
    <header class="card__head">
      <h2>资料列表</h2>
      <span class="card__meta">共 {{ total }} 份</span>
    </header>
    <div class="chips">
      <button
        v-for="chip in statusChips"
        :key="chip.key"
        class="chip"
        :class="{ 'is-active': activeChip === chip.key }"
        type="button"
        @click="selectStatus(chip.value)"
      >
        {{ chip.label }}
      </button>
    </div>

    <p v-if="loading" class="loading-line">正在读取资料…</p>
    <EmptyState
      v-else-if="docs.length === 0"
      title="这里还没有资料"
      description="上传第一份课程资料后，系统会自动解析并切片。"
    />
    <div v-else class="grid-2">
      <DocCard
        v-for="item in docs"
        :key="item.id"
        :item="item"
        :class-id="classId"
        @delete="removeDoc"
      />
    </div>
    <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
  </section>
</template>
