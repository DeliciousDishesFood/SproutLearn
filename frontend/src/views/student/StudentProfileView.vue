<!-- 学生个人中心：账号信息 + QQ 绑定码倒计时、复制、重新生成与解绑。 -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  AlertCircle,
  Check,
  CheckCircle2,
  ClipboardCopy,
  Clock3,
  KeyRound,
  Link2Off,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { bindingApi } from '@/api/binding'
import { toUserMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { QqBindCode } from '@/api/types'
import {
  BIND_CODE_FALLBACK_TTL_SECONDS,
  BIND_CODE_LENGTH,
  BIND_COUNTDOWN_TICK_MS,
} from '@/utils/constants'
import { copyText, formatCountdown, formatNumber } from '@/utils/format'

const auth = useAuthStore()
const ui = useUiStore()

const bindCode = ref<QqBindCode | null>(null)
const remaining = ref(0)
const generating = ref(false)
const generateError = ref('')
const copied = ref(false)
const copiedHint = ref(false)

const unbindOpen = ref(false)
const unbinding = ref(false)
const unbindError = ref('')

let countdownTimer: ReturnType<typeof setInterval> | null = null
let copiedTimer: ReturnType<typeof setTimeout> | null = null

const student = computed(() => (auth.user?.role === 'student' ? auth.user : null))
const isBound = computed(() => student.value?.qq_bound === true)
const isExpired = computed(() => bindCode.value !== null && remaining.value <= 0)
const totalSeconds = computed(() => {
  const value = bindCode.value?.expires_in ?? BIND_CODE_FALLBACK_TTL_SECONDS
  return value > 0 ? value : BIND_CODE_FALLBACK_TTL_SECONDS
})
const progressPercent = computed(() => {
  if (!bindCode.value) return 0
  return Math.max(0, Math.min(100, (remaining.value / totalSeconds.value) * 100))
})
const bindInstruction = computed(() => {
  if (!bindCode.value) return ''
  return `在班级群 @机器人 发送：绑定 ${bindCode.value.code}`
})
const codeDigits = computed(() => {
  const code = bindCode.value?.code ?? ''
  return code.padEnd(BIND_CODE_LENGTH, ' ').slice(0, BIND_CODE_LENGTH).split('')
})

function clearCountdown(): void {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function startCountdown(seconds: number): void {
  clearCountdown()
  remaining.value = Math.max(0, Math.floor(seconds))
  countdownTimer = setInterval(() => {
    if (remaining.value <= 1) {
      remaining.value = 0
      clearCountdown()
      return
    }
    remaining.value -= 1
  }, BIND_COUNTDOWN_TICK_MS)
}

function resetCopied(): void {
  if (copiedTimer !== null) {
    clearTimeout(copiedTimer)
    copiedTimer = null
  }
  copied.value = false
  copiedHint.value = false
}

async function generateCode(): Promise<void> {
  if (generating.value) return
  generating.value = true
  generateError.value = ''
  resetCopied()
  try {
    const result = await bindingApi.generateCode()
    bindCode.value = result
    startCountdown(result.expires_in)
    ui.success('绑定码已生成，请在有效期内发送给机器人')
  } catch (err) {
    generateError.value = toUserMessage(err)
  } finally {
    generating.value = false
  }
}

async function copyCode(): Promise<void> {
  if (!bindCode.value) return
  const ok = await copyText(bindCode.value.code)
  if (!ok) {
    ui.error('复制失败，请手动选择绑定码')
    return
  }
  copied.value = true
  ui.success('绑定码已复制')
  if (copiedTimer !== null) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copied.value = false
  }, 1800)
}

async function copyInstruction(): Promise<void> {
  if (!bindInstruction.value) return
  const ok = await copyText(bindInstruction.value)
  if (!ok) {
    ui.error('复制失败，请手动选择指令')
    return
  }
  copiedHint.value = true
  ui.success('绑定指令已复制')
  if (copiedTimer !== null) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copiedHint.value = false
  }, 1800)
}

async function refreshProfile(): Promise<void> {
  try {
    await auth.fetchMe()
  } catch {
    // 会话失效由全局客户端处理；其他错误保留本地已有信息。
  }
}

function openUnbind(): void {
  if (unbinding.value) return
  unbindError.value = ''
  unbindOpen.value = true
}

