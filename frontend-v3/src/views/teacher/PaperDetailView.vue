<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { GroupNoticeStatus, PaperDetail } from '@/api/contract'
import {
  PAPER_KIND_LABEL,
  PAPER_STATUS_LABEL,
  QUESTION_TYPE_LABEL,
  formatAnswer,
  formatDateTime,
  paperStatusTone,
} from '@/utils/format'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const paperId = computed(() => Number(route.params.paperId))

const kindOptions = [
  { label: '练习', value: 'practice' },
  { label: '作业', value: 'homework' },
  { label: '考试', value: 'exam' },
]
const blankModeOptions = [
  { label: '智能判定', value: 'smart' },
  { label: '严格判定', value: 'strict' },
]

const paper = ref<PaperDetail | null>(null)
const loading = ref(true)
const errorText = ref('')
const acting = ref(false)
const groupNotice = ref<GroupNoticeStatus | null>(null)

const editOpen = ref(false)
const saving = ref(false)
const editError = ref('')
const editForm = reactive({
  title: '',
  duration_minutes: 30,
  blank_mode: 'smart' as 'smart' | 'strict',
  kind: 'practice' as 'practice' | 'homework' | 'exam',
  due_at: '',
})

const isDraft = computed(() => paper.value?.status === 'draft')
const isPublished = computed(() => paper.value?.status === 'published')

