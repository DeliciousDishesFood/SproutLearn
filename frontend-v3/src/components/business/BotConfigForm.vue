<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { botApi } from '@/api/bot'
import { toUserMessage } from '@/api/client'
import type { BotChatMode, BotConfig, BotConfigPayload, BotTestResult, GroupBindCode } from '@/api/contract'
import { formatDateTime } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ classId: number }>()
const toast = useToast()

const config = ref<BotConfig | null>(null)
const form = ref<BotConfigPayload>({
  app_id: '',
  callback_url: '',
  enabled: false,
  binding_enabled: true,
  notify_assignment: true,
  notify_due_soon: true,
  mention_missing: true,
  allow_query_assignments: true,
  allow_query_scores: true,
  bot_chat_mode: 'balanced',
  bot_chat_enabled: false,
  bot_chat_max_chars: 200,
})
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<BotTestResult | null>(null)
const groupCode = ref<GroupBindCode | null>(null)
const codeLeft = ref(0)
const errorText = ref('')
let codeTimer: number | null = null

const modeOptions: Array<{ value: BotChatMode; label: string }> = [
  { value: 'strict', label: '严格命令' },
  { value: 'balanced', label: '知识优先' },
  { value: 'free', label: '自由回答' },
]

const bindingText = computed(() => {
  if (!config.value) return '未知'
  if (config.value.teacher_bound_at) return `已绑定 · ${formatDateTime(config.value.teacher_bound_at)}`
  return '未绑定'
})