async function confirmUnbind(): Promise<void> {
  if (unbinding.value) return
  unbinding.value = true
  unbindError.value = ''
  try {
    await bindingApi.unbind()
    if (auth.user?.role === 'student') {
      auth.setUser({ ...auth.user, qq_bound: false })
    }
    bindCode.value = null
    remaining.value = 0
    clearCountdown()
    resetCopied()
    unbindOpen.value = false
    ui.success('QQ 已解绑，可重新生成绑定码')
  } catch (err) {
    unbindError.value = toUserMessage(err)
  } finally {
    unbinding.value = false
  }
}

onMounted(() => {
  void refreshProfile()
})

onBeforeUnmount(() => {
  clearCountdown()
  if (copiedTimer !== null) {
    clearTimeout(copiedTimer)
    copiedTimer = null
  }
})
</script>

<template>
  <div class="page page--narrow profile-page">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">STUDENT PROFILE</p>
        <h1 class="page-title">个人中心</h1>
        <p class="page-subtitle">确认你的班级身份，并把 QQ 绑定到青芽，方便在班级群里收到课堂提醒。</p>
      </div>
    </header>

    <div v-if="!student" class="panel panel-body">
      <AppSkeleton variant="title" />
      <AppSkeleton variant="text" :rows="3" />
    </div>

    <template v-else>
      <section class="panel profile-card" aria-labelledby="profile-title">
        <header class="panel-head">
          <div>
            <h2 id="profile-title" class="section-title">账号信息</h2>
            <p class="section-note">身份由加入班级时的邀请码确定。</p>
          </div>
          <AppTag :tone="isBound ? 'success' : 'neutral'" dot>
            {{ isBound ? 'QQ 已绑定' : 'QQ 未绑定' }}
          </AppTag>
        </header>

        <div class="panel-body">
          <div class="profile-identity">
            <span class="profile-avatar" aria-hidden="true">{{ student.name.slice(0, 1) }}</span>
            <div class="profile-identity__copy">
              <p class="profile-name">{{ student.name }}</p>
              <p class="profile-meta">
                <span>{{ student.class_name || '当前班级' }}</span>
                <span class="profile-dot" aria-hidden="true">·</span>
                <span class="mono">{{ student.student_no }}</span>
              </p>
            </div>
          </div>

          <dl class="profile-grid">
            <div class="profile-item">
              <dt><UserRound :size="14" :stroke-width="1.8" aria-hidden="true" /> 班级编号</dt>
              <dd class="mono">{{ student.class_code }}</dd>
            </div>
            <div class="profile-item">
              <dt><ShieldCheck :size="14" :stroke-width="1.8" aria-hidden="true" /> 学号</dt>
              <dd class="mono">{{ student.student_no }}</dd>
            </div>
            <div class="profile-item">
              <dt><KeyRound :size="14" :stroke-width="1.8" aria-hidden="true" /> 当前等级</dt>
              <dd>Lv. {{ student.level ?? 1 }}</dd>
            </div>
            <div class="profile-item">
              <dt><Clock3 :size="14" :stroke-width="1.8" aria-hidden="true" /> 累计经验值</dt>
              <dd class="tabular">{{ formatNumber(student.xp_total ?? 0) }}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section class="panel binding-card" aria-labelledby="binding-title">
        <header class="panel-head">
          <div>
            <h2 id="binding-title" class="section-title">QQ 绑定</h2>
            <p class="section-note">
              绑定码由数字组成，生成后 {{ formatCountdown(totalSeconds) }} 内有效；重新生成会让旧码立即失效。
            </p>
          </div>
          <AppTag :tone="isBound ? 'success' : 'warning'" dot>
            {{ isBound ? '已绑定' : '待绑定' }}
          </AppTag>
        </header>

        <div class="panel-body binding-body">
          <template v-if="isBound">
            <div class="bound-panel">
              <span class="bound-panel__icon">
                <CheckCircle2 :size="26" :stroke-width="1.7" aria-hidden="true" />
              </span>
              <div class="bound-panel__copy">
                <h3>QQ 已绑定到当前学号</h3>
                <p>青芽可以通过机器人向你发送课堂提醒。更换 QQ 时，先解绑再生成新的绑定码。</p>
              </div>
              <AppButton variant="danger-outline" @click="openUnbind">
                <Link2Off :size="15" :stroke-width="1.8" />
                解绑 QQ
              </AppButton>
            </div>

            <p v-if="generateError" class="form-error" role="alert">
              <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
              <span>{{ generateError }}</span>
            </p>
          </template>

          <template v-else-if="bindCode">
            <div class="code-stage" :class="{ 'code-stage--expired': isExpired }">
              <div class="code-stage__head">
                <span class="code-stage__label">
                  <MessageCircle :size="15" :stroke-width="1.8" aria-hidden="true" />
                  你的 QQ 绑定码
                </span>
                <span v-if="isExpired" class="code-stage__expired">已过期</span>
                <span v-else class="code-stage__timer tabular">
                  <Clock3 :size="14" :stroke-width="1.8" aria-hidden="true" />
                  剩余 {{ formatCountdown(remaining) }}
                </span>
              </div>

              <div class="code-digits" aria-label="QQ 绑定码">
                <span v-for="(digit, index) in codeDigits" :key="index" class="code-digit mono">
                  {{ digit === ' ' ? '·' : digit }}
                </span>
              </div>

              <p v-if="!isExpired" class="code-instruction">{{ bindInstruction }}</p>
              <p v-else class="code-instruction code-instruction--expired">
                绑定码已失效，请重新生成后再发送给机器人。
              </p>

              <div
                class="code-progress"
                role="progressbar"
                :aria-valuenow="Math.round(progressPercent)"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="`绑定码剩余 ${remaining} 秒`"
              >
                <span class="code-progress__fill" :style="{ width: `${progressPercent}%` }" />
              </div>

              <div class="code-actions">
                <AppButton variant="primary" :disabled="isExpired" @click="copyCode">
                  <Check v-if="copied" :size="15" :stroke-width="2" />
                  <ClipboardCopy v-else :size="15" :stroke-width="1.8" />
                  {{ copied ? '已复制' : '复制绑定码' }}
                </AppButton>
                <AppButton variant="ghost" :disabled="isExpired" @click="copyInstruction">
                  <Check v-if="copiedHint" :size="15" :stroke-width="2" />
                  <MessageCircle v-else :size="15" :stroke-width="1.8" />
                  {{ copiedHint ? '已复制' : '复制绑定指令' }}
                </AppButton>
                <AppButton variant="secondary" :loading="generating" @click="generateCode">
                  <RefreshCw v-if="!generating" :size="15" :stroke-width="1.8" />
                  {{ isExpired ? '重新生成' : '换一个绑定码' }}
                </AppButton>
              </div>
            </div>

            <p v-if="generateError" class="form-error" role="alert">
              <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
              <span>{{ generateError }}</span>
            </p>

            <div class="binding-usage">
              <h3>怎么完成绑定？</h3>
              <ol>
                <li>打开班级群，找到青芽机器人。</li>
                <li>在群里 @机器人，发送上方展示的完整绑定指令。</li>
                <li>机器人回复绑定成功后，本页状态会变为「QQ 已绑定」。</li>
              </ol>
              <p>绑定码只能使用一次，{{ formatCountdown(totalSeconds) }} 内有效。请不要把绑定码发给班外同学。</p>
            </div>
          </template>

          <template v-else>
            <div class="binding-empty">
              <span class="binding-empty__art" aria-hidden="true">
                <MessageCircle :size="30" :stroke-width="1.5" />
              </span>
              <h3>还没有绑定 QQ</h3>
              <p>
                生成一个 {{ BIND_CODE_LENGTH }} 位一次性绑定码，在班级群 @机器人 发送指定指令即可完成绑定。
                绑定码会在 {{ formatCountdown(totalSeconds) }} 后自动失效。
              </p>
              <AppButton variant="primary" :loading="generating" @click="generateCode">
                <ClipboardCopy v-if="!generating" :size="16" :stroke-width="1.9" />
                生成绑定码
              </AppButton>
            </div>

            <p v-if="generateError" class="form-error" role="alert">
              <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
              <span>{{ generateError }}</span>
            </p>
          </template>

          <div class="binding-note">
            <ShieldCheck :size="16" :stroke-width="1.8" aria-hidden="true" />
            <p>
              QQ 绑定只关联当前班级与学号，一个 QQ 不能同时绑定多个学号。
              {{
                isBound
                  ? '如需更换，请先解绑当前 QQ，再重新生成绑定码。'
                  : '生成绑定码后，在班级群 @机器人 发送即可完成绑定。'
              }}
            </p>
          </div>
        </div>
      </section>
    </template>

    <AppModal
      v-model="unbindOpen"
      title="解绑当前 QQ？"
      description="解绑后，青芽将无法通过 QQ 向你发送提醒。如需继续使用，需要重新生成绑定码并绑定。"
      confirm-text="解绑 QQ"
      confirm-variant="danger"
      :confirm-loading="unbinding"
      width="440px"
      @confirm="confirmUnbind"
    >
      <div class="unbind-body">
        <span class="unbind-icon" aria-hidden="true"><Link2Off :size="18" :stroke-width="1.8" /></span>
        <p>当前学号 <strong class="mono">{{ student?.student_no }}</strong> 的 QQ 绑定会被移除。</p>
      </div>
      <p v-if="unbindError" class="form-error" role="alert">
        <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
        <span>{{ unbindError }}</span>
      </p>
    </AppModal>
  </div>
