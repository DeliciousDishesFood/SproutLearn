<!-- 班级详情：邀请码面板 + 学生 / 文档 / 切片三个 Tab。 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  ExternalLink,
  FileText,
  Layers3,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import ChunkPreviewList from '@/components/business/ChunkPreviewList.vue'
import InviteCodePanel from '@/components/business/InviteCodePanel.vue'
import StudentTable from '@/components/business/StudentTable.vue'
import { isApiError } from '@/api/client'
import { botApi } from '@/api/bot'
import { knowledgeApi } from '@/api/knowledge'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import type {
  BotConfig,
  BotTestResult,
  KnowledgeChunk,
  KnowledgeDocListItem,
} from '@/api/types'
import type { DocStatusValue, TableColumn } from '@/types'
import {
  DOC_STATUS_META,
  PAGE_SIZE,
  PAGE_SIZE_MAX,
  PAGE_SIZE_OPTIONS,
} from '@/utils/constants'
import { formatDateTime, formatFileSize } from '@/utils/format'

type TabKey = 'students' | 'documents' | 'chunks'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const tab = ref<TabKey>('students')
const booting = ref(true)
const studentsLoaded = ref(false)
const documentsLoaded = ref(false)
const chunksLoaded = ref(false)

const studentKeyword = ref('')
const studentPage = ref(1)
const studentPageSize = ref(PAGE_SIZE)

const documents = ref<KnowledgeDocListItem[]>([])
const docTotal = ref(0)
const docPage = ref(1)
const docPageSize = ref(PAGE_SIZE)
const docStatus = ref('')
const docLoading = ref(false)
const docError = ref('')
const deleteTarget = ref<KnowledgeDocListItem | null>(null)
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const chunkDocOptions = ref<KnowledgeDocListItem[]>([])
const selectedDocId = ref('')
const chunks = ref<KnowledgeChunk[]>([])
const chunkTotal = ref(0)
const chunkPage = ref(1)
const chunkPageSize = ref(PAGE_SIZE)
const chunkLoading = ref(false)
const chunkError = ref('')

const botConfig = ref<BotConfig | null>(null)
const botLoading = ref(false)
const botLoadError = ref('')
const botSaving = ref(false)
const botTesting = ref(false)
const botError = ref('')
const botTest = ref<BotTestResult | null>(null)
const botForm = reactive({
  appId: '',
  appSecret: '',
  callbackUrl: '',
  enabled: false,
})

const classId = computed(() => Number(route.params.id))
const classDetail = computed(() => classStore.currentClass)
const classError = computed(() => classStore.currentError)
const classLoading = computed(() => booting.value || classStore.currentLoading)

const tabs: { key: TabKey; label: string; icon: typeof UsersRound }[] = [
  { key: 'students', label: '学生', icon: UsersRound },
  { key: 'documents', label: '文档', icon: FileText },
  { key: 'chunks', label: '切片预览', icon: Layers3 },
]

const docColumns: TableColumn[] = [
  { key: 'title', title: '文档' },
  { key: 'file_ext', title: '类型', width: '82px' },
  { key: 'file_size', title: '大小', width: '96px', align: 'right' },
  { key: 'chunk_count', title: '切片', width: '78px', align: 'right' },
  { key: 'status', title: '状态', width: '104px' },
  { key: 'created_at', title: '上传时间', width: '150px' },
  { key: 'actions', title: '操作', width: '148px', align: 'right' },
]

const docStatusOptions = [
  { label: '全部状态', value: '' },
  ...Object.entries(DOC_STATUS_META).map(([value, meta]) => ({
    label: meta.label,
    value,
  })),
]

const chunkDocOptionsFormatted = computed(() =>
  chunkDocOptions.value.map((doc) => ({
    label: `${doc.title}（${doc.chunk_count} 个切片）`,
    value: String(doc.id),
    disabled: doc.status !== 2,
  })),
)

const selectedChunkDoc = computed(
  () => chunkDocOptions.value.find((doc) => String(doc.id) === selectedDocId.value) ?? null,
)

function docMeta(status: number): { label: string; tone: 'neutral' | 'warning' | 'success' | 'danger' } {
  return DOC_STATUS_META[status as DocStatusValue] ?? DOC_STATUS_META[0]
}

