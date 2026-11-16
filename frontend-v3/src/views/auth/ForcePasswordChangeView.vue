<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Sprout } from 'lucide-vue-next'
import PublicLayout from '@/layouts/PublicLayout.vue'
import ChangePasswordForm from '@/components/business/ChangePasswordForm.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const forced = computed(() => route.query.forced === '1')
const homePath = computed(() => (auth.isTeacher ? '/teacher' : '/student'))
</script>

<template>
  <PublicLayout>
    <main class="account-page">
      <section class="account-card">
        <RouterLink class="account-brand" to="/">
          <span class="account-brand__mark" aria-hidden="true"><Sprout :size="15" /></span>
          <span>青芽 <em>SproutLearn</em></span>
        </RouterLink>

        <p class="account-eyebrow">SECURITY · 账号安全</p>
        <h1>{{ forced ? '先设置新密码' : '修改密码' }}</h1>
        <p class="account-lede">
          {{
            forced
              ? '临时密码只能用于本次登录，设置新密码后才能继续。'
              : '验证当前密码后设置新密码。修改成功后需要重新登录。'
          }}
        </p>

        <ChangePasswordForm :forced="forced" />

        <p v-if="!forced" class="account-foot">
          <RouterLink :to="homePath">返回{{ auth.isTeacher ? '工作台' : '学习台' }}</RouterLink>
        </p>
      </section>
    </main>
  </PublicLayout>
</template>

<style scoped>
.account-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: 24px 20px calc(24px + env(safe-area-inset-bottom));
  background: var(--stage-cool);
}

.account-card {
  width: 100%;
  max-width: 440px;
  padding: 28px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--surface);
  box-shadow: 0 2px 4px rgba(11, 20, 15, 0.04), 0 24px 56px rgba(11, 20, 15, 0.08);
}

.account-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
  font-size: 13.5px;
  font-weight: 700;
}

.account-brand em {
  color: var(--text-3);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10px;
  font-style: normal;
  font-weight: 500;
  letter-spacing: 0.06em;
}

.account-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--lime-soft);
  color: var(--lime-text);
}

.account-eyebrow {
  margin: 22px 0 0;
  color: var(--text-3);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.16em;
}

.account-card h1 {
  margin: 8px 0 0;
  font-size: 23px;
  font-weight: 700;
  line-height: 1.25;
}

.account-lede {
  margin: 6px 0 20px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.account-foot {
  margin: 18px 0 0;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 640px) {
  .account-card {
    padding: 22px 18px;
  }
}
</style>
