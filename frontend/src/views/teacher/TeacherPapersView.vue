<!-- 教师试卷列表：按班级展示状态卡片，支持发布、撤回与查看成绩。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AlertCircle, Plus, RefreshCw } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import PaperCard from '@/components/business/PaperCard.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { papersApi } from '@/api/papers'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import { PAGE_SIZE } from '@/utils/constants'
import type { PaperItem } from '@/api/types'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const selectedClassId = ref('')
const papers = ref<PaperItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(PAGE_SIZE)
const loading = ref(false)
const loadError = ref('')
const classErroring = ref(false)

const actionOpen = ref(false)
const actionKind = ref<'publish' | 'withdraw'>('publish')
const actionTarget = ref<PaperItem | null>(null)
const actioning = ref(false)
const actionError = ref('')

const classOptions = computed(() =>
  classStore.classes.map((item) => ({
    label: `${item.class_name} · ${item.course_name}`,
    value: String(item.id),
  })),
)
const currentClass = computed(
  () => classStore.classes.find((item) => String(item.id) === selectedClassId.value) ?? null,
)
const publishedCount = computed(
  () => papers.value.filter((paper) => paper.status === 'published').length,
)
const draftCount = computed(
  () => papers.value.filter((paper) => paper.status === 'draft').length,
)

const actionTitle = computed(() =>
  actionKind.value === 'publish' ? '发布这份试卷？' : '撤回这份试卷？',
)
const actionDescription = computed(() =>
  actionKind.value === 'publish'
    ? '发布后学生会在试卷列表中看到并可以开始作答，题目内容将锁定。'
    : '撤回后学生列表立即隐藏；已完成的历史成绩仍保留，可继续打开查看。',
)
const actionConfirmText = computed(() =>
  actionKind.value === 'publish' ? '确认发布' : '确认撤回',
)

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  return toUserMessage(err)
}

function syncClassQuery(): void {
  void router.replace({
    query: {
      ...route.query,
      class_id: selectedClassId.value,
    },
  })
}