const botStatus = computed<{ label: string; tone: 'neutral' | 'success' | 'danger' }>(() => {
  if (!botConfig.value?.app_id) return { label: '未配置', tone: 'neutral' }
  if (botConfig.value.last_check_status === 'ok') return { label: '连接正常', tone: 'success' }
  if (botConfig.value.last_check_status === 'failed') return { label: '连接失败', tone: 'danger' }
  return { label: '未测试', tone: 'neutral' }
})

const botSecretHint = computed(() =>
  botConfig.value?.has_secret
    ? `已保存，末 4 位 ${botConfig.value.secret_tail || '****'}；留空表示不修改`
    : '首次保存必须填写 AppSecret，保存后不再回显',
)

const botLastCheck = computed(() => {
  const config = botConfig.value
  if (!config?.last_check_at) return ''
  const status =
    config.last_check_status === 'ok'
      ? '连接正常'
      : config.last_check_status === 'failed'
        ? '连接失败'
        : '未测试'
  return `上次测试 ${formatDateTime(config.last_check_at)} · ${status}`
})

function resetBotState(): void {
  botConfig.value = null
  botLoadError.value = ''
  botError.value = ''
  botTest.value = null
  botForm.appId = ''
  botForm.appSecret = ''
  botForm.callbackUrl = ''
  botForm.enabled = false
}

async function loadBotConfig(): Promise<void> {
  if (!Number.isFinite(classId.value) || classId.value <= 0) return
  botLoading.value = true
  botLoadError.value = ''
  try {
    const config = await botApi.get(classId.value)
    botConfig.value = config
    botForm.appId = config.app_id ?? ''
    botForm.callbackUrl = config.callback_url ?? ''
    botForm.enabled = config.enabled
    botForm.appSecret = ''
  } catch (err) {
    botLoadError.value = isApiError(err) ? err.friendlyMessage : '机器人配置暂时无法加载'
  } finally {
    botLoading.value = false
  }
}

async function saveBot(): Promise<void> {
  if (botSaving.value) return
  botError.value = ''
  const appId = botForm.appId.trim()
  if (!appId) {
    botError.value = '请填写 AppID'
    return
  }
  if (!botConfig.value?.has_secret && !botForm.appSecret.trim()) {
    botError.value = '首次保存必须填写 AppSecret'
    return
  }
  botSaving.value = true
  try {
    const config = await botApi.save(classId.value, {
      app_id: appId,
      app_secret: botForm.appSecret.trim() || undefined,
      callback_url: botForm.callbackUrl.trim() || null,
      enabled: botForm.enabled,
    })
    botConfig.value = config
    botForm.appId = config.app_id ?? ''
    botForm.callbackUrl = config.callback_url ?? ''
    botForm.enabled = config.enabled
    botForm.appSecret = ''
    botTest.value = null
    ui.success('机器人配置已保存')
  } catch (err) {
    botError.value = isApiError(err) ? err.friendlyMessage : '保存失败，请稍后重试'
  } finally {
    botSaving.value = false
  }
}

async function testBot(): Promise<void> {
  if (botTesting.value) return
  botError.value = ''
  botTest.value = null
  if (!botConfig.value?.has_secret) {
    botError.value = '请先保存机器人配置，再测试连接'
    return
  }
  botTesting.value = true
  try {
    const result = await botApi.test(classId.value)
    botTest.value = result
    if (botConfig.value) {
      botConfig.value.last_check_at = result.last_check_at
      botConfig.value.last_check_status = result.last_check_status
    }
    if (result.ok) ui.success('连接成功')
  } catch (err) {
    botError.value = isApiError(err) ? err.friendlyMessage : '测试连接失败，请稍后重试'
  } finally {
    botTesting.value = false
  }
}

function resetTabState(): void {
  studentsLoaded.value = false
  documentsLoaded.value = false
  chunksLoaded.value = false
  tab.value = 'students'
  studentKeyword.value = ''
  studentPage.value = 1
  studentPageSize.value = PAGE_SIZE
  documents.value = []
  docTotal.value = 0
  docPage.value = 1
  docPageSize.value = PAGE_SIZE
  docStatus.value = ''
  docError.value = ''
  chunkDocOptions.value = []
  selectedDocId.value = ''
  chunks.value = []
  chunkTotal.value = 0
  chunkPage.value = 1
  chunkError.value = ''
  resetBotState()
}

