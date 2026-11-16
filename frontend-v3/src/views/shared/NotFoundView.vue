<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function goHome(): void {
  if (!auth.isLoggedIn) void router.push('/login')
  else void router.push(auth.isTeacher ? '/teacher' : '/student')
}
</script>

<template>
  <div class="login-body">
    <main
      class="login-form-wrap"
      style="min-height: 100vh; display: flex; align-items: center; justify-content: center"
    >
      <div class="login-card" style="text-align: center">
        <span class="brand__mark" style="margin: 0 auto 14px" aria-hidden="true">
          <Sprout :size="19" />
        </span>
        <h2 style="font-size: 20px">页面不存在</h2>
        <p class="muted" style="margin: 8px 0 18px">链接可能已失效，或者你没有访问该页面的权限。</p>
        <button class="btn btn--primary btn--block" type="button" @click="goHome">回到首页</button>
      </div>
    </main>
  </div>
</template>
