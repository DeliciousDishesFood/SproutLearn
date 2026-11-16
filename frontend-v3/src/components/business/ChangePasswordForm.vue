<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import BaseField from '@/components/ui/BaseField.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { accountApi } from '@/api/account'
import { toUserMessage } from '@/api/client'
import { PASSWORD_RULE_TEXT, validatePassword } from '@/utils/password'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const props = withDefaults(defineProps<{ forced?: boolean }>(), { forced: false })

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const toast = useToast()

const form = reactive({ current: '', next: '', confirm: '' })
const shown = reactive({ current: false, next: false, confirm: false })
const errors = reactive({ current: '', next: '', confirm: '' })
const errorText = ref('')
const loading = ref(false)

function resetErrors(): void {
  errors.current = ''
  errors.next = ''
  errors.confirm = ''
  errorText.value = ''
}

function validate(): boolean {
  resetErrors()
  if (!form.current) errors.current = '请输入当前密码'
  if (!form.next) errors.next = '请输入新密码'
  else errors.next = validatePassword(form.next) ?? ''
  if (!errors.next && form.next === form.current) errors.next = '新密码不能与当前密码相同'
  if (!form.confirm) errors.confirm = '请再次输入新密码'
  else if (form.confirm !== form.next) errors.confirm = '两次输入的新密码不一致'
  return !errors.current && !errors.next && !errors.confirm
}

async function submit(): Promise<void> {
  if (loading.value) return
  if (!validate()) return
  loading.value = true
  try {
    await accountApi.changePassword({
      current_password: form.current,
      new_password: form.next,
    })
    toast.success('密码已更新，请使用新密码重新登录')
    auth.clear()
    ui.setCurrentClassId(null)
    await router.replace('/login')
  } catch (error) {
    // 失败保留已填内容，只展示错误。
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="pw-form" novalidate @submit.prevent="submit">
    <BaseField label="当前密码" :error="errors.current" required>
      <span class="pw">
        <input
          v-model="form.current"
          :type="shown.current ? 'text' : 'password'"
          autocomplete="current-password"
          placeholder="临时密码也填写在这里"
          @input="errors.current = ''; errorText = ''"
        />
        <button
          class="pw__toggle"
          type="button"
          :aria-label="shown.current ? '隐藏当前密码' : '显示当前密码'"
          :aria-pressed="shown.current"
          @click="shown.current = !shown.current"
        >
          <EyeOff v-if="shown.current" :size="15" aria-hidden="true" />
          <Eye v-else :size="15" aria-hidden="true" />
        </button>
      </span>
    </BaseField>

    <BaseField label="新密码" :hint="PASSWORD_RULE_TEXT" :error="errors.next" required>
      <span class="pw">
        <input
          v-model="form.next"
          :type="shown.next ? 'text' : 'password'"
          autocomplete="new-password"
          :placeholder="PASSWORD_RULE_TEXT"
          @input="errors.next = ''; errorText = ''"
        />
        <button
          class="pw__toggle"
          type="button"
          :aria-label="shown.next ? '隐藏新密码' : '显示新密码'"
          :aria-pressed="shown.next"
          @click="shown.next = !shown.next"
        >
          <EyeOff v-if="shown.next" :size="15" aria-hidden="true" />
          <Eye v-else :size="15" aria-hidden="true" />
        </button>
      </span>
    </BaseField>

    <BaseField label="确认新密码" :error="errors.confirm" required>
      <span class="pw">
        <input
          v-model="form.confirm"
          :type="shown.confirm ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="再次输入新密码"
          @input="errors.confirm = ''; errorText = ''"
        />
        <button
          class="pw__toggle"
          type="button"
          :aria-label="shown.confirm ? '隐藏确认密码' : '显示确认密码'"
          :aria-pressed="shown.confirm"
          @click="shown.confirm = !shown.confirm"
        >
          <EyeOff v-if="shown.confirm" :size="15" aria-hidden="true" />
          <Eye v-else :size="15" aria-hidden="true" />
        </button>
      </span>
    </BaseField>

    <p v-if="errorText" class="form-error" role="alert">{{ errorText }}</p>

    <BaseButton variant="primary" type="submit" :loading="loading">
      {{ forced ? '设置新密码并重新登录' : '更新密码' }}
    </BaseButton>
  </form>
</template>

<style scoped>
.pw-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 420px;
}

.pw {
  position: relative;
  display: block;
}

.pw input {
  width: 100%;
  padding-right: 44px;
}

.pw__toggle {
  position: absolute;
  top: 50%;
  right: 3px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
}

.pw__toggle:hover {
  background: var(--surface-alt);
  color: var(--text);
}
</style>
