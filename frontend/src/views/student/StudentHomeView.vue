<!-- 学生首页：班级信息占位页，仅展示 M1 已有数据，不实现问答能力。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRight,
  Check,
  Copy,
  Hash,
  MessageCircle,
  RefreshCw,
  Sparkles,
  Sprout,
  UsersRound,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { isApiError, toUserMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { copyText, formatNumber } from '@/utils/format'

const auth = useAuthStore()
const ui = useUiStore()

const loading = ref(false)
const error = ref('')
const copiedField = ref('')

const student = computed(() => (auth.user?.role === 'student' ? auth.user : null))
const initial = computed(() => student.value?.name.trim().slice(0, 1) || '学')
const qqBound = computed(() => student.value?.qq_bound === true)
const level = computed(() => student.value?.level ?? 1)
const xpTotal = computed(() => student.value?.xp_total ?? 0)
const xpProgress = computed(() => xpTotal.value % 100)

async function refreshProfile(): Promise<void> {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    await auth.fetchMe()
  } catch (err) {
    error.value = toUserMessage(err)
    if (isApiError(err) && (err.code === 40101 || err.code === 40102)) return
  } finally {
    loading.value = false
  }
}

async function copyValue(field: 'class_code' | 'student_no'): Promise<void> {
  const value = student.value?.[field]
  if (!value) return
  const ok = await copyText(value)
  if (!ok) {
    ui.error('复制失败，请手动选择文本')
    return
  }
  copiedField.value = field
  ui.success(field === 'class_code' ? '班级编号已复制' : '学号已复制')
  window.setTimeout(() => {
    if (copiedField.value === field) copiedField.value = ''
  }, 1600)
}

onMounted(() => {
  void refreshProfile()
})
</script>

