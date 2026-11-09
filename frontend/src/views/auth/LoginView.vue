<!-- 登录页：左侧 420px 品牌区 + 右侧表单卡片，教师/学生共用入口。 -->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowRight,
  Check,
  GraduationCap,
  Sprout,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppInput from '@/components/base/AppInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { isApiError } from '@/api/client'
import { ERROR_CODE, ERROR_MESSAGES } from '@/utils/constants'

type LoginRole = 'teacher' | 'student'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const role = ref<LoginRole>('teacher')
const submitting = ref(false)
const generalError = ref('')

const form = reactive({
  account: '',
  classCode: '',
  studentNo: '',
  password: '',
})

const errors = reactive<Record<string, string>>({
  account: '',
  classCode: '',
  studentNo: '',
  password: '',
})

const headline = computed(() =>
  role.value === 'teacher' ? '回到你的课堂' : '继续今天的学习',
)
const subtitle = computed(() =>
  role.value === 'teacher'
    ? '登录教师工作台，管理班级与课程知识库。'
    : '使用班级编号与学号登录，查看老师共享的课程资料。',
)

watch(
  role,
  () => {
    generalError.value = ''
    errors.account = ''
    errors.classCode = ''
    errors.studentNo = ''
    errors.password = ''
    if (route.query.expired === '1') {
      generalError.value = '登录已过期，请重新输入账号信息。'
    }
  },
  { immediate: true },
)

function clearFieldError(field: keyof typeof errors): void {
  errors[field] = ''
  generalError.value = ''
}

function validate(): boolean {
  errors.account = ''
  errors.classCode = ''
  errors.studentNo = ''
  errors.password = ''
  generalError.value = ''

  if (!form.password) {
    errors.password = '请输入密码'
  } else if (form.password.length < 8 || form.password.length > 32) {
    errors.password = '密码长度需为 8–32 位'
  }

  if (role.value === 'teacher') {
    const account = form.account.trim()
    if (!account) {
      errors.account = '请输入邮箱或手机号'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account) && !/^\d{11}$/.test(account)) {
      errors.account = '请输入有效邮箱或 11 位手机号'
    }
  } else {
    const classCode = form.classCode.trim()
    if (!classCode) {
      errors.classCode = '请输入班级编号'
    } else if (!/^[A-Za-z0-9]{6}$/.test(classCode)) {
      errors.classCode = '班级编号为 6 位字母或数字'
    }
    const studentNo = form.studentNo.trim()
    if (!studentNo) {
      errors.studentNo = '请输入学号'
    } else if (!/^[A-Za-z0-9]{4,32}$/.test(studentNo)) {
      errors.studentNo = '学号为 4–32 位字母或数字'
    }
  }

  return !errors.account && !errors.classCode && !errors.studentNo && !errors.password
}

function resolveDestination(): string {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  const allowedPrefix = role.value === 'teacher' ? '/teacher' : '/student'
  if (target.startsWith(allowedPrefix)) return target
  return allowedPrefix === '/teacher' ? '/teacher/dashboard' : '/student/home'
}

