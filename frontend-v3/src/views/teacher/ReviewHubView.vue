<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { papersApi } from '@/api/papers'
import { workbenchApi } from '@/api/workbench'
import { toUserMessage } from '@/api/client'
import type { PaperItem, TeacherWorkbench } from '@/api/contract'
import { useUiStore } from '@/stores/ui'
import {
  PAPER_KIND_LABEL,
  PAPER_STATUS_LABEL,
  formatDateTime,
  formatPercent,
  paperStatusTone,
} from '@/utils/format'

const route = useRoute()
const ui = useUiStore()
const classId = computed(() => Number(route.params.classId))

const papers = ref<PaperItem[]>([])
const workbench = ref<TeacherWorkbench | null>(null)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const errorText = ref('')

const reviewable = computed(() => papers.value.filter((paper) => paper.status !== 'draft'))

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [paperResult, summary] = await Promise.all([
      papersApi.list(classId.value, { page: page.value, page_size: pageSize }),
      workbenchApi.teacher(classId.value),
    ])
    papers.value = paperResult.list
    total.value = paperResult.total
    workbench.value = summary
    ui.setCurrentClassId(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

watch(page, () => void load())

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> · 批改
      </p>
      <h1>批改</h1>
      <p class="page-head__lede">按试卷进入作答列表，逐题查看并复核待复核题目。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/classes/${classId}/papers`">全部试卷</RouterLink>
      <RouterLink class="btn" :to="`/teacher/classes/${classId}/questions`">去题库</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="stats">
    <article class="stat">
      <div class="stat__label">待复核题目</div>
      <div class="stat__row">
        <span class="stat__value">{{ workbench?.pending_review ?? 0 }}</span>
        <span class="stat__tag">按题目计数</span>
      </div>
      <p class="stat__hint">复核完成后清零</p>
    </article>
    <article class="stat">
      <div class="stat__label">今日提交</div>
      <div class="stat__row"><span class="stat__value">{{ workbench?.today_submissions ?? 0 }}</span></div>
      <p class="stat__hint">今天提交的作答数</p>
    </article>
    <article class="stat">
      <div class="stat__label">平均得分率</div>
      <div class="stat__row">
        <span class="stat__value">{{ formatPercent(workbench?.average_score_rate ?? 0) }}</span>
      </div>
      <p class="stat__hint">原始平均分 {{ workbench?.average_score ?? 0 }}</p>
    </article>
    <article class="stat">
      <div class="stat__label">本页可批改</div>
      <div class="stat__row"><span class="stat__value">{{ reviewable.length }}</span></div>
      <p class="stat__hint">已发布与已撤回的试卷（当前页）</p>
    </article>
  </section>

  <section class="card">
    <header class="card__head">
      <h2>批改入口</h2>
      <span class="card__meta">本页 {{ reviewable.length }} 份 · 共 {{ total }} 份</span>
    </header>

    <p v-if="loading" class="loading-line">正在读取试卷…</p>
    <EmptyState
      v-else-if="reviewable.length === 0"
      title="暂无可批改试卷"
      description="发布试卷并有学生提交后，这里会出现批改入口。"
      action-label="去组卷"
      @action="$router.push(`/teacher/classes/${classId}/papers/new`)"
    />
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>试卷</th>
            <th>用途</th>
            <th>状态</th>
            <th class="num">题量</th>
            <th class="num">满分</th>
            <th>截止</th>
            <th class="num">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="paper in reviewable" :key="paper.id">
            <td>
              <span class="row-title">
                <strong>{{ paper.title }}</strong>
                <em>{{ formatDateTime(paper.created_at) }}</em>
              </span>
            </td>
            <td>{{ PAPER_KIND_LABEL[paper.kind] }}</td>
            <td>
              <BaseBadge :tone="paperStatusTone(paper.status)">
                {{ PAPER_STATUS_LABEL[paper.status] }}
              </BaseBadge>
            </td>
            <td class="num">{{ paper.question_count }}</td>
            <td class="num">{{ paper.total_score }}</td>
            <td class="tertiary">{{ paper.due_at ? formatDateTime(paper.due_at) : '未设置截止' }}</td>
            <td>
              <div class="actions">
                <RouterLink class="btn btn--sm" :to="`/teacher/papers/${paper.id}/attempts`">
                  进入批改
                </RouterLink>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
  </section>
</template>

<style scoped>
.stat__tag {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--pill-bg);
  color: var(--pill-text);
  font-size: 11px;
}
</style>
