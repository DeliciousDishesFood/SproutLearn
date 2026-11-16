<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import PublicLayout from '@/layouts/PublicLayout.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth'
import { workbenchApi } from '@/api/workbench'
import { isApiError, toUserMessage } from '@/api/client'
import type { LoginPayload } from '@/api/contract'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const mode = ref<'teacher' | 'student'>('teacher')
const teacherForm = reactive({ account: '', password: '' })
const studentForm = reactive({ class_code: '', student_no: '', password: '' })
const loading = ref(false)
const errorText = ref('')
const quote = ref({ text: '把复杂讲简单，把简单讲深刻。', from: '青芽教学手记' })

function homePath(): string {
  return auth.isTeacher ? '/teacher' : '/student'
}

async function submit(): Promise<void> {
  errorText.value = ''
  if (mode.value === 'teacher') {
    if (!teacherForm.account.trim() || !teacherForm.password) {
      errorText.value = '请填写账号和密码'
      return
    }
  } else if (
    !studentForm.class_code.trim() ||
    !studentForm.student_no.trim() ||
    !studentForm.password
  ) {
    errorText.value = '请填写班级编号、学号和密码'
    return
  }

  loading.value = true
  try {
    const payload: LoginPayload =
      mode.value === 'teacher'
        ? {
            role: 'teacher',
            account: teacherForm.account.trim(),
            password: teacherForm.password,
          }
        : {
            role: 'student',
            class_code: studentForm.class_code.trim(),
            student_no: studentForm.student_no.trim(),
            password: studentForm.password,
          }
    await auth.login(payload)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const expected = auth.isTeacher ? '/teacher' : '/student'
    const target = redirect.startsWith(expected) ? redirect : homePath()
    await router.replace(target)
  } catch (error) {
    if (isApiError(error) && error.code === 40103) {
      errorText.value = '账号或密码错误'
    } else {
      errorText.value = toUserMessage(error)
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (auth.isLoggedIn) {
    await router.replace(homePath())
    return
  }
  try {
    const result = await workbenchApi.quote()
    quote.value = { text: result.text, from: result.from }
  } catch {
    // 金句失败时保留本地兜底文案
  }
})
</script>

<template>
  <PublicLayout>
    <main class="login">
      <section class="login-story">
        <RouterLink class="brand" to="/">
          <span class="brand__mark" aria-hidden="true"><Sprout :size="19" /></span>
          <span class="brand__text">青芽 <em>SproutLearn</em></span>
        </RouterLink>

        <div class="story">
          <p class="eyebrow">SPROUTLEARN</p>
          <h1>让每一次练习，<br />都有回响。</h1>
          <p class="story__lede">从资料到组卷，从作答到复核，把教学闭环留在同一个地方。</p>
          <ul class="story__list">
            <li><i></i>资料有出处，讲评有依据</li>
            <li><i></i>班级练习与批改形成闭环</li>
            <li><i></i>成长反馈看得见、跟得上</li>
          </ul>
        </div>

        <p class="story__quote">“{{ quote.text }}”<span>{{ quote.from }}</span></p>
      </section>

      <section class="login-form-wrap">
        <form class="login-card" novalidate @submit.prevent="submit">
          <header class="login-card__head">
            <h2>欢迎回来</h2>
            <p>登录后继续你的教学与学习。</p>
          </header>

          <div class="segmented" role="tablist" aria-label="身份">
            <button
              class="segmented__item"
              :class="{ 'is-active': mode === 'teacher' }"
              type="button"
              role="tab"
              :aria-selected="mode === 'teacher'"
              @click="mode = 'teacher'; errorText = ''"
            >
              教师
            </button>
            <button
              class="segmented__item"
              :class="{ 'is-active': mode === 'student' }"
              type="button"
              role="tab"
              :aria-selected="mode === 'student'"
              @click="mode = 'student'; errorText = ''"
            >
              学生
            </button>
          </div>

          <template v-if="mode === 'teacher'">
            <BaseField label="账号">
              <input
                v-model="teacherForm.account"
                type="text"
                autocomplete="username"
                placeholder="教师账号"
              />
            </BaseField>
            <BaseField label="密码">
              <input
                v-model="teacherForm.password"
                type="password"
                autocomplete="current-password"
                placeholder="登录密码"
              />
            </BaseField>
          </template>

          <template v-else>
            <BaseField label="班级编号">
              <input
                v-model="studentForm.class_code"
                type="text"
                autocomplete="off"
                placeholder="例如 C2026001"
              />
            </BaseField>
            <BaseField label="学号">
              <input
                v-model="studentForm.student_no"
                type="text"
                autocomplete="username"
                placeholder="班级学号"
              />
            </BaseField>
            <BaseField label="密码">
              <input
                v-model="studentForm.password"
                type="password"
                autocomplete="current-password"
                placeholder="登录密码"
              />
            </BaseField>
          </template>

          <p v-if="errorText" class="form-error" role="alert">{{ errorText }}</p>

          <BaseButton variant="primary" type="submit" :loading="loading">进入青芽</BaseButton>

          <div class="login-links">
            <RouterLink class="login-link" to="/join">学生加入班级</RouterLink>
            <RouterLink class="login-link" to="/register/teacher">教师注册</RouterLink>
          </div>
          <p class="login-foot">账号由班级老师统一开通，忘记密码请联系老师。</p>
        </form>
      </section>
    </main>
  </PublicLayout>
</template>