</template>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.profile-card,
.binding-card {
  overflow: hidden;
}

.profile-identity {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding-bottom: var(--sp-5);
  border-bottom: 1px solid var(--color-border);
}

.profile-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  border-radius: 999px;
  color: var(--color-accent);
  background: var(--color-primary);
  font-size: var(--fs-xl);
  font-weight: 600;
}

.profile-name {
  font-size: var(--fs-xl);
  font-weight: 600;
}

.profile-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-1);
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.profile-dot {
  padding: 0 2px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-3);
  margin-top: var(--sp-4);
}

.profile-item {
  min-width: 0;
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.profile-item dt {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.profile-item dd {
  font-size: var(--fs-sm);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.binding-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.bound-panel {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-4);
  padding: var(--sp-5);
  border: 1px solid color-mix(in srgb, var(--color-success) 24%, var(--color-border));
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-success) 6%, var(--color-surface));
}

.bound-panel__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 999px;
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 11%, var(--color-surface));
}

.bound-panel__copy {
  flex: 1;
  min-width: 0;
}

.bound-panel__copy h3 {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.bound-panel__copy p {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.75;
}

.code-stage {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-5);
  border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-border));
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--color-accent) 10%, transparent) 0, transparent 38%),
    var(--color-primary-soft);
}