async function loadPapers(nextPage = page.value): Promise<void> {
  if (!selectedClassId.value) return
  loading.value = true
  loadError.value = ''
  try {
    const result = await papersApi.list(Number(selectedClassId.value), {
      page: nextPage,
      page_size: pageSize.value,
    })
    papers.value = result.list
    total.value = result.total
    page.value = result.page
    pageSize.value = result.page_size
  } catch (err) {
    papers.value = []
    total.value = 0
    loadError.value = mapError(err)
  } finally {
    loading.value = false
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
  await loadPapers(1)
}

function handleClassChange(value: string): void {
  if (value === selectedClassId.value) return
  selectedClassId.value = value
  papers.value = []
  total.value = 0
  page.value = 1
  loadError.value = ''
  syncClassQuery()
  void loadPapers(1)
}

function handlePageChange(nextPage: number, nextSize: number): void {
  pageSize.value = nextSize
  page.value = nextPage
  void loadPapers(nextPage)
}

function openPaper(paper: PaperItem): void {
  void router.push({
    path: `/teacher/papers/${paper.id}`,
    query: { class_id: String(paper.class_id) },
  })
}

function gotoCreate(): void {
  void router.push({
    path: '/teacher/papers/new',
    query: selectedClassId.value ? { class_id: selectedClassId.value } : undefined,
  })
}

function askAction(paper: PaperItem, kind: 'publish' | 'withdraw'): void {
  actionTarget.value = paper
  actionKind.value = kind
  actionError.value = ''
  actionOpen.value = true
}

async function confirmAction(): Promise<void> {
  if (!actionTarget.value || actioning.value) return
  actioning.value = true
  actionError.value = ''
  try {
    if (actionKind.value === 'publish') {
      await papersApi.publish(actionTarget.value.id)
      ui.success('试卷已发布，学生现在可以作答')
    } else {
      await papersApi.withdraw(actionTarget.value.id)
      ui.success('试卷已撤回')
    }
    actionOpen.value = false
    actionTarget.value = null
    await loadPapers(page.value)
  } catch (err) {
    actionError.value = mapError(err)
  } finally {
    actioning.value = false
  }
}

onMounted(bootstrap)
</script>

<template>
  <div class="page paper-list">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">PAPERS</p>
        <h1 class="page-title">试卷</h1>
        <p class="page-subtitle">
          固定选题或按知识点随机组卷。发布后学生可作答，撤回不会删除已产生的成绩。
        </p>
      </div>
      <div class="page-actions">
        <AppButton variant="ghost" :disabled="!selectedClassId" @click="loadPapers(page)">
          <RefreshCw :size="15" :stroke-width="1.8" />
          刷新
        </AppButton>
        <AppButton variant="primary" :disabled="!selectedClassId" @click="gotoCreate">
          <Plus :size="16" :stroke-width="1.9" />
          新建试卷
        </AppButton>
      </div>
    </header>

    <section v-if="classErroring" class="panel">
      <AppEmpty error title="班级列表暂时无法加载" description="请检查网络后重试">
        <template #action>
          <AppButton variant="secondary" @click="bootstrap">重新加载</AppButton>
        </template>
      </AppEmpty>
    </section>

    <section v-else-if="classStore.classes.length === 0" class="panel">
      <AppEmpty
        title="还没有可组卷的班级"
        description="试卷按班级隔离。先创建班级，再从题库选题组卷。"
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
      <section class="paper-toolbar panel">
        <AppSelect
          :model-value="selectedClassId"
          label="当前班级"
          :options="classOptions"
          class="class-select"
          @update:model-value="handleClassChange"
        />
        <dl class="paper-summary">
          <div>
            <dt>已发布</dt>
            <dd class="tabular">{{ publishedCount }}</dd>
          </div>
          <div>
            <dt>草稿</dt>
            <dd class="tabular">{{ draftCount }}</dd>
          </div>
          <div>
            <dt>共计</dt>
            <dd class="tabular">{{ total }}</dd>
          </div>
        </dl>
      </section>

      <section v-if="loading" class="paper-grid" aria-busy="true">
        <article v-for="index in 4" :key="index" class="panel panel-body">
          <AppSkeleton variant="title" />
          <AppSkeleton variant="text" :rows="4" />
        </article>
      </section>

      <section v-else-if="loadError" class="panel">
        <AppEmpty error title="试卷列表暂时无法加载" :description="loadError">
          <template #action>
            <AppButton variant="secondary" @click="loadPapers(page)">
              <RefreshCw :size="15" :stroke-width="1.8" />
              重新加载
            </AppButton>
          </template>
        </AppEmpty>
      </section>

      <section v-else-if="papers.length === 0" class="panel">
        <AppEmpty
          title="这个班还没有试卷"
          :description="currentClass ? `为「${currentClass.class_name}」从题库选题，生成第一份试卷。` : '从题库选题，生成第一份试卷。'"
        >
          <template #action>
            <AppButton variant="primary" @click="gotoCreate">
              <Plus :size="15" :stroke-width="1.9" />
              新建试卷
            </AppButton>
          </template>
        </AppEmpty>
      </section>

      <template v-else>
        <section class="paper-grid">
          <PaperCard
            v-for="paper in papers"
            :key="paper.id"
            :paper="paper"
            @open="openPaper"
            @publish="askAction($event, 'publish')"
            @withdraw="askAction($event, 'withdraw')"
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
    </template>

    <AppModal
      v-model="actionOpen"
      :title="actionTitle"
      :description="actionDescription"
      :confirm-text="actionConfirmText"
      :confirm-variant="actionKind === 'withdraw' ? 'danger' : 'primary'"
      :confirm-loading="actioning"
      @confirm="confirmAction"
    >
      <p v-if="actionTarget" class="action-target">
        {{ actionTarget.title }} · {{ actionTarget.question_count }} 题 · {{ actionTarget.total_score }} 分
      </p>
      <p v-if="actionError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ actionError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.paper-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
  padding: var(--sp-4) var(--sp-5);
  flex-wrap: wrap;
}

.class-select {
  width: 320px;
  max-width: 100%;
}

.paper-summary {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
}

.paper-summary dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-summary dd {
  margin-top: 2px;
  color: var(--color-primary);
  font-size: var(--fs-xl);
  font-weight: 700;
}

.paper-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4);
  margin-bottom: var(--sp-4);
}

.action-target {
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

@media (max-width: 1023px) {
  .paper-grid {
    grid-template-columns: 1fr;
  }
}
</style>
