<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import PublicLayout from '@/layouts/PublicLayout.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth'
import { toUserMessage } from '@/api/client'
import { useToast } from '@/composables/useToast'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const form = reactive({ invite_code: '', student_no: '', name: '', password: '' })
const loading = ref(false)
const errorText = ref('')

async function submit(): Promise<void> {
  errorText.value = ''
  if (!form.invite_code.trim() || !form.student_no.trim() || !form.name.trim() || !form.password) {
    errorText.value = '请完整填写邀请码、学号、姓名和密码'
    return
  }
  if (form.password.length < 6) {
    errorText.value = '密码至少 6 位'
    return
  }
  loading.value = true
  try {
    await auth.joinClass({
      invite_code: form.invite_code.trim(),
      student_no: form.student_no.trim(),
      name: form.name.trim(),
      password: form.password,
    })
    toast.success('已加入班级')
    await router.replace('/student')
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
          <p class="eyebrow">JOIN CLASS</p>
          <h1>带着邀请码，<br />开始今天的练习。</h1>
          <p class="story__lede">向班级老师索取 6 位邀请码，填写学号与姓名即可加入班级。</p>
          <ul class="story__list">
            <li><i></i>加入后即可看到班级试卷与待办</li>
            <li><i></i>练习中可选中题目文字问问小芽</li>
            <li><i></i>经验、等级与成长记录自动累计</li>
          </ul>
        </div>
        <p class="story__quote">“每一次认真作答，都会留下痕迹。”<span>青芽学习手记</span></p>
      </section>

      <section class="login-form-wrap">
        <form class="login-card" novalidate @submit.prevent="submit">
          <header class="login-card__head">
            <h2>加入班级</h2>
            <p>加入成功后会自动登录学生账号。</p>
          </header>

          <BaseField label="邀请码" hint="6 位邀请码，向班级老师索取">
            <input
              v-model="form.invite_code"
              type="text"
              maxlength="12"
              autocomplete="off"
              placeholder="请输入邀请码"
            />
          </BaseField>
          <div class="form-row">
            <BaseField label="学号">
              <input v-model="form.student_no" type="text" autocomplete="username" placeholder="班级学号" />
            </BaseField>
            <BaseField label="姓名">
              <input v-model="form.name" type="text" autocomplete="name" placeholder="真实姓名" />
            </BaseField>
          </div>
          <BaseField label="密码" hint="至少 6 位">
            <input
              v-model="form.password"
              type="password"
              autocomplete="new-password"
              placeholder="设置登录密码"
            />
          </BaseField>

          <p v-if="errorText" class="form-error" role="alert">{{ errorText }}</p>

          <BaseButton variant="primary" type="submit" :loading="loading">加入并进入</BaseButton>
          <div class="login-links">
            <RouterLink class="login-link" to="/login">已有账号，去登录</RouterLink>
            <RouterLink class="login-link" to="/register/teacher">教师注册</RouterLink>
          </div>
        </form>
      </section>
    </main>
  </PublicLayout>
</template>
