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

function toPayload(next: BotConfig): BotConfigPayload {
  return {
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

function snapshot(payload: BotConfigPayload): string {
  const normalized: BotConfigPayload = {
    ...payload,
    app_id: payload.app_id.trim(),
    callback_url: (payload.callback_url ?? '').trim(),
  }
  return JSON.stringify(normalized, Object.keys(normalized).sort())
}

/** 表单与最近一次服务端配置不一致即视为未保存。 */
const dirty = computed(() => {
  if (!config.value) return false
  return snapshot(form.value) !== snapshot(toPayload(config.value))
})

const savedTestStatus = computed(() => {
  const status = config.value?.last_check_status ?? 'never'
  if (status === 'ok') return { text: '连接正常', tone: 'lime' as const }
  if (status === 'failed') return { text: '连接失败', tone: 'danger' as const }
  return { text: '未检测', tone: 'plain' as const }
})

const groupBound = computed(() => Boolean(config.value?.group_openid))

const teacherBoundText = computed(() => {
  if (!config.value) return '未绑定'
  if (config.value.teacher_bound_at) return `已绑定 · ${formatDateTime(config.value.teacher_bound_at)}`
  return '未绑定'
})

const testText = computed(() => {
  if (testResult.value) {
    return `${testResult.value.ok ? '连接成功' : '连接失败'}：${testResult.value.message}`
  }
  return ''
})

function applyConfig(next: BotConfig): void {
  config.value = next
  form.value = toPayload(next)
  testResult.value = null
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
    // 用服务端返回值刷新快照，但保留未提交的本地输入（例如保存后继续改字）。
    const pending = { ...form.value }
    applyConfig(next)
    form.value = { ...pending, app_id: next.app_id ?? pending.app_id }
    toast.success('机器人配置已保存')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

async function test(): Promise<void> {
  if (dirty.value) {
    toast.info('请先保存配置，再测试连通性')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await botApi.test(props.classId)
    // 同步服务端检测状态，不伪造 worker 在线状态。
    if (config.value) {
      config.value = {
        ...config.value,
        last_check_status: testResult.value.ok ? 'ok' : 'failed',
        last_check_at: testResult.value.last_check_at,
      }
    }
  } catch (error) {
    testResult.value = {
      ok: false,
      message: toUserMessage(error),
      expires_in: null,
      last_check_at: null,
      last_check_status: 'failed',
    }
    if (config.value) {
      config.value = { ...config.value, last_check_status: 'failed', last_check_at: null }
    }
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

async function copyCode(): Promise<void> {
  if (!groupCode.value) return
  try {
    await navigator.clipboard.writeText(groupCode.value.code)
    toast.success('绑定码已复制')
  } catch {
    toast.error('复制失败，请长按或选中下方绑定码手动复制')
  }
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

      <ol class="bot-steps">
        <li class="bot-step">
          <div class="bot-step__head">
            <span class="bot-step__no" aria-hidden="true">1</span>
            <strong>保存配置</strong>
            <BaseBadge :tone="dirty ? 'amber' : 'lime'">{{ dirty ? '未保存' : '已保存' }}</BaseBadge>
          </div>
          <p class="bot-step__body">App ID、回调与通知开关保存后才会生效。</p>
          <BaseButton variant="primary" size="sm" :loading="saving" :disabled="!dirty" @click="save">
            保存配置
          </BaseButton>
        </li>

        <li class="bot-step">
          <div class="bot-step__head">
            <span class="bot-step__no" aria-hidden="true">2</span>
            <strong>测试连通性</strong>
            <BaseBadge :tone="savedTestStatus.tone">{{ savedTestStatus.text }}</BaseBadge>
          </div>
          <p class="bot-step__body">
            只检测服务端已保存的配置。
            <template v-if="config?.last_check_at">最近 {{ formatDateTime(config.last_check_at) }}。</template>
            <template v-if="dirty"> 当前有未保存修改，请先保存再测试。</template>
          </p>
          <BaseButton size="sm" :loading="testing" :disabled="dirty || saving" @click="test">
            测试连通性
          </BaseButton>
        </li>

        <li class="bot-step">
          <div class="bot-step__head">
            <span class="bot-step__no" aria-hidden="true">3</span>
            <strong>群绑定</strong>
            <BaseBadge :tone="groupBound ? 'lime' : 'plain'">{{ groupBound ? '已绑定' : '未绑定' }}</BaseBadge>
          </div>
          <p class="bot-step__body">在班级 QQ 群内发送绑定码即可完成绑定。</p>
          <div class="row row--wrap">
            <BaseButton size="sm" @click="generateCode">
              {{ groupCode ? '重新生成群绑定码' : '生成群绑定码' }}
            </BaseButton>
            <span v-if="groupCode" class="small text-3" aria-live="polite">
              {{
                codeLeft > 0
                  ? `${Math.floor(codeLeft / 60)} 分 ${codeLeft % 60} 秒后失效`
                  : '已过期，请重新生成'
              }}
            </span>
          </div>
          <div v-if="groupCode" class="copy-code">
            <code style="user-select: all">{{ groupCode.code }}</code>
            <button class="btn btn--sm" type="button" @click="copyCode">复制</button>
          </div>
        </li>

        <li class="bot-step">
          <div class="bot-step__head">
            <span class="bot-step__no" aria-hidden="true">4</span>
            <strong>学生绑定</strong>
            <BaseBadge tone="plain">由学生发起</BaseBadge>
          </div>
          <p class="bot-step__body">
            学生需在自己的「我的」页面生成绑定码，再私聊机器人发送；教师端不展示学生绑定明细。
          </p>
        </li>
      </ol>

      <p v-if="testText" class="notice" :class="testResult?.ok ? 'notice--lime' : 'notice--danger'">
        {{ testText }}
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

      <p class="notice notice--lime">
        AppSecret
        {{ config?.secret_managed_by_env ? '由服务端环境变量管理，前端不保存、不回显。' : '由服务端托管，前端不输入。' }}
      </p>

      <details class="bot-tech">
        <summary>技术详情</summary>
        <div class="form-row">
          <BaseField label="App ID">
            <input v-model="form.app_id" class="input" type="text" placeholder="请输入 App ID" />
          </BaseField>
          <BaseField label="回调地址" hint="留空则使用服务端默认回调">
            <input v-model="form.callback_url" class="input" type="text" placeholder="https://…" />
          </BaseField>
        </div>
        <dl class="bot-tech__kv">
          <div><dt>教师绑定</dt><dd>{{ teacherBoundText }}</dd></div>
          <div><dt>群 OpenID</dt><dd class="mono">{{ config?.group_openid ?? '未绑定' }}</dd></div>
          <div><dt>教师 OpenID</dt><dd class="mono">{{ config?.teacher_openid ?? '未绑定' }}</dd></div>
        </dl>
      </details>
    </template>
  </section>
</template>

<style scoped>
.bot-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bot-step {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line-soft);
}

.bot-step:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.bot-step__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bot-step__head strong {
  font-size: 13.5px;
  font-weight: 600;
}

.bot-step__no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--lime-soft);
  color: var(--lime-text);
  font-size: 11.5px;
  font-weight: 600;
}

.bot-step__body {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}

.bot-step .btn {
  align-self: flex-start;
}

.bot-tech {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-alt);
}

.bot-tech summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.bot-tech[open] summary {
  margin-bottom: 8px;
}

.bot-tech__kv {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 8px 0 0;
  font-size: 12px;
}

.bot-tech__kv div {
  display: flex;
  gap: 8px;
}

.bot-tech__kv dt {
  color: var(--text-3);
}

.bot-tech__kv dd {
  margin: 0;
  word-break: break-all;
}
</style>