<template>
  <div class="page student-home">
    <div v-if="loading && !student" class="content-stack" aria-busy="true">
      <section class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="3" />
      </section>
    </div>

    <div v-else-if="error && !student" class="panel">
      <AppEmpty error title="班级信息暂时无法加载" :description="error">
        <template #action>
          <AppButton variant="secondary" @click="refreshProfile">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </div>

    <template v-else-if="student">
      <header class="student-hero">
        <div class="student-hero__copy">
          <p class="eyebrow">MY CLASS</p>
          <h1 class="student-hero__title">
            你好，<span class="student-hero__name">{{ student.name }}</span>
          </h1>
          <p class="student-hero__desc">
            你已加入「{{ student.class_name || '当前班级' }}」。这一页会陪你从课堂资料开始，
            慢慢长出自己的知识树。
          </p>

          <dl class="identity-rows">
            <div class="identity-row">
              <dt>班级编号</dt>
              <dd>
                <span class="mono identity-code">{{ student.class_code }}</span>
                <button
                  class="copy-btn"
                  type="button"
                  :aria-label="copiedField === 'class_code' ? '班级编号已复制' : '复制班级编号'"
                  @click="copyValue('class_code')"
                >
                  <Check v-if="copiedField === 'class_code'" :size="14" :stroke-width="2" />
                  <Copy v-else :size="14" :stroke-width="1.8" />
                </button>
              </dd>
            </div>
            <div class="identity-row">
              <dt>学号</dt>
              <dd>
                <span class="mono identity-code">{{ student.student_no }}</span>
                <button
                  class="copy-btn"
                  type="button"
                  :aria-label="copiedField === 'student_no' ? '学号已复制' : '复制学号'"
                  @click="copyValue('student_no')"
                >
                  <Check v-if="copiedField === 'student_no'" :size="14" :stroke-width="2" />
                  <Copy v-else :size="14" :stroke-width="1.8" />
                </button>
              </dd>
            </div>
          </dl>

          <div class="student-hero__actions">
            <router-link to="/student/profile">
              <AppButton variant="primary">
                <MessageCircle :size="16" :stroke-width="1.9" />
                {{ qqBound ? '管理 QQ 绑定' : '绑定 QQ 接收提醒' }}
              </AppButton>
            </router-link>
            <AppButton variant="ghost" :loading="loading" @click="refreshProfile">
              <RefreshCw v-if="!loading" :size="15" :stroke-width="1.8" />
              刷新信息
            </AppButton>
          </div>
        </div>

        <aside class="student-card" aria-label="学生成长卡片">
          <span class="student-card__avatar">{{ initial }}</span>
          <div class="student-card__meta">
            <p class="student-card__label">当前等级</p>
            <p class="student-card__level tabular">Lv. {{ level }}</p>
            <AppTag :tone="qqBound ? 'success' : 'neutral'" dot>
              {{ qqBound ? 'QQ 已绑定' : 'QQ 未绑定' }}
            </AppTag>
          </div>
          <div class="student-card__xp">
            <div class="student-card__xp-head">
              <span>累计经验值</span>
              <strong class="tabular">{{ formatNumber(xpTotal) }}</strong>
            </div>
            <div class="student-card__xp-track" aria-hidden="true">
              <span class="student-card__xp-fill" :style="{ width: `${xpProgress}%` }" />
            </div>
            <p class="student-card__xp-note">经验会随着每一次学习积累，慢慢长出新的高度。</p>
          </div>
        </aside>
      </header>

      <p v-if="error" class="form-error" role="alert">
        {{ error }}
      </p>

      <section class="coming-panel panel" aria-labelledby="coming-title">
        <div class="coming-panel__art" aria-hidden="true">
          <Sprout :size="34" :stroke-width="1.44" />
          <span class="coming-panel__spark"><Sparkles :size="16" :stroke-width="1.7" /></span>
        </div>

        <div class="coming-panel__copy">
          <AppTag tone="accent" dot>正在生长</AppTag>
          <h2 id="coming-title" class="coming-panel__title">课堂问答功能开发中</h2>
          <p class="coming-panel__lead">
            下一阶段，你可以在青芽里围绕课程资料提问，得到带着出处与章节的答案。
            目前先在班级中安顿下来，熟悉自己的学习空间。
          </p>

          <ul class="coming-list">
            <li class="coming-item">
              <span class="coming-item__icon"><Hash :size="15" :stroke-width="1.8" /></span>
              <span>
                <strong>已加入班级</strong>
                <small>{{ student.class_name || '班级信息' }} · 班级编号 {{ student.class_code }}</small>
              </span>
            </li>
            <li class="coming-item">
              <span class="coming-item__icon"><UsersRound :size="15" :stroke-width="1.8" /></span>
              <span>
                <strong>学号身份</strong>
                <small class="mono">{{ student.student_no }}</small>
              </span>
            </li>
            <li class="coming-item">
              <span class="coming-item__icon"><MessageCircle :size="15" :stroke-width="1.8" /></span>
              <span>
                <strong>QQ 绑定</strong>
                <small>
                  {{ qqBound ? '已绑定，可在班级群接收青芽提醒' : '尚未绑定，可前往个人中心生成绑定码' }}
                </small>
              </span>
              <router-link v-if="!qqBound" class="coming-item__link" to="/student/profile">
                去绑定
                <ArrowRight :size="13" :stroke-width="1.9" />
              </router-link>
            </li>
          </ul>
        </div>

        <footer class="coming-panel__foot">
          <span class="status-dot" aria-hidden="true" />
          问答功能正在开发中，当前版本不提供提问入口。
        </footer>
      </section>
    </template>
  </div>
</template>

<style scoped>
.student-home {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  max-width: 1040px;
}

.student-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(290px, 1fr);
  gap: var(--sp-5);
  align-items: stretch;
  padding: var(--sp-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 88% 8%, color-mix(in srgb, var(--color-accent) 12%, transparent) 0, transparent 34%),
    linear-gradient(150deg, var(--color-surface) 0%, var(--color-surface-alt) 100%);
  box-shadow: var(--shadow-2);
}