async function loadClass(): Promise<void> {
  if (!Number.isFinite(classId.value) || classId.value <= 0) return
  try {
    await classStore.fetchDetail(classId.value)
  } catch {
    // classStore.currentError 负责展示
  }
}

async function loadStudents(page = studentPage.value, size = studentPageSize.value, keyword = studentKeyword.value): Promise<void> {
  studentPage.value = page
  studentPageSize.value = size
  studentKeyword.value = keyword
  studentsLoaded.value = true
  try {
    await classStore.fetchStudents(classId.value, { page, pageSize: size, keyword })
  } catch {
    // store.studentsError 负责展示
  }
}

function handleStudentSearch(keyword: string): void {
  void loadStudents(1, studentPageSize.value, keyword)
}

function handleStudentPagination(page: number, size: number): void {
  void loadStudents(page, size, studentKeyword.value)
}

async function loadDocuments(page = docPage.value): Promise<void> {
  if (!Number.isFinite(classId.value)) return
  docLoading.value = true
  docError.value = ''
  try {
    const status = docStatus.value ? Number(docStatus.value) : undefined
    const result = await knowledgeApi.listDocuments({
      class_id: classId.value,
      status,
      page,
      page_size: docPageSize.value,
    })
    documents.value = result.list
    docTotal.value = result.total
    docPage.value = result.page
    docPageSize.value = result.page_size
    documentsLoaded.value = true
  } catch (err) {
    docError.value = err instanceof Error ? err.message : '文档列表暂时无法加载'
  } finally {
    docLoading.value = false
  }
}

function handleDocStatusChange(value: string): void {
  docStatus.value = value
  void loadDocuments(1)
}

function handleDocPagination(page: number, size: number): void {
  docPageSize.value = size
  void loadDocuments(page)
}

function openDoc(doc: KnowledgeDocListItem): void {
  void router.push({
    path: `/teacher/knowledge/${doc.id}`,
    query: { class_id: String(classId.value) },
  })
}

function goUpload(): void {
  void router.push({ path: '/teacher/knowledge', query: { class_id: String(classId.value) } })
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
    if (documents.value.length === 1 && docPage.value > 1) {
      docPage.value -= 1
    }
    await loadDocuments(docPage.value)
    if (classDetail.value) {
      await classStore.fetchDetail(classId.value, true).catch(() => undefined)
    }
    if (chunksLoaded.value) {
      await loadChunkDocs()
    }
  } catch (err) {
    if (isApiError(err)) {
      deleteError.value = err.friendlyMessage
    } else {
      deleteError.value = '删除失败，请稍后重试'
    }
  } finally {
    deleting.value = false
  }
}

async function loadChunkDocs(): Promise<void> {
  try {
    const result = await knowledgeApi.listDocuments({
      class_id: classId.value,
      page: 1,
      page_size: PAGE_SIZE_MAX,
    })
    chunkDocOptions.value = result.list
    chunkError.value = ''
    if (!selectedDocId.value && result.list.length > 0) {
      const preferred = result.list.find((doc) => doc.status === 2) ?? result.list[0]
      selectedDocId.value = String(preferred.id)
    }
    if (
      selectedDocId.value &&
      !result.list.some((doc) => String(doc.id) === selectedDocId.value)
    ) {
      selectedDocId.value = result.list.length > 0 ? String(result.list[0].id) : ''
    }
  } catch (err) {
    chunkError.value = err instanceof Error ? err.message : '文档列表暂时无法加载'
  }
}

async function loadChunks(page = chunkPage.value): Promise<void> {
  const docId = Number(selectedDocId.value)
  if (!Number.isFinite(docId) || docId <= 0) {
    chunks.value = []
    chunkTotal.value = 0
    return
  }
  chunkLoading.value = true
  chunkError.value = ''
  try {
    const result = await knowledgeApi.chunks(docId, {
      page,
      page_size: chunkPageSize.value,
    })
    chunks.value = result.list
    chunkTotal.value = result.total
    chunkPage.value = result.page
  } catch (err) {
    chunkError.value = err instanceof Error ? err.message : '切片暂时无法加载'
  } finally {
    chunkLoading.value = false
  }
}

