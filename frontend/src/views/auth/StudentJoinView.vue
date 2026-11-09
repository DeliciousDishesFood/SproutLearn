<!-- 学生加入班级：邀请码 + 学号 + 姓名 + 密码，成功即签发会话并进入学生端。 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, ArrowRight, Check, Sprout, Ticket } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppInput from '@/components/base/AppInput.vue'
import { classesApi } from '@/api/classes'
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
  inviteCode: '',
  studentNo: '',
  name: '',
  password: '',
  confirmPassword: '',
})
const errors = reactive<Record<string, string>>({
  inviteCode: '',
  studentNo: '',
  name: '',
  password: '',
  confirmPassword: '',
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

  const inviteCode = form.inviteCode.trim()
  const studentNo = form.studentNo.trim()
  const name = form.name.trim()

  if (!inviteCode) {
    errors.inviteCode = '请输入老师提供的邀请码'
  } else if (!/^[A-Za-z0-9]{6}$/.test(inviteCode)) {
    errors.inviteCode = '邀请码为 6 位大写字母或数字'
  }

  if (!studentNo) {
    errors.studentNo = '请输入学号'
  } else if (!/^[A-Za-z0-9]{4,32}$/.test(studentNo)) {
    errors.studentNo = '学号为 4–32 位字母或数字'
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

  return !Object.values(errors).some(Boolean)
}

async function submit(): Promise<void> {
  if (submitting.value || !validate()) return
  submitting.value = true
  generalError.value = ''
  try {
    const result = await classesApi.join({
      invite_code: form.inviteCode.trim().toUpperCase(),
      student_no: form.studentNo.trim(),
      name: form.name.trim(),
      password: form.password,
    })
    auth.setSession({ token: result.token, user: result.user })
    ui.success(`已加入「${result.class.class_name}」，欢迎你`)
    await router.replace('/student/home')
  } catch (err) {
    if (isApiError(err)) {
      if (err.code === ERROR_CODE.INVITE_INVALID) {
        errors.inviteCode = '邀请码无效或已失效，请向老师确认后重新输入'
      } else if (err.code === ERROR_CODE.STUDENT_NO_EXISTS) {
        errors.studentNo = '该学号已在本班使用，请更换学号或直接登录'
      } else if (err.code === ERROR_CODE.RATE_LIMITED) {
        generalError.value = '加入请求过于频繁，请稍后再试'
      } else if (err.code === ERROR_CODE.VALIDATION) {
        generalError.value = '填写内容未通过校验，请检查邀请码、学号、姓名与密码格式'
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
          <p class="auth-kicker">JOIN · YOUR CLASS</p>
          <h1 class="auth-headline">一枚邀请码，<br />把你<em>种进</em>课堂。</h1>
          <p class="auth-lead">
            加入后，可以在班级知识库里回看老师上传的每一份资料。
            知识被切成细细的片段，总有一片恰好回答你此刻的问题。
          </p>

          <ul class="auth-points">
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              邀请码由任课老师提供，6 位大写字母或数字
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              学号在班内唯一，用于后续登录与学习记录
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              加入成功即进入学生空间，无需再次登录
            </li>
          </ul>
        </div>

        <footer class="auth-story-foot">
          <span>M1 · 学生空间</span>
          <span>SPROUTLEARN</span>
        </footer>
      </div>
    </aside>

    <section class="auth-form-area">
      <div class="auth-card auth-card--surface join-card">
        <div class="auth-mobile-brand">
          <Sprout :size="20" :stroke-width="2" aria-hidden="true" />
          青芽 SproutLearn
        </div>

        <header class="auth-card-head">
          <p class="eyebrow">JOIN A CLASS</p>
          <h2 class="auth-title">加入你的班级</h2>
          <p class="auth-subtitle">向老师索取邀请码，填写后会直接进入学生空间。</p>
        </header>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <AppInput
            v-model="form.inviteCode"
            label="邀请码"
            placeholder="6 位大写字母或数字"
            autocomplete="one-time-code"
            :maxlength="6"
            :error="errors.inviteCode"
            @update:model-value="clearFieldError('inviteCode')"
          />

          <AppInput
            v-model="form.studentNo"
            label="学号"
            placeholder="例如 20260101"
            autocomplete="username"
            :maxlength="32"
            :error="errors.studentNo"
            hint="4–32 位字母或数字，在班级内不可重复。"
            @update:model-value="clearFieldError('studentNo')"
          />

          <AppInput
            v-model="form.name"
            label="姓名"
            placeholder="填写真实姓名"
            autocomplete="name"
            :maxlength="50"
            :error="errors.name"
            @update:model-value="clearFieldError('name')"
          />

          <AppInput
            v-model="form.password"
            label="登录密码"
            type="password"
            placeholder="设置 8–32 位密码"
            autocomplete="new-password"
            :maxlength="32"
            :error="errors.password"
            hint="需同时包含字母与数字，之后登录学生端时使用。"
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

          <p v-if="generalError" class="auth-error" role="alert">
            <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ generalError }}</span>
          </p>

          <div class="auth-actions">
            <AppButton type="submit" variant="primary" size="md" block :loading="submitting">
              <Ticket v-if="!submitting" :size="16" :stroke-width="1.9" aria-hidden="true" />
              加入班级
              <ArrowRight v-if="!submitting" :size="16" :stroke-width="1.9" aria-hidden="true" />
            </AppButton>
          </div>
        </form>

        <p class="join-note">
          已经加入过班级？
          <router-link to="/login" class="link">直接登录</router-link>
        </p>

        <p class="auth-footnote">
          邀请码不区分大小写，我们会自动转成大写。若提示已失效，请让老师重置邀请码后再试。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.join-note {
  margin-top: var(--sp-5);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.join-card {
  max-width: 436px;
}
</style>