.student-hero__copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.student-hero__title {
  font-size: 32px;
  line-height: 1.32;
  letter-spacing: -0.02em;
}

.student-hero__name {
  color: var(--color-primary);
}

.student-hero__desc {
  max-width: 520px;
  margin-top: var(--sp-3);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

.identity-rows {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3) var(--sp-6);
  margin-top: var(--sp-5);
}

.identity-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.identity-row dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.identity-row dd {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  color: var(--color-text);
}

.identity-code {
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
  transition: color 160ms ease-out, background-color 160ms ease-out, border-color 160ms ease-out;
}

.copy-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-border);
  background: var(--color-surface-alt);
}

.student-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  margin-top: var(--sp-5);
}

.student-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--sp-5);
  padding: var(--sp-5);
  border: 1px solid color-mix(in srgb, var(--color-primary) 18%, var(--color-border));
  border-radius: var(--radius-md);
  background:
    linear-gradient(165deg, color-mix(in srgb, var(--color-primary) 94%, var(--color-surface)) 0%, var(--color-primary-hover) 100%);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-1);
}

.student-card__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border: 1px solid color-mix(in srgb, var(--color-accent) 45%, transparent);
  border-radius: 999px;
  color: var(--color-accent);
  background: color-mix(in srgb, var(--color-text-inverse) 10%, transparent);
  font-size: var(--fs-xl);
  font-weight: 600;
}

.student-card__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-2);
  margin-top: calc(var(--sp-5) * -1);
}

.student-card__label {
  color: color-mix(in srgb, var(--color-text-inverse) 64%, transparent);
  font-size: var(--fs-xs);
  letter-spacing: 0.08em;
}

.student-card__level {
  font-size: 38px;
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.student-card__xp {
  padding-top: var(--sp-4);
  border-top: 1px solid color-mix(in srgb, var(--color-text-inverse) 16%, transparent);
}

.student-card__xp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  font-size: var(--fs-sm);
}

.student-card__xp-head span {
  color: color-mix(in srgb, var(--color-text-inverse) 62%, transparent);
}

.student-card__xp-head strong {
  font-size: var(--fs-lg);
}

.student-card__xp-track {
  height: 6px;
  margin-top: var(--sp-2);
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-text-inverse) 16%, transparent);
}

.student-card__xp-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-accent);
  transition: width 200ms ease-out;
}

.student-card__xp-note {
  margin-top: var(--sp-2);
  color: color-mix(in srgb, var(--color-text-inverse) 55%, transparent);
  font-size: 11px;
  line-height: 1.65;
}

.coming-panel {
  padding: var(--sp-6);
}

.coming-panel__art {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin-bottom: var(--sp-4);
  border: 1px dashed color-mix(in srgb, var(--color-primary) 34%, transparent);
  border-radius: 999px;
  color: var(--color-primary);
  background:
    radial-gradient(circle at 50% 58%, var(--color-primary-soft) 0, transparent 70%),
    var(--color-surface-alt);
}

.coming-panel__spark {
  position: absolute;
  top: -2px;
  right: -2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  color: var(--color-accent);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.coming-panel__title {
  margin-top: var(--sp-2);
  font-size: var(--fs-xl);
}

.coming-panel__lead {
  max-width: 660px;
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

.coming-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  margin-top: var(--sp-5);
  border-top: 1px solid var(--color-border);
}

.coming-item {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--fs-sm);
}

.coming-item__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.coming-item strong {
  display: block;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.coming-item small {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.coming-item__link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.coming-panel__foot {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-top: var(--sp-5);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

@media (max-width: 900px) {
  .student-hero {
    grid-template-columns: 1fr;
  }

  .student-card {
    min-height: 240px;
  }
}

@media (max-width: 560px) {
  .student-hero,
  .coming-panel {
    padding: var(--sp-4);
  }

  .student-hero__title {
    font-size: var(--fs-2xl);
  }

  .identity-rows {
    flex-direction: column;
    gap: var(--sp-2);
  }
}
</style>
