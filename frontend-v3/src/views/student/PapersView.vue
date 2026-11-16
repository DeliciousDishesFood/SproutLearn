<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { papersApi } from '@/api/papers'
import { attemptsApi } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'
import type { MyAttemptItem, PaperItem } from '@/api/contract'
import { useAuthStore } from '@/stores/auth'
import {
  ATTEMPT_STATUS_LABEL,
  PAPER_KIND_LABEL,
  formatDateTime,
  formatScore,
} from '@/utils/format'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const papers = ref<PaperItem[]>([])
const mine = ref<MyAttemptItem[]>([])
const papersPage = ref(1)
const papersTotal = ref(0)
const minePage = ref(1)
const mineTotal = ref(0)
const pageSize = 20
const loading = ref(true)
const errorText = ref('')
const startingId = ref<number | null>(null)

const classId = computed(() => auth.student?.class_id ?? null)

function attemptFor(paperId: number): MyAttemptItem | undefined {
  return mine.value.find((item) => item.paper_id === paperId)
}

function actionLabel(paper: PaperItem): string {
  if (startingId.value === paper.id) return '进入中…'
  const status = paper.my_attempt_status
  if (status === 'doing') return '继续作答'
  if (status === 'submitted' || status === 'graded') return '查看结果'
  return '开始作答'
}

/** 不依赖当前页是否包含该 paper，直接发起/恢复作答。 */
async function openPaperById(id: number): Promise<void> {
  if (startingId.value !== null) return
  startingId.value = id
  try {
    const attempt = await papersApi.startAttempt(id)
    if (attempt.status === 'doing') {
      await router.push(`/student/attempts/${attempt.id}`)
    } else {
      await router.push(`/student/attempts/${attempt.id}/result`)
    }
  } catch (error) {
    if (isApiError(error) && error.code === 40910) {
      const attempt = attemptFor(id)
      if (attempt) await router.push(`/student/attempts/${attempt.attempt_id}/result`)
      else toast.error(error.friendlyMessage)
    } else {
      toast.error(toUserMessage(error))
    }
  } finally {
    startingId.value = null
  }
}

async function loadPapers(): Promise<void> {
  if (!classId.value) return
  try {
    const result = await papersApi.list(classId.value, {
      page: papersPage.value,
      page_size: pageSize,
    })
    papers.value = result.list
    papersTotal.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
}

async function loadMine(): Promise<void> {
  if (!classId.value) return
  try {
    const result = await attemptsApi.mine({ page: minePage.value, page_size: pageSize })
    mine.value = result.list
    mineTotal.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
}

async function load(): Promise<void> {
  if (!classId.value) {
    loading.value = false
    return
  }
  loading.value = true
  errorText.value = ''
  await Promise.all([loadPapers(), loadMine()])
  loading.value = false
}

function parsePaperQuery(): number | null {
  const raw = route.query.paper
  const value = Array.isArray(raw) ? raw[0] : raw
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}

watch(papersPage, () => void loadPapers())
watch(minePage, () => void loadMine())

onMounted(async () => {
  await load()
  const paperId = parsePaperQuery()
  if (paperId !== null) {
    await router.replace({ query: {} })
    await openPaperById(paperId)
  }
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">{{ auth.student?.class_name ?? '我的班级' }} · 试卷</p>
      <h1>试卷</h1>
      <p class="page-head__lede">全部试卷与我的作答记录，点开即可开始或继续作答。</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student">回到学习台</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="!classId" class="notice">当前账号没有班级信息，请联系老师重新加入班级。</p>

  <section v-else class="card">
    <header class="card__head">
      <h2>全部试卷</h2>
      <span class="card__meta">共 {{ papersTotal }} 份</span>
    </header>

    <p v-if="loading" class="loading-line">正在读取试卷…</p>
    <EmptyState
      v-else-if="papers.length === 0"
      title="没有可作答试卷"
      description="老师发布新练习后会出现在这里。"
    />
    <template v-else>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>试卷</th>
              <th>用途</th>
              <th class="num">题量</th>
              <th class="num">满分</th>
              <th>截止</th>
              <th>状态</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="paper in papers" :key="paper.id">
              <td>
                <span class="row-title">
                  <strong>{{ paper.title }}</strong>
                  <em>{{ formatDateTime(paper.created_at) }}</em>
                </span>
              </td>
              <td>{{ PAPER_KIND_LABEL[paper.kind] }}</td>
              <td class="num">{{ paper.question_count }}</td>
              <td class="num">{{ formatScore(paper.total_score) }}</td>
              <td class="tertiary">{{ paper.due_at ? formatDateTime(paper.due_at) : '未设置截止' }}</td>
              <td>
                <BaseBadge v-if="paper.my_attempt_status" :tone="paper.my_attempt_status === 'graded' ? 'lime' : 'amber'">
                  {{ ATTEMPT_STATUS_LABEL[paper.my_attempt_status] }}
                </BaseBadge>
                <BaseBadge v-else tone="plain">未开始</BaseBadge>
              </td>
              <td>
                <div class="actions">
                  <button
                    class="btn btn--sm"
                    type="button"
                    :disabled="startingId === paper.id"
                    @click="openPaperById(paper.id)"
                  >
                    {{ actionLabel(paper) }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :page="papersPage" :page-size="pageSize" :total="papersTotal" @change="papersPage = $event" />
    </template>
  </section>

  <section class="card">
    <header class="card__head">
      <h2>我的作答记录</h2>
      <span class="card__meta">共 {{ mineTotal }} 条</span>
    </header>
    <p v-if="loading" class="loading-line">正在读取作答记录…</p>
    <EmptyState
      v-else-if="mine.length === 0"
      title="还没有完成记录"
      description="完成并提交试卷后，成绩会展示在这里。"
    />
    <template v-else>
      <div class="table-wrap" style="margin-top: 10px">
        <table class="table">
          <thead>
            <tr>
              <th>试卷</th>
              <th>状态</th>
              <th class="num">得分</th>
              <th>开始</th>
              <th>提交</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in mine" :key="item.attempt_id">
              <td>{{ item.paper_title ?? `试卷 #${item.paper_id}` }}</td>
              <td>
                <BaseBadge :tone="item.status === 'graded' ? 'lime' : item.status === 'submitted' ? 'amber' : 'plain'">
                  {{ ATTEMPT_STATUS_LABEL[item.status] }}
                </BaseBadge>
              </td>
              <td class="num">{{ formatScore(item.total_score) }} / {{ formatScore(item.full_score) }}</td>
              <td class="tertiary">{{ formatDateTime(item.started_at) }}</td>
              <td class="tertiary">{{ formatDateTime(item.submitted_at) }}</td>
              <td>
                <div class="actions">
                  <RouterLink
                    class="btn btn--sm"
                    :to="
                      item.status === 'doing'
                        ? `/student/attempts/${item.attempt_id}`
                        : `/student/attempts/${item.attempt_id}/result`
                    "
                  >
                    {{ item.status === 'doing' ? '继续' : '结果' }}
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :page="minePage" :page-size="pageSize" :total="mineTotal" @change="minePage = $event" />
    </template>
  </section>
</template>
