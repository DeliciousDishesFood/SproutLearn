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

  <div class="columns">
    <section class="card stack">
      <header class="card__head"><h2>账号信息</h2></header>
      <div class="row" style="gap: 12px">
        <span class="avatar" style="width: 42px; height: 42px; font-size: 15px">
          {{ auth.displayName.slice(0, 1) }}
        </span>
        <div>
          <p class="strong">{{ auth.displayName }}</p>
          <p class="small muted">教师账号</p>
        </div>
      </div>
      <div class="kv">
        <span>登录账号：<b class="mono">{{ auth.teacher?.account ?? '—' }}</b></span>
      </div>
    </section>

    <section class="card stack">
      <header class="card__head"><h2>账号安全</h2></header>
      <ChangePasswordForm />
    </section>
  </div>
</template>
