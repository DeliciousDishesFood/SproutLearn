<!-- 教师工作台：班级/学生/文档/切片统计 + 最近文档 + 快捷入口。 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ArrowUpRight,
  FileText,
  Layers3,
  LibraryBig,
  Plus,
  RefreshCw,
  UploadCloud,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { knowledgeApi } from '@/api/knowledge'
import { useAuthStore } from '@/stores/auth'
import { useClassStore } from '@/stores/class'
import type { KnowledgeDocListItem } from '@/api/types'
import { DASHBOARD_PAGE_SIZE } from '@/utils/constants'
import { DOC_STATUS_META } from '@/utils/constants'
import { formatDateTime, formatNumber } from '@/utils/format'
import type { DocStatusValue } from '@/types'

interface RecentDoc extends KnowledgeDocListItem {
  class_name: string
  class_code: string
}

const router = useRouter()
const auth = useAuthStore()
const classStore = useClassStore()

const loading = ref(false)
const error = ref('')
const recentDocs = ref<RecentDoc[]>([])
const stats = reactive({
  classes: 0,
  students: 0,
  docs: 0,
  chunks: 0,
  pending: 0,
})

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const today = computed(() => {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    }).format(new Date())
  } catch {
    return ''
  }
})

const hasClasses = computed(() => stats.classes > 0)

const statCards = computed(() => [
  {
    key: 'classes',
    label: '班级总数',
    value: stats.classes,
    hint: '进行中的教学空间',
    icon: UsersRound,
    tone: 'primary',
  },
  {
    key: 'students',
    label: '学生总数',
    value: stats.students,
    hint: '已加入班级的学生',
    icon: LibraryBig,
    tone: 'accent',
  },
  {
    key: 'docs',
    label: '文档总数',
    value: stats.docs,
    hint: stats.pending > 0 ? `${stats.pending} 份待处理` : '全部可预览',
    icon: FileText,
    tone: 'success',
  },
  {
    key: 'chunks',
    label: '知识切片',
    value: stats.chunks,
    hint: '可供课堂回看的内容',
    icon: Layers3,
    tone: 'neutral',
  },
])