async function ensureChunksTab(): Promise<void> {
  if (!chunksLoaded.value) {
    chunksLoaded.value = true
    await loadChunkDocs()
    await loadChunks(1)
  } else if (!chunks.value.length && selectedDocId.value) {
    await loadChunks(chunkPage.value)
  }
}

function handleChunkDocChange(value: string): void {
  selectedDocId.value = value
  chunkPage.value = 1
  void loadChunks(1)
}

function handleChunkPage(page: number): void {
  void loadChunks(page)
}

async function ensureTabData(): Promise<void> {
  if (booting.value || !classDetail.value) return
  if (tab.value === 'students' && !studentsLoaded.value) {
    await loadStudents(1, studentPageSize.value, studentKeyword.value)
  } else if (tab.value === 'documents' && !documentsLoaded.value) {
    await loadDocuments(1)
  } else if (tab.value === 'chunks') {
    await ensureChunksTab()
  }
}

async function bootstrap(): Promise<void> {
  booting.value = true
  classStore.resetCurrent()
  resetTabState()
  deleteOpen.value = false
  deleteTarget.value = null
  deleteError.value = ''
  await loadClass()
  booting.value = false
  if (classDetail.value) {
    await loadStudents(1, studentPageSize.value, '')
    await loadBotConfig()
  }
}

function backToClasses(): void {
  void router.push('/teacher/classes')
}

watch(tab, () => {
  void ensureTabData()
})

watch(
  () => route.params.id,
  () => {
    if (route.name === 'teacher-class-detail') void bootstrap()
  },
)

onMounted(bootstrap)
</script>

