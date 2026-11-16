<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, Sprout } from 'lucide-vue-next'
import PublicLayout from '@/layouts/PublicLayout.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseTabs from '@/components/ui/BaseTabs.vue'
import GrowthTrack from '@/components/business/GrowthTrack.vue'
import { useAuthStore } from '@/stores/auth'
import { workbenchApi } from '@/api/workbench'
import { isApiError, toUserMessage } from '@/api/client'
import type { LoginPayload } from '@/api/contract'
import xiaoyaBot from '@/assets/brand/xiaoya-bot.png'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const ROLES = [
  { key: 'teacher', label: '教师' },
  { key: 'student', label: '学生' },
]

const mode = ref<'teacher' | 'student'>('teacher')
const teacherForm = reactive({ account: '', password: '' })
const studentForm = reactive({ class_code: '', student_no: '', password: '' })
const loading = ref(false)
const errorText = ref('')
const showPassword = ref(false)
const quote = ref<{ text: string; from: string } | null>(null)
const trackStep = ref(0)

const panelLabelId = computed(() => `login-role-tab-${mode.value}`)

function homePath(): string {
  return auth.isTeacher ? '/teacher' : '/student'
}

function setMode(value: string): void {
  const next = value === 'student' ? 'student' : 'teacher'
  if (next === mode.value) return
  mode.value = next
  errorText.value = ''
  showPassword.value = false
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

let trackTimer = 0

onMounted(async () => {
  // 轨迹只推进一次：完成作答 → 获得讲评，之后停住，不做循环动画。
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    trackTimer = window.setTimeout(() => {
      trackStep.value = 1
    }, 1100)
  }

  if (auth.isLoggedIn) {
    await router.replace(homePath())
    return
  }
  try {
    const result = await workbenchApi.quote()
    quote.value = { text: result.text, from: result.from }
  } catch {
    // 接口失败就不显示金句，不用本地文案伪装成功。
    quote.value = null
  }
})

onBeforeUnmount(() => window.clearTimeout(trackTimer))
</script>

<template>
  <PublicLayout>
    <main class="gt-login">
      <!-- 左：石墨品牌画布 -->
      <section class="gt-canvas" aria-label="青芽产品介绍">
        <div class="gt-canvas__rules" aria-hidden="true" />
        <div class="gt-canvas__glow" aria-hidden="true" />

        <header class="gt-canvas__head">
          <RouterLink class="gt-brand" to="/">
            <span class="gt-brand__mark" aria-hidden="true"><Sprout :size="15" /></span>
            <span class="gt-brand__text">青芽<em>SproutLearn</em></span>
          </RouterLink>
          <p class="gt-canvas__pitch">让每一次练习，都留下成长的轨迹</p>
        </header>

        <div class="gt-canvas__center">
          <p class="gt-canvas__eyebrow">Growth Track · 学习轨迹</p>
          <div class="gt-canvas__track">
            <img
              class="gt-canvas__xiaoya"
              :src="xiaoyaBot"
              alt="小芽形象"
              width="56"
              height="56"
            />
            <GrowthTrack :active="trackStep" />
          </div>
        </div>

        <ul class="gt-caps">
          <li><b>自动保存</b><span>切换题目不丢失答案</span></li>
          <li><b>讲评有依据</b><span>区分官方解析与 AI 生成内容</span></li>
          <li><b>成长记录</b><span>作答结果回流学习记录</span></li>
        </ul>

        <p v-if="quote" class="gt-quote">“{{ quote.text }}”<span>{{ quote.from }}</span></p>
      </section>

      <!-- 右：冷灰舞台上的紧凑登录卡 -->
      <section class="gt-side">
        <form class="gt-card" novalidate @submit.prevent="submit">
          <p class="gt-eyebrow">SIGN IN · 账号登录</p>
          <h1 class="gt-title">登录青芽</h1>
          <p class="gt-sub">继续你的学习轨迹。</p>

          <BaseTabs
            id="login-role"
            class="gt-roles"
            :model-value="mode"
            :items="ROLES"
            panel-id="login-role-panel"
            aria-label="登录身份"
            @update:model-value="setMode"
          />

          <div
            id="login-role-panel"
            class="gt-fields"
            role="tabpanel"
            :aria-labelledby="panelLabelId"
          >
            <template v-if="mode === 'teacher'">
              <BaseField label="账号">
                <input
                  v-model="teacherForm.account"
                  type="text"
                  autocomplete="username"
                  placeholder="教师账号"
                  @input="errorText = ''"
                />
              </BaseField>
              <BaseField label="密码">
                <span class="gt-pw">
                  <input
                    v-model="teacherForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    autocomplete="current-password"
                    placeholder="登录密码"
                    @input="errorText = ''"
                  />
                  <button
                    class="gt-pw__toggle"
                    type="button"
                    :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                    :aria-pressed="showPassword"
                    @click="showPassword = !showPassword"
                  >
                    <EyeOff v-if="showPassword" :size="15" aria-hidden="true" />
                    <Eye v-else :size="15" aria-hidden="true" />
                  </button>
                </span>
              </BaseField>
            </template>

            <template v-else>
              <BaseField label="班级编号">
                <input
                  v-model="studentForm.class_code"
                  type="text"
                  autocomplete="off"
                  placeholder="例如 C2026001"
                  @input="errorText = ''"
                />
              </BaseField>
              <BaseField label="学号">
                <input
                  v-model="studentForm.student_no"
                  type="text"
                  autocomplete="username"
                  placeholder="班级学号"
                  @input="errorText = ''"
                />
              </BaseField>
              <BaseField label="密码">
                <span class="gt-pw">
                  <input
                    v-model="studentForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    autocomplete="current-password"
                    placeholder="登录密码"
                    @input="errorText = ''"
                  />
                  <button
                    class="gt-pw__toggle"
                    type="button"
                    :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                    :aria-pressed="showPassword"
                    @click="showPassword = !showPassword"
                  >
                    <EyeOff v-if="showPassword" :size="15" aria-hidden="true" />
                    <Eye v-else :size="15" aria-hidden="true" />
                  </button>
                </span>
              </BaseField>
            </template>
          </div>

          <p v-if="errorText" class="form-error" role="alert">{{ errorText }}</p>

          <BaseButton class="gt-submit" variant="primary" block type="submit" :loading="loading">
            进入青芽
          </BaseButton>

          <div class="gt-links">
            <RouterLink class="login-link" to="/join">学生加入班级</RouterLink>
            <span class="gt-links__sep" aria-hidden="true" />
            <RouterLink class="login-link" to="/register/teacher">教师注册</RouterLink>
          </div>
          <p class="gt-foot">账号由班级老师统一开通，忘记密码请联系老师。</p>
        </form>
      </section>
    </main>
  </PublicLayout>
