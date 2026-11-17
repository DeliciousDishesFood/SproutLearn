<script setup lang="ts">
import ChangePasswordForm from '@/components/business/ChangePasswordForm.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">教学 · 账号</p>
      <h1>账号设置</h1>
    </div>
  </header>

  <div class="settings-page">
    <div class="columns columns--even">
      <section class="card">
        <header class="card__head"><h2>账号信息</h2></header>
        <div class="settings-profile">
          <span class="avatar" style="width: 42px; height: 42px; font-size: 15px">
            {{ auth.displayName.slice(0, 1) }}
          </span>
          <div class="settings-profile__meta">
            <p class="strong">{{ auth.displayName }}</p>
            <p class="small text-3">
              教师账号 · <span class="mono">{{ auth.teacher?.account ?? '—' }}</span>
            </p>
          </div>
        </div>
      </section>

      <section class="card stack">
        <header class="card__head"><h2>账号安全</h2></header>
        <p class="small text-3">修改密码后，其他设备需要重新登录。</p>
        <ChangePasswordForm />
      </section>
    </div>
  </div>
</template>