async function submit(): Promise<void> {
  if (submitting.value || !validate()) return
  submitting.value = true
  generalError.value = ''
  try {
    if (role.value === 'teacher') {
      await auth.loginTeacher(form.account.trim(), form.password)
    } else {
      await auth.loginStudent(form.classCode.trim().toUpperCase(), form.studentNo.trim(), form.password)
    }
    ui.success(`欢迎回来，${auth.displayName || '同学'}`)
    await router.replace(resolveDestination())
  } catch (err) {
    if (isApiError(err)) {
      if (err.code === ERROR_CODE.BAD_CREDENTIALS) {
        generalError.value = '账号或密码错误。请检查后重试，教师与学生请选择对应身份登录。'
      } else if (err.code === ERROR_CODE.VALIDATION) {
        generalError.value = '登录信息格式不正确，请按提示检查后重试。'
      } else {
        generalError.value = ERROR_MESSAGES[err.code] || err.message || '登录未完成，请稍后重试'
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
          <p class="auth-kicker">CLASSROOM · KNOWLEDGE</p>
          <h1 class="auth-headline">让每一次提问，<br />都在知识里<em>发芽</em>。</h1>
          <p class="auth-lead">
            青芽把课堂资料沉淀为可检索的知识切片。老师安心整理，
            学生随时回看，学习在课堂之外继续生长。
          </p>

          <ul class="auth-points">
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              教师创建班级，一枚邀请码邀请全班入座
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              学生绑定 QQ，在班级群即可找到课程知识
            </li>
            <li class="auth-point">
              <Check :size="15" :stroke-width="2.2" aria-hidden="true" />
              文档解析成切片，每一页内容都有迹可循
            </li>
          </ul>
        </div>

        <footer class="auth-story-foot">
          <span>M1 · 班级知识库</span>
          <span>SPROUTLEARN</span>
        </footer>
      </div>
    </aside>

    <section class="auth-form-area">
      <div class="auth-card auth-card--surface">
        <div class="auth-mobile-brand">
          <Sprout :size="20" :stroke-width="2" aria-hidden="true" />
          青芽 SproutLearn
        </div>

        <header class="auth-card-head">
          <p class="eyebrow">WELCOME BACK</p>
          <h2 class="auth-title">{{ headline }}</h2>
          <p class="auth-subtitle">{{ subtitle }}</p>
        </header>

        <div class="auth-switch" role="tablist" aria-label="登录身份">
          <button
            class="auth-switch__btn"
            :class="{ 'auth-switch__btn--active': role === 'teacher' }"
            type="button"
            role="tab"
            :aria-selected="role === 'teacher'"
            @click="role = 'teacher'"
          >
            <GraduationCap :size="15" :stroke-width="1.9" aria-hidden="true" />
            教师登录
          </button>
          <button
            class="auth-switch__btn"
            :class="{ 'auth-switch__btn--active': role === 'student' }"
            type="button"
            role="tab"
            :aria-selected="role === 'student'"
            @click="role = 'student'"
          >
            <UsersRound :size="15" :stroke-width="1.9" aria-hidden="true" />
            学生登录
          </button>
        </div>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <template v-if="role === 'teacher'">
            <AppInput
              v-model="form.account"
              label="账号"
              placeholder="teacher@school.edu.cn"
              autocomplete="username"
              :maxlength="64"
              :error="errors.account"
              @update:model-value="clearFieldError('account')"
            />
          </template>

          <template v-else>
            <AppInput
              v-model="form.classCode"
              label="班级编号"
              placeholder="例如 C26A79"
              autocomplete="username"
              :maxlength="6"
              :error="errors.classCode"
              @update:model-value="clearFieldError('classCode')"
            />
            <AppInput
              v-model="form.studentNo"
              label="学号"
              placeholder="例如 20260101"
              :maxlength="32"
              :error="errors.studentNo"
              @update:model-value="clearFieldError('studentNo')"
            />
          </template>

          <AppInput
            v-model="form.password"
            label="密码"
            type="password"
            :placeholder="role === 'teacher' ? '输入账号密码' : '输入加入班级时设置的密码'"
            autocomplete="current-password"
            :maxlength="32"
            :error="errors.password"
            @update:model-value="clearFieldError('password')"
          />

          <p v-if="generalError" class="auth-error" role="alert">
            <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ generalError }}</span>
          </p>

          <div class="auth-actions">
            <AppButton type="submit" variant="primary" size="md" block :loading="submitting">
              登录
              <ArrowRight v-if="!submitting" :size="16" :stroke-width="1.9" aria-hidden="true" />
            </AppButton>
          </div>
        </form>

        <div class="auth-divider"><span>第一次来到这里</span></div>

        <div class="auth-links">
          <router-link to="/register" class="link">注册教师账号</router-link>
          <span class="auth-link-row">
            学生？
            <router-link to="/join" class="link">使用邀请码加入班级</router-link>
          </span>
        </div>

        <p class="auth-footnote">
          教师账号使用邮箱或手机号登录；学生使用班级编号与学号登录。忘记密码请联系所在班级的教师。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
@media (min-width: 900px) {
  .auth-story {
    min-height: 100vh;
  }
}
</style>