</template>

<style scoped>
.gt-login {
  display: grid;
  grid-template-columns: minmax(0, 1.32fr) minmax(420px, 0.92fr);
  min-height: 100dvh;
  padding: 14px;
  background: var(--stage-cool);
}

/* ── 左侧品牌画布 ────────────────────────────────────────── */
.gt-canvas {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 28px);
  padding: 32px 36px 24px;
  border-radius: 26px;
  background: var(--graphite);
  color: var(--graphite-ink);
  box-shadow: inset 0 0 0 1px var(--graphite-line);
  overflow: hidden;
}

.gt-canvas__rules {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: repeating-linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.055) 0 1px,
    transparent 1px 84px
  );
  mask-image: linear-gradient(180deg, transparent, #000 18%, #000 82%, transparent);
}

.gt-canvas__glow {
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(46% 42% at 58% 46%, rgba(154, 230, 0, 0.14), transparent 72%),
    radial-gradient(52% 46% at 96% 96%, rgba(154, 230, 0, 0.05), transparent 70%);
}

.gt-canvas__head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.gt-brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  width: fit-content;
}

.gt-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
  color: var(--lime);
}

.gt-brand__text {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  color: var(--graphite-ink);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.gt-brand__text em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10.5px;
  font-style: normal;
  font-weight: 500;
  letter-spacing: 0.06em;
  opacity: 0.55;
}

.gt-canvas__pitch {
  margin: 0;
  color: var(--graphite-ink-2);
  font-size: 12.5px;
  letter-spacing: 0.01em;
}

.gt-canvas__center {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
  padding: 26px 0 20px;
}

.gt-canvas__eyebrow {
  margin: 0;
  color: var(--graphite-ink-3);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.gt-canvas__track {
  position: relative;
  padding-top: 10px;
}

.gt-canvas__xiaoya {
  position: absolute;
  top: -18px;
  right: 0;
  width: 56px;
  height: 56px;
  border-radius: 999px;
  box-shadow:
    0 0 0 1px rgba(154, 230, 0, 0.3),
    0 10px 22px rgba(0, 0, 0, 0.45);
  z-index: 2;
}

.gt-caps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin: 0;
  padding: 16px 0 0;
  border-top: 1px solid var(--graphite-line);
  list-style: none;
}