.code-stage--expired {
  border-color: color-mix(in srgb, var(--color-danger) 26%, var(--color-border));
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--color-danger) 8%, transparent) 0, transparent 38%),
    color-mix(in srgb, var(--color-danger) 4%, var(--color-surface));
}

.code-stage__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.code-stage__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.code-stage__timer {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.code-stage__expired {
  color: var(--color-danger);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.code-digits {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.code-digit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 56px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
  box-shadow: var(--shadow-1);
}

.code-stage--expired .code-digit {
  color: var(--color-text-muted);
  opacity: 0.7;
}

.code-instruction {
  padding: var(--sp-3) var(--sp-4);
  border: 1px dashed color-mix(in srgb, var(--color-primary) 32%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-surface) 72%, transparent);
  color: var(--color-text);
  font-size: var(--fs-sm);
  font-weight: 600;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.code-instruction--expired {
  color: var(--color-text-muted);
  font-weight: 400;
}

.code-progress {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.code-progress__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width 200ms linear;
}

.code-stage--expired .code-progress__fill {
  background: var(--color-text-muted);
}

.code-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.binding-usage {
  padding: var(--sp-4) var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.binding-usage h3 {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.binding-usage ol {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: var(--sp-2);
  padding-left: 18px;
  color: var(--color-text);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.binding-usage p {
  margin-top: var(--sp-3);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.binding-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-7) var(--sp-5);
  text-align: center;
}

.binding-empty__art {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 66px;
  height: 66px;
  border: 1px dashed color-mix(in srgb, var(--color-primary) 34%, transparent);
  border-radius: 999px;
  color: var(--color-primary);
  background:
    radial-gradient(circle at 50% 56%, var(--color-primary-soft) 0, transparent 70%),
    var(--color-surface-alt);
}

.binding-empty h3 {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.binding-empty p {
  max-width: 460px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

.binding-note {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.7;
}

.binding-note svg {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--color-primary);
}

.unbind-body {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.unbind-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 9%, transparent);
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .bound-panel {
    flex-direction: column;
  }

  .bound-panel > :deep(.app-button) {
    width: 100%;
  }

  .code-digit {
    width: 36px;
    height: 48px;
    font-size: 23px;
  }

  .code-actions :deep(.app-button) {
    flex: 1;
  }
}
</style>
