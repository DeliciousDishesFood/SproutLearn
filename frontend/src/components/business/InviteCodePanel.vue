<!-- 邀请码面板：等宽大字、复制、危险色描边重置（二次确认）+ 旧码失效提示。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Copy, RotateCcw, ShieldAlert } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppModal from '@/components/base/AppModal.vue'
import { classesApi } from '@/api/classes'
import { toUserMessage } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { copyText } from '@/utils/format'

const props = defineProps<{
  classId: number
  inviteCode: string | null
  classCode: string
}>()

const emit = defineEmits<{
  (event: 'updated', inviteCode: string): void
}>()

const ui = useUiStore()
const currentCode = ref(props.inviteCode)
const copiedField = ref<'invite' | 'class' | ''>('')
const confirmOpen = ref(false)
const resetting = ref(false)
const error = ref('')

watch(
  () => props.inviteCode,
  (value) => {
    currentCode.value = value
  },
)

const displayCode = computed(() => currentCode.value || '未生成')

async function copy(value: string, field: 'invite' | 'class'): Promise<void> {
  if (!value) return
  const ok = await copyText(value)
  if (ok) {
    copiedField.value = field
    ui.success(field === 'invite' ? '邀请码已复制' : '班级编号已复制')
    window.setTimeout(() => {
      if (copiedField.value === field) copiedField.value = ''
    }, 1800)
  } else {
    ui.error('复制失败，请手动选择文本')
  }
}

function askReset(): void {
  error.value = ''
  confirmOpen.value = true
}

async function doReset(): Promise<void> {
  if (resetting.value) return
  resetting.value = true
  error.value = ''
  try {
    const result = await classesApi.resetInviteCode(props.classId)
    currentCode.value = result.invite_code
    emit('updated', result.invite_code)
    confirmOpen.value = false
    ui.success('邀请码已重置，旧码立即失效')
  } catch (err) {
    error.value = toUserMessage(err)
  } finally {
    resetting.value = false
  }
}
</script>

<template>
  <section class="invite-panel" aria-labelledby="invite-panel-title">
    <header class="invite-panel__head">
      <div>
        <p class="eyebrow">INVITE</p>
        <h2 id="invite-panel-title" class="invite-panel__title">邀请学生加入</h2>
      </div>
      <span class="invite-panel__seal" aria-hidden="true">入班</span>
    </header>

    <p class="invite-panel__label">当前邀请码</p>
    <div class="invite-panel__code-row">
      <strong class="invite-panel__code mono">{{ displayCode }}</strong>
      <button
        class="invite-panel__copy"
        type="button"
        :disabled="!currentCode"
        aria-label="复制邀请码"
        title="复制邀请码"
        @click="copy(currentCode || '', 'invite')"
      >
        <Check v-if="copiedField === 'invite'" :size="17" :stroke-width="2" />
        <Copy v-else :size="17" :stroke-width="1.8" />
      </button>
    </div>
    <p class="invite-panel__hint">学生打开「加入班级」，输入邀请码、学号、姓名与密码即可入班。</p>

    <div class="invite-panel__class-code">
      <span>
        <span class="invite-panel__class-label">班级编号</span>
        <span class="mono">{{ classCode }}</span>
      </span>
      <button type="button" class="invite-panel__mini-copy" aria-label="复制班级编号" @click="copy(classCode, 'class')">
        <Check v-if="copiedField === 'class'" :size="14" :stroke-width="2" />
        <Copy v-else :size="14" :stroke-width="1.8" />
      </button>
    </div>
    <p class="invite-panel__hint">班级编号永久不变，学生登录时使用。</p>

    <div class="invite-panel__actions">
      <AppButton variant="danger-outline" size="sm" @click="askReset">
        <RotateCcw :size="15" :stroke-width="1.8" />
        重置邀请码
      </AppButton>
    </div>

    <p class="invite-panel__warning">
      <ShieldAlert :size="14" :stroke-width="1.8" aria-hidden="true" />
      重置后旧邀请码立即失效，已加入的学生不受影响。
    </p>

    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <AppModal
      v-model="confirmOpen"
      title="重置邀请码？"
      description="系统会立即作废当前邀请码并生成新码，已经加入班级的学生不会受到影响。"
      confirm-text="重置邀请码"
      confirm-variant="danger"
      :confirm-loading="resetting"
      width="440px"
    >
      <p class="invite-panel__modal-note">
        请确认你已经把新码发给学生，或准备在课堂上重新公布。
      </p>
      <template #footer>
        <AppButton variant="ghost" :disabled="resetting" @click="confirmOpen = false">取消</AppButton>
        <AppButton variant="danger" :loading="resetting" @click="doReset">重置邀请码</AppButton>
      </template>
    </AppModal>
  </section>
</template>

<style scoped>
.invite-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    linear-gradient(160deg, color-mix(in srgb, var(--color-accent) 7%, transparent) 0, transparent 42%),
    var(--color-surface);
  box-shadow: var(--shadow-1);
}

.invite-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
}

.invite-panel__title {
  font-size: var(--fs-lg);
}

.invite-panel__seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid color-mix(in srgb, var(--color-accent) 55%, transparent);
  border-radius: 999px;
  color: color-mix(in srgb, var(--color-accent) 84%, var(--color-text));
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  transform: rotate(-6deg);
}

.invite-panel__label {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  letter-spacing: 0.08em;
}

.invite-panel__code-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.invite-panel__code {
  font-size: 30px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: 0.18em;
  color: var(--color-text);
}

.invite-panel__copy,
.invite-panel__mini-copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
  transition: color 160ms ease-out, border-color 160ms ease-out, background-color 160ms ease-out;
}

.invite-panel__copy {
  width: 34px;
  height: 34px;
}

.invite-panel__mini-copy {
  width: 26px;
  height: 26px;
}

.invite-panel__copy:hover,
.invite-panel__mini-copy:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.invite-panel__hint {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.65;
}

.invite-panel__class-code {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
}

.invite-panel__class-code > span {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.invite-panel__class-label {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.invite-panel__class-code .mono {
  letter-spacing: 0.08em;
  font-weight: 600;
}

.invite-panel__actions {
  margin-top: var(--sp-1);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.invite-panel__warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: var(--color-warning);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.invite-panel__modal-note {
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-warning) 20%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 8%, transparent);
  color: var(--color-text);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
</style>
