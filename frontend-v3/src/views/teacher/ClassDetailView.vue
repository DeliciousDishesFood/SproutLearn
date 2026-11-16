<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, ClipboardList, FileText, RefreshCw, Settings, Users } from 'lucide-vue-next'
import BaseTabs from '@/components/ui/BaseTabs.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import StudentTable from '@/components/business/StudentTable.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { classesApi } from '@/api/classes'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { ClassDetail, InviteCodeInfo, PaperItem, StudentListItem } from '@/api/contract'
import {
  PAPER_KIND_LABEL,
  PAPER_STATUS_LABEL,
  formatDateTime,
  paperStatusTone,
} from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const toast = useToast()

const classId = computed(() => Number(route.params.classId))
const tab = ref('overview')
const detail = ref<ClassDetail | null>(null)
const invite = ref<InviteCodeInfo | null>(null)
const students = ref<StudentListItem[]>([])
const recentPapers = ref<PaperItem[]>([])
const studentTotal = ref(0)
const page = ref(1)
const pageSize = 10
const keyword = ref('')
const loading = ref(true)
const loadingStudents = ref(false)
const resetting = ref(false)
const errorText = ref('')

const tabs = [
  { key: 'overview', label: '概览' },
  { key: 'students', label: '学生' },
  { key: 'invite', label: '邀请码' },
]

const quickLinks = computed(() => [
  { label: '知识库', to: `/teacher/classes/${classId.value}/knowledge`, icon: BookOpen },
  { label: '题库', to: `/teacher/classes/${classId.value}/banks`, icon: ClipboardList },
  { label: '试卷', to: `/teacher/classes/${classId.value}/papers`, icon: FileText },
  { label: '班级设置', to: `/teacher/classes/${classId.value}/settings`, icon: Settings },
])