<template>
  <div class="page detail-page">
    <div v-if="classLoading" class="detail-skeleton">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="2" width="46%" />
      </div>
      <div class="detail-skeleton__grid">
        <div class="panel panel-body">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="4" />
        </div>
        <div class="panel panel-body">
          <AppSkeleton variant="stat" />
        </div>
      </div>
    </div>

    <div v-else-if="classError || !classDetail" class="panel">
      <AppEmpty error title="无法打开这个班级" :description="classError || '班级不存在或已被删除。'">
        <template #action>
          <div class="row">
            <AppButton variant="ghost" @click="loadClass">
              <RefreshCw :size="15" :stroke-width="1.8" />
              重试
            </AppButton>
            <AppButton variant="secondary" @click="backToClasses">
              <ArrowLeft :size="15" :stroke-width="1.8" />
              返回班级列表
            </AppButton>
          </div>
        </template>
      </AppEmpty>
    </div>

    <template v-else>
      <header class="class-hero">
        <div class="class-hero__top">
          <router-link to="/teacher/classes" class="back-link">
            <ArrowLeft :size="15" :stroke-width="1.9" />
            我的班级
          </router-link>
          <span class="class-hero__code">
            班级编号
            <strong class="mono">{{ classDetail.class_code }}</strong>
          </span>
        </div>

        <div class="class-hero__main">
          <div class="class-hero__copy">
            <p class="eyebrow">CLASSROOM</p>
            <h2 class="class-hero__name">{{ classDetail.class_name }}</h2>
            <p class="class-hero__course">{{ classDetail.course_name }}</p>
            <p class="class-hero__meta">
              {{ classDetail.student_count }} 名学生 · {{ classDetail.doc_count }} 份文档 ·
              {{ classDetail.created_at }} 创建
            </p>
          </div>

          <div class="class-hero__actions">
            <router-link :to="{ path: '/teacher/knowledge', query: { class_id: String(classId) } }">
              <AppButton variant="primary">
                <UploadCloud :size="16" :stroke-width="1.9" />
                上传文档
              </AppButton>
            </router-link>
            <AppButton variant="ghost" @click="backToClasses">
              班级列表
              <ArrowRight :size="15" :stroke-width="1.8" />
            </AppButton>
          </div>
        </div>
      </header>

      <div class="detail-layout">
        <main class="detail-main">
          <nav class="detail-tabs" role="tablist" aria-label="班级内容">
            <button
              v-for="item in tabs"
              :key="item.key"
              class="detail-tab"
              :class="{ 'detail-tab--active': tab === item.key }"
              type="button"
              role="tab"
              :aria-selected="tab === item.key"
              @click="tab = item.key"
            >
              <component :is="item.icon" :size="16" :stroke-width="1.8" aria-hidden="true" />
              {{ item.label }}
            </button>
          </nav>

          <section v-if="tab === 'students'" class="detail-panel" role="tabpanel">
            <StudentTable
              :students="classStore.students"
              :loading="classStore.studentsLoading"
              :total="classStore.studentsTotal"
              :page="classStore.studentsPage"
              :page-size="classStore.studentsPageSize"
              :keyword="classStore.studentsKeyword"
              :error="classStore.studentsError"
              @search="handleStudentSearch"
              @pagination-change="handleStudentPagination"
              @refresh="loadStudents(classStore.studentsPage, classStore.studentsPageSize, classStore.studentsKeyword)"
            />
          </section>

          <section v-else-if="tab === 'documents'" class="detail-panel" role="tabpanel">
            <div class="panel">
              <header class="panel-head doc-toolbar">
                <div>
                  <h3 class="section-title">班级文档</h3>
                  <p class="section-note">上传成功后即可查看切片，解析失败可删除重传。</p>
                </div>
                <div class="doc-toolbar__actions">
                  <AppSelect
                    v-model="docStatus"
                    :options="docStatusOptions"
                    id="doc-status-filter"
                    @change="handleDocStatusChange"
                  />
                  <AppButton variant="secondary" size="sm" @click="goUpload">
                    <Plus :size="15" :stroke-width="2" />
                    上传文档
                  </AppButton>
                </div>
              </header>

              <div v-if="docError" class="doc-error">
                <AppEmpty error title="文档列表暂时无法加载" :description="docError">
                  <template #action>
                    <AppButton variant="secondary" size="sm" @click="loadDocuments(docPage)">
                      <RefreshCw :size="14" :stroke-width="1.8" />
                      重新加载
                    </AppButton>
                  </template>
                </AppEmpty>
              </div>

              <AppTable
                v-else
                :columns="docColumns"
                :rows="documents"
                :loading="docLoading"
                :skeleton-rows="6"
                empty-title="这个班级还没有文档"
                empty-description="上传课件或讲义后，青芽会自动整理成可预览的知识切片。"
              >
                <template #cell-title="{ row }">
                  <button class="doc-title" type="button" @click="openDoc(row)">
                    <FileText :size="15" :stroke-width="1.7" aria-hidden="true" />
                    <span class="truncate">{{ row.title }}</span>
                  </button>
                </template>
                <template #cell-file_ext="{ row }">
                  <span class="file-ext mono">{{ row.file_ext.toUpperCase() }}</span>
                </template>
                <template #cell-file_size="{ row }">
                  <span class="muted tabular">{{ formatFileSize(row.file_size) }}</span>
                </template>
                <template #cell-chunk_count="{ row }">
                  <span class="tabular">{{ row.chunk_count }}</span>
                </template>
                <template #cell-status="{ row }">
                  <AppTag :tone="docMeta(row.status).tone" dot>{{ docMeta(row.status).label }}</AppTag>
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
                  <AppButton variant="secondary" size="sm" @click="goUpload">
                    <UploadCloud :size="15" :stroke-width="1.9" />
                    上传第一份文档
                  </AppButton>
                </template>
              </AppTable>

              <AppPagination
                v-if="docTotal > 0"
                :total="docTotal"
                :page="docPage"
                :page-size="docPageSize"
                :page-size-options="PAGE_SIZE_OPTIONS"
                @change="handleDocPagination"
              />
            </div>
          </section>

          <section v-else class="detail-panel" role="tabpanel">
            <div class="panel chunk-panel">
              <header class="panel-head chunk-panel__head">
                <div>
                  <h3 class="section-title">切片预览</h3>
                  <p class="section-note">切片内容超过 400 字符会折叠，展开后可核对完整文本。</p>
                </div>
                <div class="chunk-doc-picker">
                  <AppSelect
                    v-model="selectedDocId"
                    label="选择文档"
                    placeholder="请选择文档"
                    :options="chunkDocOptionsFormatted"
                    :disabled="chunkDocOptions.length === 0"
                    @change="handleChunkDocChange"
                  />
                </div>
              </header>

              <div class="chunk-panel__body">
                <ChunkPreviewList
                  :chunks="chunks"
                  :loading="chunkLoading"
                  :total="chunkTotal"
                  :page="chunkPage"
                  :page-size="chunkPageSize"
                  :error="chunkError"
                  @update:page="handleChunkPage"
                  @retry="loadChunks(chunkPage)"
                />
              </div>
            </div>
          </section>
        </main>

        <aside class="detail-aside">
          <InviteCodePanel
            :class-id="classId"
            :invite-code="classDetail.invite_code"
            :class-code="classDetail.class_code"
            @updated="classStore.fetchDetail(classId, true).catch(() => undefined)"
          />

          <section class="aside-note">
            <p class="eyebrow">TEACHING NOTE</p>
            <h3 class="aside-note__title">让学生知道为什么</h3>
            <p>
              邀请码只负责“进门”。真正留住学生的，是每次课上都能找到的那一份资料。
              上传前替文档起一个清楚的标题，也替学生省下三分钟。
            </p>
          </section>
        </aside>
      </div>

      <section class="bot-section" aria-labelledby="bot-title">
        <header class="bot-head">
          <div class="bot-head__copy">
            <span class="bot-head__icon" aria-hidden="true">
              <Bot :size="19" :stroke-width="1.8" />
            </span>
            <div>
              <h3 id="bot-title" class="section-title">QQ 机器人</h3>
              <p class="section-note">
                保存 AppID / Secret 并做一次凭证连通性测试。机器人需在 QQ 开放平台申请，由外部 AstrBot 运行。
              </p>
            </div>
          </div>
          <AppTag :tone="botStatus.tone" dot>{{ botStatus.label }}</AppTag>
        </header>

        <div class="bot-layout">
          <form class="panel bot-form" @submit.prevent="saveBot">
            <div v-if="botLoadError" class="bot-load-error">
              <p class="form-error" role="alert">
                <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
                <span>{{ botLoadError }}</span>
              </p>
              <AppButton variant="secondary" size="sm" type="button" @click="loadBotConfig">
                <RefreshCw :size="14" :stroke-width="1.8" />
                重新加载
              </AppButton>
            </div>

            <template v-else>
              <p v-if="!botLoading && !botConfig?.app_id" class="bot-empty">
                尚未保存机器人配置。填写下方信息并保存后，这里会显示最近一次测试状态。
              </p>

              <AppInput
                v-model="botForm.appId"
                label="AppID"
                placeholder="QQ 开放平台应用详情中的 AppID"
                :disabled="botLoading || botSaving"
                :maxlength="64"
              />
              <AppInput
                v-model="botForm.appSecret"
                type="password"
                label="AppSecret"
                :placeholder="botConfig?.has_secret ? '已保存，留空不修改' : '填写 AppSecret'"
                :hint="botSecretHint"
                :disabled="botLoading || botSaving"
                :maxlength="512"
              />
              <AppInput
                v-model="botForm.callbackUrl"
                label="回调地址"
                placeholder="https://your-server.example.com/qq/callback"
                :disabled="botLoading || botSaving"
                :maxlength="255"
              />

              <div class="bot-switch-row">
                <div>
                  <p class="bot-switch-row__label">启用机器人</p>
                  <p class="bot-switch-row__hint">关闭后，学生绑定仍沿用原有鉴权方式。</p>
                </div>
                <button
                  type="button"
                  class="bot-switch"
                  :class="{ 'bot-switch--on': botForm.enabled }"
                  role="switch"
                  :aria-checked="botForm.enabled"
                  aria-label="启用机器人"
                  :disabled="botLoading || botSaving"
                  @click="botForm.enabled = !botForm.enabled"
                >
                  <span class="bot-switch__thumb" />
                </button>
              </div>

              <p v-if="botLastCheck" class="bot-last-check">{{ botLastCheck }}</p>

              <p v-if="botError" class="form-error" role="alert">
                <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
                <span>{{ botError }}</span>
              </p>

              <div class="bot-actions">
                <AppButton type="submit" :loading="botSaving" :disabled="botLoading">
                  保存配置
                </AppButton>
                <AppButton
                  variant="secondary"
                  type="button"
                  :loading="botTesting"
                  :disabled="botLoading || botSaving || !botConfig?.has_secret"
                  @click="testBot"
                >
                  测试连接
                </AppButton>
                <span v-if="!botConfig?.has_secret" class="bot-actions__hint">保存后可测试</span>
              </div>

              <div
                v-if="botTest"
                class="bot-result"
                :class="botTest.ok ? 'bot-result--ok' : 'bot-result--failed'"
                role="status"
              >
                <p class="bot-result__title">
                  <CheckCircle2
                    v-if="botTest.ok"
                    :size="17"
                    :stroke-width="1.9"
                    aria-hidden="true"
                  />
                  <AlertCircle v-else :size="17" :stroke-width="1.9" aria-hidden="true" />
                  {{ botTest.ok ? '连接成功' : '连接失败' }}
                </p>
                <p
                  v-if="botTest.message && botTest.message !== (botTest.ok ? '连接成功' : '连接失败')"
                  class="bot-result__message"
                >
                  {{ botTest.message }}
                </p>
                <p class="bot-result__meta">
                  <span v-if="botTest.ok && botTest.expires_in !== null">
                    access_token 有效期 {{ botTest.expires_in }} 秒
                  </span>
                  <span v-if="botTest.last_check_at">
                    测试时间 {{ formatDateTime(botTest.last_check_at) }}
                  </span>
                </p>
              </div>
            </template>
          </form>

          <aside class="bot-steps">
            <p class="eyebrow">SETUP GUIDE</p>
            <h4 class="bot-steps__title">四步接入</h4>
            <ol class="bot-steps__list">
              <li>
                <span class="bot-steps__index">1</span>
                <div>
                  <strong>去开放平台建应用</strong>
                  <p>在 QQ 开放平台创建机器人应用，获取 AppID 与 AppSecret。</p>
                </div>
              </li>
              <li>
                <span class="bot-steps__index">2</span>
                <div>
                  <strong>填 AppID / Secret</strong>
                  <p>AppSecret 保存后不再回显，留空表示不修改。</p>
                </div>
              </li>
              <li>
                <span class="bot-steps__index">3</span>
                <div>
                  <strong>配回调地址</strong>
                  <p>填写外部机器人服务接收事件的回调地址。</p>
                </div>
              </li>
              <li>
                <span class="bot-steps__index">4</span>
                <div>
                  <strong>启用并测试</strong>
                  <p>保存后点「测试连接」，确认凭证能换到 access_token。</p>
                </div>
              </li>
            </ol>
            <router-link class="bot-steps__link" to="/docs/qq-bot-setup">
              查看完整配置文档
              <ExternalLink :size="14" :stroke-width="1.8" />
            </router-link>
            <p class="bot-steps__note">平台不代申请机器人，也不托管机器人进程。</p>
          </aside>
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
      <p class="delete-target">
        {{ deleteTarget?.title || '未选择文档' }}
      </p>
      <p v-if="deleteError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ deleteError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.detail-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.detail-skeleton__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--sp-4);
}