async function loadDashboard(): Promise<void> {
  if (loading.value) return
  loading.value = true
  error.value = ''
  recentDocs.value = []
  try {
    const classes = (await classStore.fetchAllClasses()) ?? []
    const collections: RecentDoc[][] = []
    let chunkCount = 0
    let pendingCount = 0
    let docLoadFailed = false

    await Promise.all(
      classes.map(async (classItem) => {
        try {
          const result = await knowledgeApi.listDocuments({
            class_id: classItem.id,
            page: 1,
            page_size: DASHBOARD_PAGE_SIZE,
          })
          const items = result.list.map((doc) => ({
            ...doc,
            class_name: classItem.class_name,
            class_code: classItem.class_code,
          }))
          collections.push(items)
          chunkCount += items.reduce((sum, doc) => sum + doc.chunk_count, 0)
          pendingCount += items.filter((doc) => doc.status !== 2).length
        } catch {
          docLoadFailed = true
          collections.push([])
        }
      }),
    )

    stats.classes = classStore.classes.length
    stats.students = classStore.classes.reduce((sum, item) => sum + item.student_count, 0)
    stats.docs = classStore.classes.reduce((sum, item) => sum + item.doc_count, 0)
    stats.chunks = chunkCount
    stats.pending = pendingCount
    recentDocs.value = collections
      .flat()
      .sort((left, right) => right.created_at.localeCompare(left.created_at))
      .slice(0, 6)

    if (docLoadFailed) {
      // 文档总量来自班级聚合；最近文档局部读取失败时仍保留可用的部分。
      recentDocs.value = recentDocs.value
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '工作台数据暂时无法加载'
  } finally {
    loading.value = false
  }
}

function openDoc(doc: RecentDoc): void {
  router.push(`/teacher/knowledge/${doc.id}`)
}

function statusMeta(status: number): { label: string; tone: 'neutral' | 'warning' | 'success' | 'danger' } {
  return DOC_STATUS_META[status as DocStatusValue] ?? DOC_STATUS_META[0]
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page dashboard-page">
    <header class="page-head dashboard-head">
      <div class="page-head__text">
        <p class="eyebrow">TEACHING OVERVIEW</p>
        <h2 class="page-title">{{ greeting }}，{{ auth.displayName || '老师' }}</h2>
        <p class="page-subtitle">今天也一起把课堂资料，整理成学生伸手就能摘到的知识。</p>
      </div>
      <div class="dashboard-date">
        <span class="dashboard-date__day">{{ today }}</span>
        <button class="icon-btn" type="button" title="刷新数据" aria-label="刷新工作台数据" @click="loadDashboard">
          <RefreshCw :size="16" :stroke-width="1.8" />
        </button>
      </div>
    </header>

    <div v-if="loading" class="content-stack" aria-busy="true">
      <div class="stat-grid">
        <div v-for="index in 4" :key="index" class="stat-card">
          <AppSkeleton variant="stat" />
        </div>
      </div>
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <div class="dashboard-skeleton-list">
          <AppSkeleton v-for="index in 5" :key="index" variant="text" width="100%" />
        </div>
      </div>
    </div>

    <div v-else-if="error" class="panel">
      <AppEmpty error title="工作台暂时无法加载" :description="error">
        <template #action>
          <AppButton variant="secondary" @click="loadDashboard">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </div>

    <template v-else>
      <div class="stat-grid">
        <article
          v-for="card in statCards"
          :key="card.key"
          class="stat-card"
          :class="`stat-card--${card.tone}`"
        >
          <span class="stat-card__icon" aria-hidden="true">
            <component :is="card.icon" :size="19" :stroke-width="1.8" />
          </span>
          <p class="stat-card__label">{{ card.label }}</p>
          <p class="stat-card__value tabular">{{ formatNumber(card.value) }}</p>
          <p class="stat-card__hint">{{ card.hint }}</p>
        </article>
      </div>

      <div class="dashboard-grid">
        <section class="panel">
          <header class="panel-head">
            <div>
              <h3 class="section-title">最近文档</h3>
              <p class="section-note">按上传时间排序，最多展示 6 份。</p>
            </div>
            <router-link class="dashboard-link" to="/teacher/knowledge">
              去知识库
              <ArrowRight :size="14" :stroke-width="1.9" />
            </router-link>
          </header>

          <div v-if="recentDocs.length > 0" class="recent-list">
            <button
              v-for="doc in recentDocs"
              :key="doc.id"
              class="recent-item"
              type="button"
              @click="openDoc(doc)"
            >
              <span class="recent-item__icon">
                <FileText :size="17" :stroke-width="1.7" aria-hidden="true" />
              </span>
              <span class="recent-item__main">
                <span class="recent-item__title truncate">{{ doc.title }}</span>
                <span class="recent-item__meta">
                  {{ doc.class_name }} · {{ doc.file_ext.toUpperCase() }} ·
                  {{ formatDateTime(doc.created_at) }}
                </span>
              </span>
              <AppTag :tone="statusMeta(doc.status).tone">{{ statusMeta(doc.status).label }}</AppTag>
              <ArrowUpRight class="recent-item__arrow" :size="16" :stroke-width="1.8" aria-hidden="true" />
            </button>
          </div>

          <AppEmpty
            v-else-if="hasClasses"
            compact
            title="还没有课程文档"
            description="上传第一份课件后，最近文档会在这里持续出现。"
          >
            <template #action>
              <router-link to="/teacher/knowledge">
                <AppButton variant="secondary" size="sm">上传课程文档</AppButton>
              </router-link>
            </template>
          </AppEmpty>

          <AppEmpty
            v-else
            compact
            title="从第一个班级开始"
            description="创建班级后，学生可用邀请码加入你的课堂。"
          >
            <template #action>
              <router-link to="/teacher/classes">
                <AppButton variant="primary" size="sm">
                  <Plus :size="15" :stroke-width="2" />
                  创建班级
                </AppButton>
              </router-link>
            </template>
          </AppEmpty>
        </section>

        <aside class="quick-panel">
          <p class="eyebrow">QUICK START</p>
          <h3 class="quick-panel__title">今天要做点什么？</h3>
          <p class="quick-panel__lead">从三件小事开始，让班级知识库保持生长。</p>

          <div class="quick-actions">
            <router-link to="/teacher/classes" class="quick-action">
              <span class="quick-action__icon quick-action__icon--primary">
                <Plus :size="17" :stroke-width="1.9" />
              </span>
              <span class="quick-action__copy">
                <strong>创建一个新班级</strong>
                <small>生成班级编号与邀请码</small>
              </span>
              <ArrowUpRight :size="15" :stroke-width="1.8" aria-hidden="true" />
            </router-link>

            <router-link to="/teacher/knowledge" class="quick-action">
              <span class="quick-action__icon quick-action__icon--accent">
                <UploadCloud :size="17" :stroke-width="1.9" />
              </span>
              <span class="quick-action__copy">
                <strong>上传课程文档</strong>
                <small>支持 PDF、Word、PPT、TXT</small>
              </span>
              <ArrowUpRight :size="15" :stroke-width="1.8" aria-hidden="true" />
            </router-link>

            <router-link to="/teacher/classes" class="quick-action">
              <span class="quick-action__icon quick-action__icon--neutral">
                <UsersRound :size="17" :stroke-width="1.9" />
              </span>
              <span class="quick-action__copy">
                <strong>查看学生名单</strong>
                <small>确认入班与 QQ 绑定状态</small>
              </span>
              <ArrowUpRight :size="15" :stroke-width="1.8" aria-hidden="true" />
            </router-link>
          </div>

          <p class="quick-note">知识库会陪学生走过整个单元，记得常回来看一眼。</p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard-head {
  align-items: flex-end;
}

.dashboard-date {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding-bottom: 4px;
}

.dashboard-date__day {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  white-space: nowrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}

.stat-card {
  position: relative;
  padding: var(--sp-4);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.stat-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: var(--sp-4);
  right: var(--sp-4);
  height: 2px;
  border-radius: 0 0 999px 999px;
  background: var(--color-primary);
  opacity: 0.55;
}

.stat-card--accent::after {
  background: var(--color-accent);
}

.stat-card--success::after {
  background: var(--color-success);
}

.stat-card--neutral::after {
  background: var(--color-border-strong);
}

.stat-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-bottom: var(--sp-3);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.stat-card--accent .stat-card__icon {
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
  background: color-mix(in srgb, var(--color-accent) 12%, var(--color-surface));
}

.stat-card--success .stat-card__icon {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
}

.stat-card--neutral .stat-card__icon {
  color: var(--color-text-muted);
  background: var(--color-surface-alt);
}

.stat-card__label {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.stat-card__value {
  margin-top: 2px;
  font-size: 30px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.stat-card__hint {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.dashboard-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin-top: var(--sp-4);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(280px, 1fr);
  gap: var(--sp-5);
  align-items: start;
}

.dashboard-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.recent-list {
  display: flex;
  flex-direction: column;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  width: 100%;
  padding: var(--sp-3) var(--sp-5);
  border: 0;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  text-align: left;
  transition: background-color 160ms ease-out;
}

.recent-item:last-child {
  border-bottom: 0;
}

.recent-item:hover {
  background: var(--color-surface-alt);
}

.recent-item:hover .recent-item__arrow {
  color: var(--color-primary);
  transform: translate(1px, -1px);
}

.recent-item__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.recent-item__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1 1 auto;
}

.recent-item__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.recent-item__meta {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.recent-item__arrow {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: color 160ms ease-out, transform 160ms ease-out;
}

.quick-panel {
  padding: var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--color-accent) 9%, transparent) 0, transparent 40%),
    var(--color-surface);
  box-shadow: var(--shadow-1);
}

.quick-panel__title {
  font-size: var(--fs-lg);
}

.quick-panel__lead {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin-top: var(--sp-5);
}

.quick-action {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  background: var(--color-surface-alt);
  transition: border-color 160ms ease-out, background-color 160ms ease-out, transform 160ms ease-out;
}

.quick-action:hover {
  color: var(--color-text);
  border-color: color-mix(in srgb, var(--color-primary) 30%, var(--color-border));
  background: var(--color-surface);
  transform: translateY(-1px);
}

.quick-action__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
}

.quick-action__icon--primary {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.quick-action__icon--accent {
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
  background: color-mix(in srgb, var(--color-accent) 13%, var(--color-surface));
}

.quick-action__icon--neutral {
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.quick-action__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
  line-height: 1.4;
}

.quick-action__copy strong {
  font-size: var(--fs-sm);
}

.quick-action__copy small {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.quick-action > svg {
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.quick-note {
  margin-top: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
