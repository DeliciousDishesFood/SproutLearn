<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import PublicLayout from '@/layouts/PublicLayout.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth'
import { toUserMessage } from '@/api/client'
import { PASSWORD_RULE_TEXT, validatePassword } from '@/utils/password'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const form = reactive({ account: '', name: '', password: '', email: '', phone: '' })
const loading = ref(false)
const errorText = ref('')

async function submit(): Promise<void> {
  errorText.value = ''
  if (!form.account.trim() || !form.name.trim() || !form.password) {
    errorText.value = '账号、姓名和密码为必填项'
    return
  }
  const passwordError = validatePassword(form.password)
  if (passwordError) {
    errorText.value = passwordError
    return
  }
  loading.value = true
  try {
    await auth.registerTeacher({
      account: form.account.trim(),
      name: form.name.trim(),
      password: form.password,
      email: form.email.trim() || undefined,
      phone: form.phone.trim() || undefined,
    })
    toast.success('注册成功，已为你登录')
    await router.replace('/teacher')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}
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
          <p class="eyebrow">TEACHER</p>
          <h1>把课堂的资料，<br />变成可练的题。</h1>
          <p class="story__lede">注册教师账号后即可创建班级、上传资料、组卷并把练习发到班级。</p>
          <ul class="story__list">
            <li><i></i>知识库解析与切片可追溯</li>
            <li><i></i>题库导入、组卷与复核一体化</li>
            <li><i></i>班级学情与成长数据实时可见</li>
          </ul>
        </div>
      </section>

      <section class="login-form-wrap">
        <form class="login-card" novalidate @submit.prevent="submit">
          <header class="login-card__head">
            <h2>教师注册</h2>
            <p>创建账号后直接进入教师工作台。</p>
          </header>

          <div class="form-row">
            <BaseField label="账号">
              <input v-model="form.account" type="text" autocomplete="username" placeholder="登录账号" />
            </BaseField>
            <BaseField label="姓名">
              <input v-model="form.name" type="text" autocomplete="name" placeholder="真实姓名" />
            </BaseField>
          </div>
          <BaseField label="密码" :hint="PASSWORD_RULE_TEXT">
            <input v-model="form.password" type="password" autocomplete="new-password" placeholder="设置登录密码" />
          </BaseField>
          <div class="form-row">
            <BaseField label="邮箱（选填）">
              <input v-model="form.email" type="email" autocomplete="email" placeholder="name@school.edu.cn" />
            </BaseField>
            <BaseField label="手机号（选填）">
              <input v-model="form.phone" type="tel" autocomplete="tel" placeholder="手机号" />
            </BaseField>
          </div>

          <p v-if="errorText" class="form-error" role="alert">{{ errorText }}</p>

          <BaseButton variant="primary" type="submit" :loading="loading">注册并进入</BaseButton>
          <div class="login-links">
            <RouterLink class="login-link" to="/login">已有账号，去登录</RouterLink>
            <RouterLink class="login-link" to="/join">学生加入班级</RouterLink>
          </div>
        </form>
      </section>
    </main>
  </PublicLayout>
</template>