function toInputDateTime(value: string | null | undefined): string {
  if (!value) return ''
  return value.replace(' ', 'T').slice(0, 16)
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const detail = await papersApi.detail(paperId.value)
    paper.value = detail
    editForm.title = detail.title
    editForm.duration_minutes = detail.duration_minutes
    editForm.blank_mode = detail.blank_mode
    editForm.kind = detail.kind
    editForm.due_at = toInputDateTime(detail.due_at)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveEdit(): Promise<void> {
  if (!editForm.title.trim()) {
    editError.value = '试卷标题不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    const detail = await papersApi.update(paperId.value, {
      title: editForm.title.trim(),
      duration_minutes: editForm.duration_minutes,
      blank_mode: editForm.blank_mode,
      kind: editForm.kind,
      due_at: editForm.due_at ? editForm.due_at : null,
    })
    paper.value = detail
    editOpen.value = false
    toast.success('试卷设置已保存')
  } catch (error) {
    editError.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

const publishOpen = ref(false)
const withdrawOpen = ref(false)

async function publish(): Promise<void> {
  if (!paper.value || paper.value.status === 'published') return
  publishOpen.value = true
}

async function confirmPublish(): Promise<void> {
  acting.value = true
  errorText.value = ''
  try {
    const result = await papersApi.publish(paperId.value)
    paper.value = result
    groupNotice.value = result.group_notice ?? null
    publishOpen.value = false
    toast.success('试卷已发布')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    acting.value = false
  }
}

async function withdraw(): Promise<void> {
  if (!paper.value || paper.value.status !== 'published') return
  withdrawOpen.value = true
}

async function confirmWithdraw(): Promise<void> {
  acting.value = true
  errorText.value = ''
  try {
    const detail = await papersApi.withdraw(paperId.value)
    paper.value = detail
    withdrawOpen.value = false
    toast.success('试卷已撤回')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    acting.value = false
  }
}

function copyNotice(): void {
  const text = paper.value
    ? `【作业通知】${paper.value.title} 已发布，请到青芽查看并按时完成。`
    : ''
  if (!text) return
  navigator.clipboard?.writeText(text).then(
    () => toast.success('通知文案已复制'),
    () => toast.error('复制失败，请手动复制'),
  )
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink v-if="paper" :to="`/teacher/classes/${paper.class_id}/papers`">试卷</RouterLink>
        <template v-else>试卷</template> · 详情
      </p>
      <h1>{{ paper?.title ?? '试卷详情' }}</h1>
      <p class="page-head__lede">
        {{ paper ? `${PAPER_KIND_LABEL[paper.kind]} · ${paper.question_count} 题 · 满分 ${paper.total_score}` : '—' }}
      </p>
    </div>
    <div v-if="paper" class="page-head__actions">
      <RouterLink
        v-if="paper.status !== 'draft'"
        class="btn"
        :to="`/teacher/papers/${paper.id}/attempts`"
      >
        查看作答
      </RouterLink>
      <BaseButton v-if="isDraft" @click="editOpen = true">编辑设置</BaseButton>
      <BaseButton v-if="isPublished" :loading="acting" @click="withdraw">撤回</BaseButton>
      <BaseButton v-else variant="primary" :loading="acting" @click="publish">
        {{ paper.status === 'closed' ? '重新发布' : '发布试卷' }}
      </BaseButton>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">
    {{ errorText }}
    <RouterLink class="btn btn--sm" style="margin-left: 8px" to="/teacher/classes">返回班级列表</RouterLink>
  </p>
  <p v-if="loading" class="loading-line">读取中…</p>

  <template v-else-if="paper">
    <p v-if="groupNotice === 'failed'" class="notice notice--warn">
      群通知失败，但试卷已发布。可复制下面的文案，手动发到班级群。
      <span class="copy-code" style="margin-left: 8px">
        <button class="btn btn--sm" type="button" @click="copyNotice">复制「作业通知」文案</button>
      </span>
    </p>
    <p v-else-if="groupNotice === 'skipped'" class="notice">
      班级群未绑定机器人，本次未发送群通知；试卷已正常发布。
    </p>

    <section class="card stack">
      <div class="row row--between row--wrap">
        <div class="kv">
          <span>状态：<BaseBadge :tone="paperStatusTone(paper.status)">{{ PAPER_STATUS_LABEL[paper.status] }}</BaseBadge></span>
          <span>用途：<b>{{ PAPER_KIND_LABEL[paper.kind] }}</b></span>
          <span>组卷：<b>{{ paper.mode === 'fixed' ? '固定题目' : '随机抽题' }}</b></span>
          <span>时长：<b>{{ paper.duration_minutes > 0 ? `${paper.duration_minutes} 分钟` : '不限时' }}</b></span>
          <span>满分：<b>{{ paper.total_score }}</b></span>
        </div>
        <span class="small tertiary">创建于 {{ formatDateTime(paper.created_at) }}</span>
      </div>
      <div class="kv">
        <span>试卷截止：<b>{{ paper.due_at ? formatDateTime(paper.due_at) : '未设置截止' }}</b></span>
        <span>发布时间：<b>{{ formatDateTime(paper.published_at) }}</b></span>
        <span v-if="paper.banks.length">来源题库：<b>{{ paper.banks.map((bank) => bank.name).join('、') }}</b></span>
      </div>
      <p class="small tertiary">
        说明：试卷截止时间决定学生能否进入作答；单次作答倒计时由作答记录单独计算，两者不是同一个时间。
      </p>
    </section>

    <section class="card">
      <header class="card__head">
        <h2>题目清单</h2>
        <span class="card__meta">共 {{ paper.questions.length }} 题</span>
      </header>
      <div class="stack" style="margin-top: 12px">
        <article v-for="question in paper.questions" :key="question.id" class="notice" style="padding: 14px">
          <div class="row row--between row--wrap">
            <span class="strong">第 {{ question.seq }} 题</span>
            <span class="small tertiary">
              {{ QUESTION_TYPE_LABEL[question.type] }} · {{ question.score }} 分 · {{ question.knowledge_tag }}
            </span>
          </div>
          <p style="margin-top: 8px; white-space: pre-wrap; line-height: 1.7">{{ question.stem }}</p>
          <div v-if="question.options && question.options.length" class="stack" style="gap: 4px; margin-top: 8px">
            <span v-for="option in question.options" :key="option.key" class="small muted">
              {{ option.key }}. {{ option.text }}
            </span>
          </div>
          <div class="answer-grid">
            <div><span>标准答案</span><b>{{ formatAnswer(question.answer, question.type) }}</b></div>
            <div><span>解析</span><b>{{ question.analysis || '暂无解析' }}</b></div>
          </div>
        </article>
      </div>
    </section>
  </template>

  <BaseModal :open="editOpen" title="编辑试卷设置" description="已发布的试卷不可修改内容。" @close="editOpen = false">
    <div class="form">
      <BaseField label="试卷标题" required>
        <input v-model="editForm.title" class="input" type="text" />
      </BaseField>
      <div class="form-row">
        <BaseField label="用途">
          <BaseSelect v-model="editForm.kind" :options="kindOptions" aria-label="试卷用途" />
        </BaseField>
        <BaseField label="时长（分钟）">
          <input v-model.number="editForm.duration_minutes" class="input" type="number" min="0" max="300" />
        </BaseField>
      </div>
      <div class="form-row">
        <BaseField label="填空判定">
          <BaseSelect v-model="editForm.blank_mode" :options="blankModeOptions" aria-label="填空题判定" />
        </BaseField>
        <BaseField label="截止时间">
          <input v-model="editForm.due_at" class="input" type="datetime-local" />
        </BaseField>
      </div>
      <p v-if="editError" class="form-error">{{ editError }}</p>
    </div>
    <template #footer>
      <BaseButton @click="editOpen = false">取消</BaseButton>
      <BaseButton variant="primary" :loading="saving" @click="saveEdit">保存</BaseButton>
    </template>
  </BaseModal>

  <ConfirmDialog
    :open="publishOpen"
    title="发布试卷"
    :target="paper?.title ?? ''"
    message="发布后学生即可看到并作答，通知会按班级配置推送。"
    confirm-label="发布"
    tone="primary"
    :loading="acting"
    @confirm="confirmPublish"
    @cancel="publishOpen = false"
  />

  <ConfirmDialog
    :open="withdrawOpen"
    title="撤回试卷"
    :target="paper?.title ?? ''"
    message="撤回后学生列表不再显示这份试卷，已提交的作答仍保留。"
    confirm-label="撤回"
    tone="danger"
    :loading="acting"
    @confirm="confirmWithdraw"
    @cancel="withdrawOpen = false"
  />
</template>