async function loadDetail(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [classDetail, inviteInfo] = await Promise.all([
      classesApi.detail(classId.value),
      classesApi.inviteCode(classId.value),
    ])
    detail.value = classDetail
    invite.value = inviteInfo
    ui.setCurrentClassId(classId.value)
    await loadRecentPapers()
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadRecentPapers(): Promise<void> {
  try {
    const result = await papersApi.list(classId.value, { page: 1, page_size: 3 })
    recentPapers.value = result.list
  } catch {
    recentPapers.value = []
  }
}

async function loadStudents(): Promise<void> {
  loadingStudents.value = true
  try {
    const result = await classesApi.students(classId.value, {
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize,
    })
    students.value = result.list
    studentTotal.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loadingStudents.value = false
  }
}

function search(): void {
  page.value = 1
  void loadStudents()
}

async function resetInvite(): Promise<void> {
  if (!window.confirm('重置后旧邀请码立即失效，已加入的学生不受影响。确定重置吗？')) return
  resetting.value = true
  try {
    const result = await classesApi.resetInviteCode(classId.value)
    invite.value = invite.value
      ? { ...invite.value, invite_code: result.invite_code, created_at: result.created_at }
      : null
    toast.success('邀请码已重置')
    await loadDetail()
  } catch (error) {
    toast.error(toUserMessage(error))
  } finally {
    resetting.value = false
  }
}

function copyInvite(): void {
  const code = invite.value?.invite_code
  if (!code) return
  navigator.clipboard?.writeText(code).then(
    () => toast.success('邀请码已复制'),
    () => toast.error('复制失败，请手动复制'),
  )
}

watch(tab, (value) => {
  if (value === 'students' && students.value.length === 0) void loadStudents()
})

watch(page, () => {
  void loadStudents()
})

onMounted(async () => {
  await loadDetail()
  if (detail.value) await loadStudents()
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink to="/teacher/classes">班级</RouterLink> · {{ detail?.class_name ?? '班级详情' }}
      </p>
      <h1>{{ detail?.class_name ?? '班级详情' }}</h1>
      <p class="page-head__lede">
        {{ detail?.course_name ?? '—' }} · 班级编号 {{ detail?.class_code ?? '—' }}
      </p>
    </div>
    <div class="page-head__actions">
      <RouterLink
        class="btn btn--primary"
        :to="`/teacher/classes/${classId}/papers/new`"
      >
        组卷
      </RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="card">
    <BaseTabs v-model="tab" :items="tabs" />

    <div v-if="loading" class="loading-line">正在读取班级…</div>

    <div v-else-if="tab === 'overview'" class="stack" style="padding-top: 14px">
      <div class="kv">
        <span>学生人数：<b>{{ detail?.student_count ?? 0 }}</b></span>
        <span>资料数量：<b>{{ detail?.doc_count ?? 0 }}</b></span>
        <span>创建时间：<b>{{ formatDateTime(detail?.created_at) }}</b></span>
        <span>邀请码：<b class="mono">{{ detail?.invite_code ?? '—' }}</b></span>
      </div>
      <div class="grid-2">
        <RouterLink
          v-for="link in quickLinks"
          :key="link.to"
          class="notice"
          :to="link.to"
          style="display: flex; align-items: center; gap: 8px; text-decoration: none"
        >
          <component :is="link.icon" :size="15" aria-hidden="true" />
          <span>{{ link.label }}</span>
        </RouterLink>
      </div>

      <div class="card__head">
        <h2>最近试卷</h2>
        <RouterLink class="card__link" :to="`/teacher/classes/${classId}/papers`">查看全部</RouterLink>
      </div>
      <EmptyState
        v-if="recentPapers.length === 0"
        title="还没有试卷"
        description="从题库组一份练习，发布后学生会收到作答提醒。"
        action-label="去组卷"
        @action="router.push(`/teacher/classes/${classId}/papers/new`)"
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>试卷</th>
              <th>用途</th>
              <th>状态</th>
              <th>截止</th>
              <th class="num">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="paper in recentPapers" :key="paper.id">
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
              <td class="tertiary">{{ paper.due_at ? formatDateTime(paper.due_at) : '未设置截止' }}</td>
              <td>
                <div class="actions">
                  <RouterLink class="btn btn--sm" :to="`/teacher/papers/${paper.id}`">详情</RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'students'" class="stack" style="padding-top: 14px">
      <form class="row row--wrap" @submit.prevent="search">
        <input
          v-model="keyword"
          class="input"
          style="max-width: 260px"
          type="search"
          placeholder="搜索学号或姓名"
          aria-label="搜索学生"
        />
        <BaseButton type="submit">搜索</BaseButton>
      </form>
      <p v-if="loadingStudents" class="loading-line">正在读取学生…</p>
      <EmptyState
        v-else-if="students.length === 0"
        title="还没有学生"
        description="把邀请码发给学生，学生用邀请码即可加入班级。"
        action-label="查看邀请码"
        @action="tab = 'invite'"
      />
      <template v-else>
        <StudentTable :items="students" />
        <PaginationBar :page="page" :page-size="pageSize" :total="studentTotal" @change="page = $event" />
      </template>
    </div>

    <div v-else class="stack" style="padding-top: 14px">
      <div class="notice">
        当前邀请码：
        <span class="copy-code" style="margin: 0 6px">
          <code>{{ invite?.invite_code ?? detail?.invite_code ?? '—' }}</code>
          <button class="btn btn--sm" type="button" @click="copyInvite">复制</button>
        </span>
        <BaseBadge :tone="invite?.status === 1 ? 'lime' : 'plain'">
          {{ invite?.status === 1 ? '有效' : '未知状态' }}
        </BaseBadge>
      </div>
      <div class="kv">
        <span>创建时间：<b>{{ formatDateTime(invite?.created_at) }}</b></span>
        <span>过期时间：<b>{{ invite?.expires_at ? formatDateTime(invite.expires_at) : '长期有效' }}</b></span>
      </div>
      <div class="row">
        <BaseButton :loading="resetting" @click="resetInvite">
          <RefreshCw :size="14" aria-hidden="true" />重置邀请码
        </BaseButton>
        <span class="small tertiary">重置后旧码立即失效，已加入学生不受影响。</span>
      </div>
      <p class="foot"><Users :size="12" aria-hidden="true" /> 已加入 {{ detail?.student_count ?? 0 }} 名学生</p>
    </div>
  </section>
</template>