.class-hero {
  padding: var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 96% 8%, color-mix(in srgb, var(--color-accent) 9%, transparent) 0, transparent 34%),
    var(--color-surface);
  box-shadow: var(--shadow-1);
}

.class-hero__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-4);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.back-link:hover {
  color: var(--color-primary);
}

.class-hero__code {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  letter-spacing: 0.04em;
}

.class-hero__code strong {
  margin-left: 4px;
  color: var(--color-text);
  font-size: var(--fs-sm);
  letter-spacing: 0.08em;
}

.class-hero__main {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
}

.class-hero__name {
  font-size: var(--fs-2xl);
}

.class-hero__course {
  margin-top: 2px;
  color: var(--color-primary);
  font-size: var(--fs-base);
  font-weight: 600;
}

.class-hero__meta {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.class-hero__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-shrink: 0;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--sp-4);
  align-items: start;
}

.detail-main {
  min-width: 0;
}

.detail-tabs {
  display: flex;
  gap: var(--sp-1);
  padding: 0 0 var(--sp-3);
  border-bottom: 1px solid var(--color-border);
}

.detail-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 var(--sp-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  font-weight: 500;
  transition: color 160ms ease-out, background-color 160ms ease-out;
}

.detail-tab:hover {
  color: var(--color-text);
  background: var(--color-surface-alt);
}