.gt-caps b {
  display: block;
  color: var(--graphite-ink);
  font-size: 12.5px;
  font-weight: 600;
}

.gt-caps span {
  display: block;
  margin-top: 3px;
  color: var(--graphite-ink-3);
  font-size: 11px;
  line-height: 1.5;
}

.gt-quote {
  margin: 16px 0 0;
  color: var(--graphite-ink-3);
  font-size: 10.5px;
  letter-spacing: 0.02em;
}

.gt-quote span {
  margin-left: 8px;
  opacity: 0.72;
}

/* ── 右侧登录区 ──────────────────────────────────────────── */
.gt-side {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px clamp(20px, 3vw, 52px);
}

.gt-card {
  width: 100%;
  max-width: 392px;
  padding: 28px 28px 22px;
  border: 1px solid var(--line-cool);
  border-radius: 20px;
  background: var(--surface);
  box-shadow: 0 2px 4px rgba(11, 20, 15, 0.04), 0 24px 56px rgba(11, 20, 15, 0.1);
}

.gt-eyebrow {
  margin: 0;
  color: var(--text-3);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.gt-title {
  margin: 8px 0 0;
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.gt-sub {
  margin: 4px 0 0;
  color: var(--stage-ink-2);
  font-size: 12.5px;
}

/* 身份切换：复用 BaseTabs 的键盘语义，这里换成紧凑分段外观 */
.gt-roles {
  margin-top: 20px;
  padding: 3px;
  border: 1px solid var(--line-cool);
  border-bottom: 1px solid var(--line-cool);
  border-radius: 999px;
  background: var(--surface-cool);
  gap: 2px;
}

.gt-roles :deep(.tabs__item) {
  flex: 1;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  color: var(--stage-ink-2);
  font-size: 12.5px;
  font-weight: 600;
}

.gt-roles :deep(.tabs__item:hover) {
  color: var(--text);
}

.gt-roles :deep(.tabs__item.is-active) {
  background: var(--graphite);
  color: var(--lime);
}

.gt-fields {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin-top: 16px;
}

.gt-card :deep(.field > span:first-child) {
  color: var(--stage-ink-2);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.gt-card :deep(.field input) {
  height: 46px;
  border-color: var(--line-cool);
  background: var(--surface);
}

.gt-card :deep(.field input:focus) {
  border-color: var(--text);
  box-shadow: var(--focus-halo);
  outline: none;
}

.gt-pw {
  position: relative;
  display: block;
}

.gt-pw :deep(input),
.gt-pw input {
  width: 100%;
  padding-right: 42px;
}

.gt-pw__toggle {
  position: absolute;
  top: 50%;
  right: 5px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
}

.gt-pw__toggle:hover {
  background: var(--surface-alt);
  color: var(--text);
}

.gt-submit {
  width: 100%;
  height: 48px;
  margin-top: 18px;
  border-radius: 999px;
  font-size: 14.5px;
}

.gt-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 14px;
}

.gt-links__sep {
  width: 1px;
  height: 11px;
  background: var(--line-cool);
}

.gt-foot {
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--line-cool);
  color: var(--stage-ink-2);
  font-size: 11px;
  text-align: center;
}

@media (max-width: 1180px) {
  .gt-login {
    grid-template-columns: minmax(0, 1fr) minmax(400px, 0.85fr);
  }

  .gt-canvas__xiaoya {
    width: 48px;
    height: 48px;
    top: -14px;
  }
}

/* ── 窄屏：紧凑品牌头部 + 完整登录表单同屏 ───────────────── */
@media (max-width: 900px) {
  .gt-login {
    grid-template-columns: minmax(0, 1fr);
    padding: 0;
    background: var(--surface);
  }

  .gt-canvas {
    min-height: 0;
    padding: 18px 20px 20px;
    border-radius: 0;
  }

  .gt-canvas__center {
    padding: 18px 0 0;
    gap: 12px;
  }

  .gt-caps,
  .gt-quote,
  .gt-canvas__xiaoya {
    display: none;
  }

  .gt-canvas__pitch {
    font-size: 12px;
  }

  .gt-side {
    justify-content: flex-start;
    padding: 22px 20px calc(24px + env(safe-area-inset-bottom));
  }

  .gt-card {
    max-width: 420px;
    padding: 0;
    border: 0;
    box-shadow: none;
    background: transparent;
  }

  .gt-title {
    font-size: 23px;
  }
}
</style>
