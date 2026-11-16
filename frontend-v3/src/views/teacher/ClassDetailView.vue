<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, ClipboardList, FileText, RefreshCw, Settings, Users } from 'lucide-vue-next'
import BaseTabs from '@/components/ui/BaseTabs.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import StudentTable from '@/components/business/StudentTable.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { classesApi } from '@/api/classes'
import { accountApi } from '@/api/account'
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

const isArchived = computed(() => detail.value?.status === 0)

// ── 学生状态筛选（即选即生效，本地过滤当前页） ───────────────
const statusFilter = ref<'all' | 'normal' | 'disabled'>('all')
const statusOptions = [
  { key: 'all', label: '全部' },
  { key: 'normal', label: '正常' },
  { key: 'disabled', label: '停用' },
] as const
const filteredStudents = computed(() => {
  if (statusFilter.value === 'all') return students.value
  const expected = statusFilter.value === 'normal' ? 1 : 0
  return students.value.filter((item) => (item.status ?? 1) === expected)
})

// ── 重置学生密码：一次性临时密码只保存在本页 ref ─────────────
const resetTarget = ref<StudentListItem | null>(null)
const resettingPassword = ref(false)
const resetError = ref('')
const tempTarget = ref<StudentListItem | null>(null)
const tempPassword = ref('')
const tempCopied = ref(false)

// ── 停用/恢复 ─────────────────────────────────────────────
const statusTarget = ref<StudentListItem | null>(null)
const statusSaving = ref(false)

const restoreOpen = ref(false)
const restoring = ref(false)

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

const resetOpen = ref(false)

async function resetInvite(): Promise<void> {
  resetOpen.value = true
}

async function confirmResetInvite(): Promise<void> {
  resetting.value = true
  try {
    const result = await classesApi.resetInviteCode(classId.value)
    invite.value = invite.value
      ? { ...invite.value, invite_code: result.invite_code, created_at: result.created_at }
      : null
    toast.success('邀请码已重置')
    resetOpen.value = false
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

function openReset(item: StudentListItem): void {
  resetTarget.value = item
  resetError.value = ''
}

function cancelReset(): void {
  if (resettingPassword.value) return
  resetTarget.value = null
  resetError.value = ''
}

async function confirmReset(): Promise<void> {
  const target = resetTarget.value
  if (!target || resettingPassword.value) return
  resettingPassword.value = true
  resetError.value = ''
  try {
    const result = await accountApi.resetStudentPassword(classId.value, target.id)
    tempTarget.value = target
    tempPassword.value = result.temporary_password
    tempCopied.value = false
    resetTarget.value = null
  } catch (error) {
    // 失败保留学生上下文，用户可直接重试。
    resetError.value = toUserMessage(error)
  } finally {
    resettingPassword.value = false
  }
}

function closeTemp(): void {
  tempTarget.value = null
  tempPassword.value = ''
  tempCopied.value = false
}

function copyTemp(): void {
  if (!tempPassword.value) return
  navigator.clipboard?.writeText(tempPassword.value).then(
    () => {
      tempCopied.value = true
      toast.success('临时密码已复制')
    },
    () => toast.error('复制失败，请手动选择密码复制'),
  )
}

function openStatus(item: StudentListItem): void {
  statusTarget.value = item
}

async function confirmStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target || statusSaving.value) return
  const index = students.value.findIndex((item) => item.id === target.id)
  const previous = target.status ?? 1
  const next: 0 | 1 = previous === 0 ? 1 : 0
  statusSaving.value = true
  // 乐观更新当前行；失败回滚并提示。
  if (index >= 0) students.value[index] = { ...students.value[index], status: next }
  try {
    await accountApi.setStudentStatus(classId.value, target.id, next)
    toast.success(next === 1 ? '学生已恢复' : '学生已停用')
    statusTarget.value = null
  } catch (error) {
    if (index >= 0) students.value[index] = { ...students.value[index], status: previous }
    toast.error(toUserMessage(error))
  } finally {
    statusSaving.value = false
  }
}

function openRestore(): void {
  restoreOpen.value = true
}