.detail-tab--active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: 600;
}

.detail-panel {
  margin-top: var(--sp-4);
}

.doc-toolbar {
  flex-wrap: wrap;
}

.doc-toolbar__actions {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-2);
}

.doc-toolbar__actions :deep(.app-select) {
  min-width: 150px;
  gap: var(--sp-1);
}

.doc-toolbar__actions :deep(.app-select__element) {
  min-height: 34px;
  padding-top: 5px;
  padding-bottom: 5px;
  font-size: var(--fs-sm);
}

.doc-error {
  min-height: 260px;
}

.doc-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text);
  font-size: var(--fs-sm);
  text-align: left;
}

.doc-title:hover {
  color: var(--color-primary);
}

.doc-title svg {
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.file-ext {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 10px;
  letter-spacing: 0.04em;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
  border-radius: var(--radius-xs);
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

.chunk-panel {
  overflow: hidden;
}

.chunk-panel__head {
  align-items: flex-end;
  flex-wrap: wrap;
}

.chunk-doc-picker {
  width: 280px;
}

.chunk-panel__body {
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
}

.aside-note {
  margin-top: var(--sp-4);
  padding: var(--sp-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.aside-note__title {
  margin-bottom: var(--sp-2);
  font-size: var(--fs-base);
}

.aside-note p:last-child {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
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

.delete-open-error {
  margin-top: var(--sp-3);
}

.bot-section {
  margin-top: var(--sp-5);
  padding-top: var(--sp-5);
  border-top: 1px solid var(--color-border);
}

.bot-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-4);
}

.bot-head__copy {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  min-width: 0;
}

.bot-head__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  background: var(--color-primary);
}

.bot-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--sp-4);
  align-items: start;
}