function applyConfig(next: BotConfig): void {
  config.value = next
  form.value = {
    app_id: next.app_id ?? '',
    callback_url: next.callback_url ?? '',
    enabled: next.enabled,
    binding_enabled: next.binding_enabled,
    notify_assignment: next.notify_assignment,
    notify_due_soon: next.notify_due_soon,
    mention_missing: next.mention_missing,
    allow_query_assignments: next.allow_query_assignments,
    allow_query_scores: next.allow_query_scores,
    bot_chat_mode: next.bot_chat_mode ?? 'balanced',
    bot_chat_enabled: next.bot_chat_enabled,
    bot_chat_max_chars: next.bot_chat_max_chars ?? 200,
  }
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    applyConfig(await botApi.get(props.classId))
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  if (!form.value.app_id.trim()) {
    errorText.value = 'App ID 必填'
    return
  }
  saving.value = true
  errorText.value = ''
  try {
    const next = await botApi.save(props.classId, { ...form.value, app_id: form.value.app_id.trim() })
    applyConfig(next)
    toast.success('机器人配置已保存')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

async function test(): Promise<void> {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await botApi.test(props.classId)
  } catch (error) {
    testResult.value = { ok: false, message: toUserMessage(error), expires_in: null, last_check_at: null, last_check_status: 'failed' }
  } finally {
    testing.value = false
  }
}

async function generateCode(): Promise<void> {
  try {
    groupCode.value = await botApi.generateGroupCode(props.classId)
    codeLeft.value = Math.max(0, groupCode.value.expires_in)
    if (codeTimer !== null) window.clearInterval(codeTimer)
    codeTimer = window.setInterval(() => {
      codeLeft.value = Math.max(0, codeLeft.value - 1)
      if (codeLeft.value === 0 && codeTimer !== null) {
        window.clearInterval(codeTimer)
        codeTimer = null
      }
    }, 1000)
  } catch (error) {
    toast.error(toUserMessage(error))
  }
}

function copyCode(): void {
  if (!groupCode.value) return
  navigator.clipboard?.writeText(groupCode.value.code).then(
    () => toast.success('绑定码已复制'),
    () => toast.error('复制失败，请手动复制'),
  )
}

onMounted(load)
onBeforeUnmount(() => {
  if (codeTimer !== null) window.clearInterval(codeTimer)
})
</script>

<template>
  <section class="card stack">
    <header class="card__head">
      <h2>QQ 机器人</h2>
      <BaseBadge :tone="config?.enabled ? 'lime' : 'plain'">
        {{ config?.enabled ? '已启用' : '未启用' }}
      </BaseBadge>
    </header>

    <p v-if="loading" class="loading-line">正在读取机器人配置…</p>
    <template v-else>
      <p v-if="errorText" class="form-error">{{ errorText }}</p>

      <div class="form-row">
        <BaseField label="App ID" required hint="QQ 开放平台机器人 AppID">
          <input v-model="form.app_id" class="input" type="text" placeholder="请输入 App ID" />
        </BaseField>
        <BaseField label="回调地址" hint="留空则使用服务端默认回调">
          <input v-model="form.callback_url" class="input" type="text" placeholder="https://…" />
        </BaseField>
      </div>

      <p class="notice notice--lime">
        AppSecret {{ config?.secret_managed_by_env ? '由服务端环境变量管理，前端不保存、不回显。' : '由服务端托管，前端不输入。' }}
      </p>

      <div class="form-row">
        <BaseField label="AI 问答模式">
          <BaseSelect v-model="form.bot_chat_mode" :options="modeOptions" aria-label="AI 问答模式" />
        </BaseField>
        <BaseField label="单次回答最大字数">
          <input v-model.number="form.bot_chat_max_chars" class="input" type="number" min="50" max="1000" />
        </BaseField>
      </div>

      <div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>启用机器人</strong><span>关闭后群内不再响应任何消息</span></span>
          <label class="switch"><input v-model="form.enabled" type="checkbox" aria-label="启用机器人" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>允许 AI 回答</strong><span>关闭后停用全部 AI 问答</span></span>
          <label class="switch"><input v-model="form.bot_chat_enabled" type="checkbox" aria-label="允许 AI 回答" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>允许学生绑定</strong><span>学生可用绑定码绑定 QQ</span></span>
          <label class="switch"><input v-model="form.binding_enabled" type="checkbox" aria-label="允许学生绑定" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>作业发布通知</strong><span>发布试卷时向班级群推送</span></span>
          <label class="switch"><input v-model="form.notify_assignment" type="checkbox" aria-label="作业发布通知" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>截止前提醒</strong><span>临近截止时提醒未提交学生</span></span>
          <label class="switch"><input v-model="form.notify_due_soon" type="checkbox" aria-label="截止前提醒" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>@ 未交学生</strong><span>提醒时点名未提交学生</span></span>
          <label class="switch"><input v-model="form.mention_missing" type="checkbox" aria-label="@ 未交学生" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>允许查询作业</strong><span>学生可私聊查询待办作业</span></span>
          <label class="switch"><input v-model="form.allow_query_assignments" type="checkbox" aria-label="允许查询作业" /><i /></label>
        </div>
        <div class="toggle-row">
          <span class="toggle-row__text"><strong>允许查询成绩</strong><span>学生可私聊查询成绩</span></span>
          <label class="switch"><input v-model="form.allow_query_scores" type="checkbox" aria-label="允许查询成绩" /><i /></label>
        </div>
      </div>

      <div class="kv">
        <span>教师绑定：<b>{{ bindingText }}</b></span>
        <span>群 OpenID：<b>{{ config?.group_openid ?? '未绑定' }}</b></span>
        <span>
          最近检测：
          <b>{{ config?.last_check_status ?? 'never' }}</b>
          <template v-if="config?.last_check_at"> · {{ formatDateTime(config.last_check_at) }}</template>
        </span>
      </div>

      <p v-if="testResult" class="notice" :class="testResult.ok ? 'notice--lime' : 'notice--danger'">
        连通性测试{{ testResult.ok ? '成功' : '失败' }}：{{ testResult.message }}
      </p>

      <div class="row row--wrap">
        <BaseButton variant="primary" :loading="saving" @click="save">保存配置</BaseButton>
        <BaseButton :loading="testing" @click="test">测试连通性</BaseButton>
        <BaseButton @click="generateCode">生成群绑定码</BaseButton>
      </div>

      <div v-if="groupCode" class="notice">
        <div class="copy-code">
          <span>群绑定码</span>
          <code>{{ groupCode.code }}</code>
          <button class="btn btn--sm" type="button" @click="copyCode">复制</button>
          <span class="tertiary small">
            {{ codeLeft > 0 ? `${Math.floor(codeLeft / 60)} 分 ${codeLeft % 60} 秒后失效` : '已过期，请重新生成' }}
          </span>
        </div>
        <p class="small tertiary" style="margin-top: 6px">
          在班级 QQ 群内发送该绑定码即可完成群绑定，10 分钟内有效。
        </p>
      </div>
    </template>
  </section>
</template>
