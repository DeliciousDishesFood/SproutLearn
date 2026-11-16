<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { bindingApi } from '@/api/binding'
import { toUserMessage } from '@/api/client'
import type { QqBindCode } from '@/api/contract'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const toast = useToast()

const loading = ref(true)
const errorText = ref('')
const code = ref<QqBindCode | null>(null)
const left = ref(0)
const generating = ref(false)
const unbinding = ref(false)
let timer: number | null = null

const student = computed(() => auth.student)

function stopTimer(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function startTimer(seconds: number): void {
  stopTimer()
  left.value = Math.max(0, seconds)
  timer = window.setInterval(() => {
    left.value = Math.max(0, left.value - 1)
    if (left.value === 0) stopTimer()
  }, 1000)
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    await auth.fetchMe()
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function generate(): Promise<void> {
  generating.value = true
  errorText.value = ''
  try {
    code.value = await bindingApi.createCode()
    startTimer(code.value.expires_in)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    generating.value = false
  }
}

const unbindOpen = ref(false)

function unbind(): void {
  unbindOpen.value = true
}

async function confirmUnbind(): Promise<void> {
  unbinding.value = true
  try {
    await bindingApi.unbind()
    toast.success('已解绑 QQ')
    code.value = null
    unbindOpen.value = false
    await load()
  } catch (error) {
    toast.error(toUserMessage(error))
  } finally {
    unbinding.value = false
  }
}

function copyCode(): void {
  if (!code.value) return
  navigator.clipboard?.writeText(code.value.code).then(
    () => toast.success('绑定码已复制'),
    () => toast.error('复制失败，请手动复制'),
  )
}

onMounted(load)
onBeforeUnmount(stopTimer)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">我的 · 账号</p>
      <h1>我的</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" to="/student">回到学习台</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
  <p v-if="loading" class="loading-line">正在读取账号…</p>

  <div v-else class="columns">
    <section class="card stack">
      <header class="card__head"><h2>账号信息</h2></header>
      <div class="row" style="gap: 12px">
        <span class="avatar" style="width: 42px; height: 42px; font-size: 15px">
          {{ auth.displayName.slice(0, 1) }}
        </span>
        <div>
          <p class="strong">{{ auth.displayName }}</p>
          <p class="small tertiary">{{ student?.class_name ?? '我的班级' }} · 学号 {{ student?.student_no ?? '—' }}</p>
        </div>
      </div>
      <div class="kv">
        <span>班级编号：<b class="mono">{{ student?.class_code ?? '—' }}</b></span>
        <span>等级：<b>Lv.{{ student?.level ?? 1 }}</b></span>
        <span>累计经验：<b>{{ student?.xp_total ?? 0 }} XP</b></span>
      </div>
      <RouterLink class="btn btn--sm" to="/student/growth" style="align-self: flex-start">
        查看成长记录
      </RouterLink>
    </section>

    <section class="card stack">
      <header class="card__head">
        <h2>QQ 绑定</h2>
        <BaseBadge :tone="student?.qq_bound ? 'lime' : 'plain'">
          {{ student?.qq_bound ? '已绑定' : '未绑定' }}
        </BaseBadge>
      </header>

      <template v-if="student?.qq_bound">
        <p class="notice notice--lime">QQ 已绑定，可在班级群里私聊机器人查询作业与成绩。</p>
        <BaseButton variant="danger" :loading="unbinding" @click="unbind">解绑 QQ</BaseButton>
      </template>

      <template v-else>
        <p class="notice">
          生成 8 位绑定码后，在班级 QQ 群里私聊机器人发送该码即可完成绑定。绑定码一次性有效，重复生成旧码失效。
        </p>
        <div class="row row--wrap">
          <BaseButton variant="primary" :loading="generating" @click="generate">生成绑定码</BaseButton>
          <span v-if="code" class="small tertiary" aria-live="polite">
            {{ left > 0 ? `${Math.floor(left / 60)} 分 ${left % 60} 秒后失效` : '已过期，请重新生成' }}
          </span>
        </div>
        <div v-if="code" class="copy-code">
          <code style="user-select: all">{{ code.code }}</code>
          <button class="btn btn--sm" type="button" @click="copyCode">复制</button>
        </div>
      </template>
    </section>
  </div>

  <ConfirmDialog
    :open="unbindOpen"
    title="解绑 QQ"
    message="解绑后 QQ 将无法查询你的作业与成绩，可随时重新绑定。"
    confirm-label="解绑"
    tone="danger"
    :loading="unbinding"
    @confirm="confirmUnbind"
    @cancel="unbindOpen = false"
  />
</template>