.bot-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-5);
}

.bot-load-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.bot-empty {
  padding: var(--sp-3);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.bot-switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.bot-switch-row__label {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bot-switch-row__hint {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.bot-switch {
  position: relative;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
  padding: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: 999px;
  background: var(--color-surface);
  transition: background-color 160ms ease-out, border-color 160ms ease-out;
}

.bot-switch__thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: var(--color-text-muted);
  transition: transform 160ms ease-out, background-color 160ms ease-out;
}

.bot-switch--on {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.bot-switch--on .bot-switch__thumb {
  background: var(--color-text-inverse);
  transform: translateX(20px);
}

.bot-switch:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.bot-last-check {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bot-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.bot-actions__hint {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bot-result {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.bot-result--ok {
  border-color: color-mix(in srgb, var(--color-success) 34%, var(--color-border));
  background: color-mix(in srgb, var(--color-success) 8%, var(--color-surface));
}

.bot-result--failed {
  border-color: color-mix(in srgb, var(--color-danger) 32%, var(--color-border));
  background: color-mix(in srgb, var(--color-danger) 7%, var(--color-surface));
}

.bot-result__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bot-result--ok .bot-result__title {
  color: var(--color-success);
}

.bot-result--failed .bot-result__title {
  color: var(--color-danger);
}

.bot-result__message {
  margin-top: var(--sp-2);
  font-size: var(--fs-sm);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.bot-result__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bot-steps {
  padding: var(--sp-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.bot-steps__title {
  margin: 2px 0 var(--sp-3);
  font-size: var(--fs-base);
}

.bot-steps__list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.bot-steps__list li {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
}

.bot-steps__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 999px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: 10px;
  font-weight: 700;
}

.bot-steps__list strong {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bot-steps__list p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.55;
}

.bot-steps__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--sp-4);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bot-steps__note {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .bot-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1100px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .detail-aside {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--sp-4);
    align-items: start;
  }

  .aside-note {
    margin-top: 0;
  }
}

@media (max-width: 760px) {
  .class-hero__main {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-aside {
    grid-template-columns: 1fr;
  }

  .chunk-doc-picker {
    width: 100%;
  }
}
</style>