async function confirmRestore(): Promise<void> {
  restoring.value = true
  try {
    await classesApi.restore(classId.value)
    toast.success('班级已恢复')
    restoreOpen.value = false
    await loadDetail()
    await loadStudents()
  } catch (error) {
    toast.error(toUserMessage(error))
  } finally {
    restoring.value = false
  }
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
    </div>
    <div class="page-head__actions">
      <BaseBadge v-if="isArchived" tone="plain">已归档</BaseBadge>
      <BaseButton v-if="isArchived" variant="primary" @click="openRestore">恢复班级</BaseButton>
      <RouterLink
        v-else
        class="btn btn--primary"
        :to="`/teacher/classes/${classId}/papers/new`"
      >
        组卷
      </RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="isArchived" class="notice" role="status">
    班级已归档，仅可查看历史数据；恢复后可继续新增、发布与通知。
  </p>

  <section class="card">
    <BaseTabs
      v-model="tab"
      :items="tabs"
      id="class-tabs"
      panel-id="class-tab-panel"
      aria-label="班级信息"
    />

    <div v-if="loading" class="loading-line">正在读取班级…</div>

    <div
      v-else-if="tab === 'overview'"
      id="class-tab-panel"
      class="stack"
      role="tabpanel"
      :aria-labelledby="`class-tabs-tab-${tab}`"
      style="padding-top: 14px"
    >
      <div class="kv">
        <span>学生人数：<b>{{ detail?.student_count ?? 0 }}</b></span>
        <span>资料数量：<b>{{ detail?.doc_count ?? 0 }}</b></span>
        <span>创建时间：<b>{{ formatDateTime(detail?.created_at) }}</b></span>
        <span>邀请码：<b class="mono">{{ detail?.invite_code ?? '—' }}</b></span>
      </div>
      <div v-if="!isArchived" class="grid-2">
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
      <EmptyState v-if="recentPapers.length === 0" title="还没有试卷" />
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

    <div
      v-else-if="tab === 'students'"
      id="class-tab-panel"
      class="stack"
      role="tabpanel"
      :aria-labelledby="`class-tabs-tab-${tab}`"
      style="padding-top: 14px"
    >
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
        action-label="查看邀请码"
        @action="tab = 'invite'"
      />
      <template v-else>
        <div class="row row--wrap" role="group" aria-label="按学生状态筛选">
          <BaseButton
            v-for="option in statusOptions"
            :key="option.key"
            size="sm"
            :variant="statusFilter === option.key ? 'primary' : 'secondary'"
            :aria-pressed="statusFilter === option.key"
            @click="statusFilter = option.key"
          >
            {{ option.label }}
          </BaseButton>
          <span class="small muted">当前显示 {{ filteredStudents.length }} 人</span>
        </div>
        <EmptyState
          v-if="filteredStudents.length === 0"
          title="当前筛选下没有学生"
          action-label="查看全部"
          @action="statusFilter = 'all'"
        />
        <StudentTable
          v-else
          :items="filteredStudents"
          :readonly="isArchived"
          @reset-password="openReset"
          @toggle-status="openStatus"
        />
        <PaginationBar :page="page" :page-size="pageSize" :total="studentTotal" @change="page = $event" />
      </template>
    </div>

    <div
      v-else
      id="class-tab-panel"
      class="stack"
      role="tabpanel"
      :aria-labelledby="`class-tabs-tab-${tab}`"
      style="padding-top: 14px"
    >
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
      <div v-if="!isArchived" class="row">
        <BaseButton :loading="resetting" @click="resetInvite">
          <RefreshCw :size="14" aria-hidden="true" />重置邀请码
        </BaseButton>
        <span class="small muted">重置后旧码立即失效，已加入学生不受影响。</span>
      </div>
      <p v-else class="small muted">班级已归档，邀请码不可重置；恢复班级后可继续邀请学生。</p>
      <p class="foot"><Users :size="12" aria-hidden="true" /> 已加入 {{ detail?.student_count ?? 0 }} 名学生</p>
    </div>
  </section>

  <ConfirmDialog
    :open="resetOpen"
    title="重置邀请码"
    message="旧邀请码会立即失效，已加入的学生不受影响。"
    confirm-label="重置"
    tone="danger"
    :loading="resetting"
    @confirm="confirmResetInvite"
    @cancel="resetOpen = false"
  />

  <ConfirmDialog
    :open="resetTarget !== null"
    title="重置学生密码"
    :target="resetTarget ? `${resetTarget.name} · 学号 ${resetTarget.student_no}` : ''"
    message="重置后该学生的所有设备会退出登录；系统生成的一次性临时密码首次登录必须改密。历史成绩、XP 与 QQ 绑定都会保留。"
    :error="resetError"
    confirm-label="重置密码"
    tone="danger"
    :loading="resettingPassword"
    @confirm="confirmReset"
    @cancel="cancelReset"
  />

  <BaseModal
    :open="tempTarget !== null"
    title="一次性临时密码"
    :description="tempTarget ? `${tempTarget.name} · 学号 ${tempTarget.student_no}` : ''"
    :close-on-mask="false"
    hide-close
    @close="closeTemp"
  >
    <div class="stack">
      <p class="notice notice--warn">
        只显示这一次，关闭后无法再次查看。请当面或私聊交给学生，并要求首次登录后立即改密。
      </p>
      <div class="copy-code temp-code">
        <code>{{ tempPassword }}</code>
        <button class="btn btn--sm" type="button" @click="copyTemp">
          {{ tempCopied ? '已复制' : '复制' }}
        </button>
      </div>
      <p class="small muted">
        学生用临时密码登录后只能进入强制改密页；改密成功会退出所有旧会话。
      </p>
    </div>
    <template #footer>
      <BaseButton variant="primary" @click="closeTemp">我已保存，关闭</BaseButton>
    </template>
  </BaseModal>

  <ConfirmDialog
    :open="statusTarget !== null"
    :title="statusTarget?.status === 0 ? '恢复学生' : '停用学生'"
    :target="statusTarget ? `${statusTarget.name} · 学号 ${statusTarget.student_no}` : ''"
    :message="
      statusTarget?.status === 0
        ? '恢复后学生可重新登录并继续作答；旧登录会话不会恢复。'
        : '停用后该学生将退出所有设备，停止作答、通知与 QQ 服务；历史成绩、XP 与 QQ 绑定保留，可随时恢复。'
    "
    :confirm-label="statusTarget?.status === 0 ? '恢复' : '停用'"
    :tone="statusTarget?.status === 0 ? 'primary' : 'danger'"
    :loading="statusSaving"
    @confirm="confirmStatus"
    @cancel="statusTarget = null"
  />

  <ConfirmDialog
    :open="restoreOpen"
    title="恢复班级"
    message="恢复后班级回到活跃列表，可继续新增学生、发布试卷与发送通知；原学生需要重新登录。"
    confirm-label="恢复班级"
    tone="primary"
    :loading="restoring"
    @confirm="confirmRestore"
    @cancel="restoreOpen = false"
  />
</template>

<style scoped>
.temp-code {
  flex-wrap: wrap;
  align-items: center;
}

.temp-code code {
  padding: 8px 12px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.08em;
  user-select: all;
  word-break: break-all;
}

@media (max-width: 640px) {
  .temp-code code {
    font-size: 19px;
  }
}
</style>
