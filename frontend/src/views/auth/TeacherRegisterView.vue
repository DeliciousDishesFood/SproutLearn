<!-- 教师注册：账号/姓名/密码 + 选填邮箱手机，成功后直接进入教学总览。 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, ArrowRight, Check, Sprout, UserPlus } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppInput from '@/components/base/AppInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { isApiError } from '@/api/client'
import { ERROR_CODE } from '@/utils/constants'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const submitting = ref(false)
const generalError = ref('')
const form = reactive({
  account: '',
  name: '',
  password: '',
  confirmPassword: '',
  email: '',
  phone: '',
})
const errors = reactive<Record<string, string>>({
  account: '',
  name: '',
  password: '',
  confirmPassword: '',
  email: '',
  phone: '',
})

function clearFieldError(field: string): void {
  errors[field] = ''
  generalError.value = ''
}

function validate(): boolean {
  Object.keys(errors).forEach((key) => {
    errors[key] = ''
  })
  generalError.value = ''

  const account = form.account.trim()
  const name = form.name.trim()
  const email = form.email.trim()
  const phone = form.phone.trim()

  if (!account) {
    errors.account = '请输入登录账号'
  } else if (account.length < 4 || account.length > 64) {
    errors.account = '账号长度需为 4–64 个字符'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account) && !/^\d{11}$/.test(account)) {
    errors.account = '账号需为有效邮箱或 11 位手机号'
  }

  if (!name) {
    errors.name = '请输入姓名'
  } else if (name.length > 50) {
    errors.name = '姓名不能超过 50 个字符'
  }

  if (!form.password) {
    errors.password = '请设置密码'
  } else if (!/^(?=.*[A-Za-z])(?=.*\d).{8,32}$/.test(form.password)) {
    errors.password = '密码需为 8–32 位，且同时包含字母与数字'
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码'
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致'
  }

  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = '请输入有效的邮箱地址'
  }

  if (phone && !/^\d{11}$/.test(phone)) {
    errors.phone = '请输入 11 位手机号'
  }

  return !Object.values(errors).some(Boolean)
}

async function submit(): Promise<void> {
  if (submitting.value || !validate()) return
  submitting.value = true
  generalError.value = ''
  try {
    await auth.registerTeacher({
      account: form.account.trim(),
      name: form.name.trim(),
      password: form.password,
      email: form.email.trim() || undefined,
      phone: form.phone.trim() || undefined,
    })
    ui.success('教师账号已创建，欢迎来到青芽')
    await router.replace('/teacher/dashboard')
  } catch (err) {
    if (isApiError(err)) {
      if (err.code === ERROR_CODE.ACCOUNT_EXISTS) {
        errors.account = '该账号已注册，请直接登录'
      } else if (err.code === ERROR_CODE.RATE_LIMITED) {
        generalError.value = '注册请求过于频繁，请稍后再试'
      } else if (err.code === ERROR_CODE.VALIDATION) {
        generalError.value = '填写内容未通过校验，请检查账号、姓名与密码格式'
      } else {
        generalError.value = err.friendlyMessage
      }
    } else {
      generalError.value = '网络连接失败，请检查网络后重试'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <aside class="auth-story">
      <div class="auth-story__inner">
        <router-link to="/login" class="auth-brand">
          <span class="auth-brand__mark">
            <Sprout :size="21" :stroke-width="1.9" aria-hidden="true" />
          </span>
          <span class="auth-brand__text">
            <strong>青芽</strong>
            <span>SPROUTLEARN</span>
          </span>
        </router-link>

        <div class="auth-story-copy">
          <p class="auth-kicker">TEACHER · WORKSPACE</p>
          <h1 class="auth-headline">一间教室，<br />从一枚<em>账号</em>开始。</h1>
          <p class="auth-lead">
            创建班级、生成邀请码，把每一次课程资料上传都沉淀为全班共享的知识。
            青芽负责整理脉络，你负责课堂里的光。
          </p>

          <ul class="auth-points">
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              班级编号永久不变，学生登录不再丢失入口
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              邀请码随时重置，旧码即时失效
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              文档自动解析为切片，课堂资料一目了然
            </li>
          </ul>
        </div>

        <footer class="auth-story-foot">
          <span>M1 · 教师工作台</span>
          <span>SPROUTLEARN</span>
        </footer>
      </div>
    </aside>

    <section class="auth-form-area">
      <div class="auth-card auth-card--surface register-card">
        <div class="auth-mobile-brand">
          <Sprout :size="20" :stroke-width="2" aria-hidden="true" />
          青芽 SproutLearn
        </div>

        <header class="auth-card-head">
          <p class="eyebrow">CREATE ACCOUNT</p>
          <h2 class="auth-title">创建教师账号</h2>
          <p class="auth-subtitle">注册完成后即进入工作台，可以创建班级并邀请学生。</p>
        </header>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <AppInput
            v-model="form.account"
            label="登录账号"
            placeholder="邮箱或 11 位手机号"
            autocomplete="username"
            :maxlength="64"
            :error="errors.account"
            hint="账号将作为登录凭证，长度 4–64 个字符。"
            @update:model-value="clearFieldError('account')"
          />

          <AppInput
            v-model="form.name"
            label="姓名"
            placeholder="学生和同事看到的名字"
            autocomplete="name"
            :maxlength="50"
            :error="errors.name"
            @update:model-value="clearFieldError('name')"
          />

          <AppInput
            v-model="form.password"
            label="密码"
            type="password"
            placeholder="设置 8–32 位密码"
            autocomplete="new-password"
            :maxlength="32"
            :error="errors.password"
            hint="需同时包含字母与数字。"
            @update:model-value="clearFieldError('password')"
          />

          <AppInput
            v-model="form.confirmPassword"
            label="确认密码"
            type="password"
            placeholder="再次输入密码"
            autocomplete="new-password"
            :maxlength="32"
            :error="errors.confirmPassword"
            @update:model-value="clearFieldError('confirmPassword')"
          />

          <div class="form-grid">
            <AppInput
              v-model="form.email"
              label="邮箱（选填）"
              type="email"
              placeholder="用于接收课程通知"
              autocomplete="email"
              :maxlength="64"
              :error="errors.email"
              @update:model-value="clearFieldError('email')"
            />
            <AppInput
              v-model="form.phone"
              label="手机号（选填）"
              type="tel"
              placeholder="11 位手机号"
              autocomplete="tel"
              :maxlength="11"
              :error="errors.phone"
              @update:model-value="clearFieldError('phone')"
            />
          </div>

          <p v-if="generalError" class="auth-error" role="alert">
            <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ generalError }}</span>
          </p>

          <div class="auth-actions">
            <AppButton type="submit" variant="primary" size="md" block :loading="submitting">
              <UserPlus v-if="!submitting" :size="16" :stroke-width="1.9" aria-hidden="true" />
              创建账号并进入
              <ArrowRight v-if="!submitting" :size="16" :stroke-width="1.9" aria-hidden="true" />
            </AppButton>
          </div>
        </form>

        <p class="register-note">
          已有账号？
          <router-link to="/login" class="link">返回登录</router-link>
        </p>

        <p class="auth-footnote">
          账号仅用于教师本人登录教学空间。请勿代学生注册，学生需通过班级邀请码加入。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.register-card {
  max-width: 456px;
}

.register-note {
  margin-top: var(--sp-5);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.auth-actions :deep(.app-button) {
  letter-spacing: 0.04em;
}
</style>
