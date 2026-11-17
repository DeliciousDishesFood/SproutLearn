<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, ChevronRight, ListChecks, Sparkles, Sprout, X } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import AskSproutPanel from '@/components/business/AskSproutPanel.vue'
import AttemptQuestionBody from '@/components/business/AttemptQuestionBody.vue'
import AttemptAnswerSheet from '@/components/business/AttemptAnswerSheet.vue'
import SaveStateIndicator from '@/components/business/SaveStateIndicator.vue'
import { attemptsApi } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'
import type { AttemptQuestion, AttemptResume } from '@/api/contract'
import { QUESTION_TYPE_LABEL, formatAnswer } from '@/utils/format'
import { useAskSproutSelection } from '@/composables/useAskSproutSelection'
import { useCountdown } from '@/composables/useCountdown'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const attemptId = computed(() => Number(route.params.attemptId))

const attempt = ref<AttemptResume | null>(null)
const loading = ref(true)
const errorText = ref('')
const submitting = ref(false)
const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const answers = reactive<Record<string, unknown>>({})
const currentIndex = ref(0)
const qScope = ref<HTMLElement | null>(null)
const askOpen = ref(false)
const askSelectedText = ref('')
const askQuestionId = ref<number | null>(null)
const sheetOpen = ref(false)
const sheetPanel = ref<HTMLElement | null>(null)
const pendingSaves = new Set<number>()
const inflight = new Map<number, Promise<void>>()
const versions = new Map<number, number>()
const timers = new Map<number, number>()

const askEnabled = computed(
  () => attempt.value?.paper.kind === 'practice' && attempt.value?.status === 'doing',
)
const { state: selection, clear: clearSelection } = useAskSproutSelection(qScope, askEnabled)

/* 手机答题卡抽屉：Tab 环绕、Escape 关闭、关闭后焦点回到触发按钮 */
useFocusTrap({
  active: () => sheetOpen.value,
  container: sheetPanel,
  onEscape: () => {
    sheetOpen.value = false
  },
})

const serverNow = computed(() => attempt.value?.server_now ?? null)
const remainingSeconds = computed(() => attempt.value?.remaining_seconds ?? null)
const { label: timerLabel, expired, warning } = useCountdown(serverNow, remainingSeconds)

const questions = computed<AttemptQuestion[]>(() => attempt.value?.questions ?? [])
const currentQuestion = computed<AttemptQuestion | null>(() => questions.value[currentIndex.value] ?? null)
const answeredCount = computed(
  () => questions.value.filter((question) => isAnswered(question.id)).length,
)
const answeredMap = computed(() => questions.value.map((question) => isAnswered(question.id)))
const isLast = computed(() => currentIndex.value >= questions.value.length - 1)
const paperKindLabel = computed(() => {
  const kind = attempt.value?.paper.kind
  if (kind === 'practice') return '练习'
  if (kind === 'homework') return '作业'
  if (kind === 'exam') return '考试'
  return '作答'
})

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function answerValue(questionId: number): unknown {
  return answers[String(questionId)]
}

function isAnswered(questionId: number): boolean {
  const value = answerValue(questionId)
  if (Array.isArray(value)) return value.length > 0
  return value !== undefined && value !== null && value !== ''
}

function applyAnswer(question: AttemptQuestion, value: unknown): void {
  if (expired.value || attempt.value?.status !== 'doing') return
  setAnswer(question.id, value)
}

function setAnswer(questionId: number, value: unknown): void {
  answers[String(questionId)] = value
  versions.set(questionId, (versions.get(questionId) ?? 0) + 1)
  pendingSaves.add(questionId)
  const existing = timers.get(questionId)
  if (existing) window.clearTimeout(existing)
  timers.set(
    questionId,
    window.setTimeout(() => {
      timers.delete(questionId)
      void persist(questionId).catch(() => undefined)
    }, 500),
  )
}

async function persist(questionId: number): Promise<void> {
  const existing = inflight.get(questionId)
  if (existing) return existing
  if (!pendingSaves.has(questionId)) return

  const task = (async () => {
    try {
      while (pendingSaves.has(questionId)) {
        const version = versions.get(questionId) ?? 0
        const value = answerValue(questionId)
        saveState.value = 'saving'
        await attemptsApi.saveAnswer(attemptId.value, questionId, value ?? null)
        // 保存成功且期间没有新的修改，才把该题移出 pending；版本变了说明有更新的答案待存。
        if ((versions.get(questionId) ?? 0) === version) {
          pendingSaves.delete(questionId)
        }
      }
      saveState.value = pendingSaves.size === 0 ? 'saved' : 'saving'
    } catch (error) {
      saveState.value = 'error'
      toast.error(`保存失败：${toUserMessage(error)}`)
      throw error
    }
  })()

  inflight.set(questionId, task)
  try {
    await task
  } finally {
    if (inflight.get(questionId) === task) inflight.delete(questionId)
  }
}

async function flushSaves(): Promise<void> {
  timers.forEach((timer) => window.clearTimeout(timer))
  timers.clear()

  // 先等在途请求；失败的题目保留在 pending，下面统一重试。
  await Promise.allSettled([...inflight.values()])
  await Promise.all([...pendingSaves].map((id) => persist(id)))

  if (pendingSaves.size > 0) {
    throw new Error('仍有答案未保存')
  }
}

/** 保存失败的显式出口：重试所有 dirty / in-flight 答案，成功才回到已保存。 */
async function retrySaves(): Promise<void> {
  if (saveState.value === 'saving') return
  saveState.value = 'saving'
  try {
    await flushSaves()
    saveState.value = 'saved'
    toast.success('答案已保存')
  } catch {
    saveState.value = 'error'
    toast.error('仍有答案未保存，请检查网络后重试')
  }
}

/* ---------- 手机滑动：滚动停止后同步题号，避免与 goTo 平滑滚动打架 ---------- */
const swipeEl = ref<HTMLElement | null>(null)
let suppressSlideSync = 0
let slideTimer: number | null = null

function readSlide(): void {
  const el = swipeEl.value
  if (!el || !el.clientWidth) return
  if (Date.now() < suppressSlideSync) return
  const index = Math.round(el.scrollLeft / el.clientWidth)
  if (index >= 0 && index < questions.value.length && index !== currentIndex.value) {
    currentIndex.value = index
    clearSelection()
    askOpen.value = false
  }
}

function onSlideScroll(): void {
  if (slideTimer) window.clearTimeout(slideTimer)
  slideTimer = window.setTimeout(readSlide, 140)
}

function scrollToSlide(index: number): void {
  const el = swipeEl.value
  if (!el || !el.clientWidth) return
  suppressSlideSync = Date.now() + 520
  el.scrollTo({ left: index * el.clientWidth, behavior: 'smooth' })
}

function goTo(index: number): void {
  if (index < 0 || index >= questions.value.length) return
  currentIndex.value = index
  clearSelection()
  askOpen.value = false
  scrollToSlide(index)
}

function openSheet(): void {
  sheetOpen.value = true
}

function jumpFromSheet(index: number): void {
  sheetOpen.value = false
  goTo(index)
}

function openAsk(): void {
  if (!selection.value || !currentQuestion.value) return
  askSelectedText.value = selection.value.text
  askQuestionId.value = currentQuestion.value.id
  askOpen.value = true
  clearSelection()
}

function closeAsk(): void {
  askOpen.value = false
  void nextTick(() => {
    qScope.value?.focus()
  })
}

const submitOpen = ref(false)
const exitOpen = ref(false)
const unsavedOpen = ref(false)

const submitMessage = computed(() => {
  const unanswered = questions.value.length - answeredCount.value
  return unanswered > 0
    ? `还有 ${unanswered} 道题未作答，提交后不可修改。`
    : '提交后试卷锁定，不可修改答案。'
})

function askSubmit(): void {
  if (submitting.value) return
  submitOpen.value = true
}

async function submit(): Promise<void> {
  if (submitting.value) return
  submitting.value = true
  submitOpen.value = false
  try {
    try {
      await flushSaves()
    } catch {
      // 保存未完成：阻断提交，不调用 submit 接口。
      toast.error('答案保存未完成，未提交；请检查网络后重试')
      return
    }
    const result = await attemptsApi.submit(attemptId.value)
    toast.success('提交成功')
    await router.replace(`/student/attempts/${result.attempt.id}/result`)
  } catch (error) {
    if (isApiError(error) && error.code === 40910) {
      toast.info('本次作答已提交，正在打开结果页')
      await router.replace(`/student/attempts/${attemptId.value}/result`)
    } else {
      toast.error(toUserMessage(error))
    }
  } finally {
    submitting.value = false
  }
}

function exit(): void {
  exitOpen.value = true
}

async function confirmExit(): Promise<void> {
  exitOpen.value = false
  try {
    await flushSaves()
  } catch {
    unsavedOpen.value = true
    return
  }
  await router.push('/student/papers')
}

async function confirmExitUnsaved(): Promise<void> {
  unsavedOpen.value = false
  await router.push('/student/papers')
}

function handleBeforeUnload(event: BeforeUnloadEvent): void {
  if (pendingSaves.size > 0 || inflight.size > 0) {
    event.preventDefault()
    event.returnValue = ''
  }
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const data = await attemptsApi.resume(attemptId.value)
    if (data.status !== 'doing') {
      await router.replace(`/student/attempts/${attemptId.value}/result`)
      return
    }
    attempt.value = data
    Object.keys(answers).forEach((key) => delete answers[key])
    Object.entries(data.answers ?? {}).forEach(([key, value]) => {
      answers[key] = value
    })
  } catch (error) {
    if (isApiError(error) && error.code === 40910) {
      await router.replace(`/student/attempts/${attemptId.value}/result`)
      return
    }
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

watch(currentIndex, () => {
  clearSelection()
  askOpen.value = false
})

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  void load()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  timers.forEach((timer) => window.clearTimeout(timer))
  timers.clear()
  if (slideTimer) window.clearTimeout(slideTimer)
})
</script>
<template>
  <div class="practice-body att-page">
    <header class="att-bar">
      <RouterLink class="att-brand" to="/student">
        <span class="att-brand__mark" aria-hidden="true"><Sprout :size="17" /></span>
        <span class="att-brand__text">青芽 <em>SproutLearn</em></span>
      </RouterLink>

      <div v-if="attempt" class="att-paper">
        <p class="att-paper__eyebrow">{{ paperKindLabel }} · 共 {{ questions.length }} 题</p>
        <p class="att-paper__title">{{ attempt.paper.title }}</p>
      </div>

      <div v-if="attempt" class="att-meta">
        <p class="att-progress">
          <span>已答</span><b class="mono">{{ answeredCount }}</b>
          <span class="mono att-progress__total">/ {{ questions.length }}</span>
        </p>
        <span class="att-timer mono" :class="{ 'is-danger': warning || expired }">{{ timerLabel }}</span>
        <SaveStateIndicator :state="saveState" @retry="retrySaves" />
        <button class="btn btn--ghost att-exit" type="button" @click="exit">退出</button>
      </div>
    </header>

    <main class="att-main">
      <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
      <p v-if="loading" class="loading-line">正在恢复作答…</p>
      <p v-if="attempt && expired" class="notice notice--warn">
        本次作答已截止，输入已锁定；你可以提交已保存的答案，或退出作答。
      </p>

      <template v-if="attempt && currentQuestion">
        <div class="att-grid">
          <section ref="qScope" class="att-stage" aria-label="当前题目" tabindex="-1">
            <div class="att-qmeta">
              <span class="att-qmeta__index mono">
                QUESTION {{ pad(currentQuestion.seq) }}
                <span class="att-qmeta__of">/ {{ pad(questions.length) }}</span>
              </span>
              <span class="att-qmeta__sep" aria-hidden="true" />
              <span>{{ QUESTION_TYPE_LABEL[currentQuestion.type] }}</span>
              <span class="att-qmeta__sep" aria-hidden="true" />
              <span>{{ currentQuestion.knowledge_tag }}</span>
              <span class="att-qmeta__sep" aria-hidden="true" />
              <span>{{ currentQuestion.score }} 分</span>
            </div>

            <div class="att-qbody att-qbody--desktop">
              <div class="q-scope">
                <AttemptQuestionBody
                  :question="currentQuestion"
                  :value="answerValue(currentQuestion.id)"
                  :disabled="expired"
                  @answer="applyAnswer(currentQuestion, $event)"
                />
              </div>
            </div>

            <div class="att-qbody att-qbody--swipe" aria-label="滑动切换题目">
              <div ref="swipeEl" class="att-swipe" @scroll="onSlideScroll">
                <div v-for="question in questions" :key="question.id" class="att-slide">
                  <div class="att-slide__head">
                    <span class="att-slide__index mono">QUESTION {{ pad(question.seq) }}</span>
                    <span class="att-slide__tag">
                      {{ QUESTION_TYPE_LABEL[question.type] }} · {{ question.score }} 分
                    </span>
                  </div>
                  <AttemptQuestionBody
                    :question="question"
                    :value="answerValue(question.id)"
                    :disabled="expired"
                    @answer="applyAnswer(question, $event)"
                  />
                </div>
              </div>
            </div>

            <p class="att-hint">
              {{
                attempt.paper.kind === 'practice'
                  ? '选择后自动保存，切换题目不会丢失；选中题干或选项可以问问小芽。'
                  : '选择后自动保存，切换题目不会丢失。'
              }}
            </p>
          </section>

          <aside class="att-rail">
            <AttemptAnswerSheet
              :total="questions.length"
              :current-index="currentIndex"
              :answered="answeredMap"
              :save-state="saveState"
              @jump="goTo"
            />
            <div class="att-rail__action">
              <BaseButton variant="primary" block :loading="submitting" @click="askSubmit">
                提交试卷
              </BaseButton>
              <p class="att-rail__note">提交前会自动保存，提交后试卷锁定，无法修改答案。</p>
            </div>
          </aside>
        </div>
      </template>

      <p v-else-if="!loading" class="empty-block">
        {{ errorText || '没有可作答的题目。' }}
      </p>
    </main>

    <footer v-if="attempt && currentQuestion" class="att-foot">
      <button class="btn" type="button" :disabled="currentIndex === 0" @click="goTo(currentIndex - 1)">
        <ChevronLeft :size="15" aria-hidden="true" />上一题
      </button>

      <button
        class="att-sheet-trigger"
        type="button"
        :aria-expanded="sheetOpen"
        aria-controls="attempt-sheet"
        @click="openSheet"
      >
        <ListChecks :size="15" aria-hidden="true" />答题卡
        <span class="mono">{{ pad(answeredCount) }}/{{ pad(questions.length) }}</span>
      </button>

      <span class="att-foot__pos mono">{{ pad(currentIndex + 1) }} / {{ pad(questions.length) }}</span>

      <button v-if="!isLast" class="btn" type="button" @click="goTo(currentIndex + 1)">
        下一题<ChevronRight :size="15" aria-hidden="true" />
      </button>
      <BaseButton v-else variant="primary" :loading="submitting" @click="askSubmit">提交试卷</BaseButton>
    </footer>

    <button
      v-if="selection"
      class="ask-trigger"
      type="button"
      data-ask-trigger
      :style="{ left: `${selection.x}px`, top: `${selection.y}px`, transform: 'translate(-50%, -100%)' }"
      @mousedown.prevent
      @click="openAsk"
    >
      <Sparkles :size="14" aria-hidden="true" />问问小芽
    </button>

    <AskSproutPanel
      v-if="attempt"
      :open="askOpen"
      :attempt-id="attemptId"
      :question-id="askQuestionId"
      :selected-text="askSelectedText"
      @close="closeAsk"
      @clear-selection="askSelectedText = ''"
    />

    <p class="sr-only" aria-live="polite">
      {{ currentQuestion ? `当前第 ${currentQuestion.seq} 题，答案 ${formatAnswer(answerValue(currentQuestion.id), currentQuestion.type)}` : '' }}
    </p>

    <Teleport to="body">
      <Transition name="att-drawer">
        <div v-if="sheetOpen" class="att-drawer">
          <div class="att-drawer__mask" @click="sheetOpen = false" />
          <div
            id="attempt-sheet"
            ref="sheetPanel"
            class="att-drawer__panel"
            role="dialog"
            aria-modal="true"
            aria-label="答题卡"
          >
            <header class="att-drawer__head">
              <h2 class="att-drawer__title">答题卡</h2>
              <button class="att-drawer__close" type="button" aria-label="关闭答题卡" @click="sheetOpen = false">
                <X :size="18" aria-hidden="true" />
              </button>
            </header>
            <AttemptAnswerSheet
              :total="questions.length"
              :current-index="currentIndex"
              :answered="answeredMap"
              :save-state="saveState"
              @jump="jumpFromSheet"
            />
            <BaseButton variant="primary" block :loading="submitting" @click="askSubmit">提交试卷</BaseButton>
          </div>
        </div>
      </Transition>
    </Teleport>

    <ConfirmDialog
      :open="submitOpen"
      title="提交试卷"
      :message="submitMessage"
      confirm-label="提交"
      tone="primary"
      :loading="submitting"
      @confirm="submit"
      @cancel="submitOpen = false"
    />
    <ConfirmDialog
      :open="exitOpen"
      title="退出作答"
      message="已保存的答案会保留，未保存的修改将丢失。"
      confirm-label="退出"
      tone="primary"
      @confirm="confirmExit"
      @cancel="exitOpen = false"
    />
    <ConfirmDialog
      :open="unsavedOpen"
      title="仍有答案未保存"
      message="退出后未保存的修改会丢失。仍要退出吗？"
      confirm-label="仍要退出"
      tone="danger"
      @confirm="confirmExitUnsaved"
      @cancel="unsavedOpen = false"
    />
  </div>
</template>

<style scoped>
/* 作答页：一个主角（当前题）+ 一条轨迹（作答位置），冷灰舞台只在本页使用 */
.att-page {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  overflow: hidden;
  background: var(--stage-cool);
}

/* ── 顶栏：完整试卷名只出现一次 ───────────────────────────── */
.att-bar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 24px;
  padding: 14px 26px;
  border-bottom: 1px solid var(--line-cool);
  background: var(--stage-cool);
}

.att-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.att-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--graphite);
  color: var(--lime);
}

.att-brand__text {
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.att-brand__text em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 10px;
  font-style: normal;
  letter-spacing: 0.06em;
  color: var(--text-3);
}

.att-paper {
  min-width: 0;
}

.att-paper__eyebrow {
  margin: 0;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--text-3);
}

.att-paper__title {
  margin: 1px 0 0;
  font-size: 13.5px;
  font-weight: 650;
  letter-spacing: -0.005em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.att-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.att-progress {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  margin: 0;
  font-size: 11.5px;
  color: var(--text-3);
}

.att-progress b {
  font-size: 15px;
  color: var(--text);
}

.att-progress__total {
  color: var(--text-3);
}

.att-timer {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 11px;
  border: 1px solid var(--line-cool);
  border-radius: 999px;
  background: var(--surface);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.att-timer.is-danger {
  border-color: var(--danger-line);
  color: var(--danger);
}

.att-exit {
  height: 32px;
  padding: 0 12px;
}

/* ── 主体 ─────────────────────────────────────────────────── */
.att-main {
  flex: 1;
  overflow-y: auto;
  padding: 30px 26px 26px;
}

.att-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 296px;
  gap: 32px;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
}

.att-stage {
  min-width: 0;
  align-self: start;
}

.att-qmeta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-3);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
}

.att-qmeta__index {
  color: var(--text);
  letter-spacing: 0.14em;
}

.att-qmeta__of {
  color: var(--text-3);
  letter-spacing: 0.06em;
}

.att-qmeta__sep {
  width: 3px;
  height: 3px;
  border-radius: 999px;
  background: var(--line-strong);
}

.att-qbody--desktop {
  margin-top: 16px;
}

.att-qbody--swipe {
  display: none;
}

.att-hint {
  margin: 18px 0 0;
  font-size: 11.5px;
  color: var(--text-3);
}

.q-scope:focus,
.att-stage:focus {
  outline: none;
}

/* ── 右侧：作答轨迹 + 答题卡 ─────────────────────────────── */
.att-rail {
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border: 1px solid var(--line-cool);
  border-radius: 12px;
  background: var(--surface);
}

.att-rail__action {
  padding-top: 14px;
  border-top: 1px solid var(--line-cool);
}

.att-rail__note {
  margin: 9px 0 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-3);
}

/* ── 底栏 ─────────────────────────────────────────────────── */
.att-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 26px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--line-cool);
  background: var(--stage-cool);
}

.att-foot__pos {
  font-size: 11.5px;
  color: var(--text-3);
}

.att-sheet-trigger {
  display: none;
  align-items: center;
  gap: 6px;
  height: 44px;
  padding: 0 12px;
  border: 1px solid var(--line-cool);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

.att-sheet-trigger .mono {
  font-size: 11px;
  color: var(--text-3);
}

/* ── 手机答题卡抽屉 ──────────────────────────────────────── */
.att-drawer {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: flex;
  align-items: flex-end;
}

.att-drawer__mask {
  position: absolute;
  inset: 0;
  background: rgba(11, 16, 13, 0.42);
}

.att-drawer__panel {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-height: 82dvh;
  overflow-y: auto;
  padding: 18px 18px calc(18px + env(safe-area-inset-bottom));
  border-radius: 20px 20px 0 0;
  background: var(--surface);
}

.att-drawer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.att-drawer__title {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.att-drawer__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin: -10px -10px -10px 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.att-drawer__close:hover {
  background: var(--surface-alt);
}

.att-drawer-enter-active,
.att-drawer-leave-active {
  transition: opacity 220ms ease;
}

.att-drawer-enter-active .att-drawer__panel,
.att-drawer-leave-active .att-drawer__panel {
  transition: transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

.att-drawer-enter-from,
.att-drawer-leave-to {
  opacity: 0;
}

.att-drawer-enter-from .att-drawer__panel,
.att-drawer-leave-to .att-drawer__panel {
  transform: translateY(24px);
}

@media (min-width: 901px) {
  .att-drawer {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .att-drawer-enter-active,
  .att-drawer-leave-active,
  .att-drawer-enter-active .att-drawer__panel,
  .att-drawer-leave-active .att-drawer__panel {
    transition: none;
  }
}

/* ── 平板 ─────────────────────────────────────────────────── */
@media (max-width: 1100px) {
  .att-grid {
    grid-template-columns: minmax(0, 1fr) 262px;
    gap: 22px;
  }
}

/* ── 手机 ─────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .att-bar {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 12px;
    padding: 10px 16px 12px;
  }

  .att-paper {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .att-paper__title {
    font-size: 12.5px;
  }

  .att-meta {
    grid-column: 2;
    gap: 10px;
  }

  .att-progress,
  .att-exit {
    display: none;
  }

  .att-main {
    padding: 18px 16px 20px;
  }

  .att-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }

  .att-qbody--desktop {
    display: none;
  }

  .att-qbody--swipe {
    display: block;
    margin-top: 12px;
  }

  /* 手机上题号信息由滑轨卡头承担，避免与页面级 meta 重复 */
  .att-qmeta {
    display: none;
  }

  .att-swipe {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
    overscroll-behavior-x: contain;
    /* 横向滚动容器需要自成一个绘制包含块，否则滑轨内容会被算进页面级滚动宽度 */
    contain: paint;
  }

  .att-swipe::-webkit-scrollbar {
    display: none;
  }

  .att-slide {
    flex: 0 0 100%;
    min-width: 0;
    padding-right: 2px;
    scroll-snap-align: start;
  }

  .att-slide__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
    color: var(--text-3);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
  }

  .att-slide__index {
    color: var(--text);
  }

  .att-rail {
    display: none;
  }

  .att-hint {
    margin-top: 14px;
    font-size: 11px;
  }

  .att-foot {
    gap: 8px;
    padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  }

  .att-foot .btn,
  .att-foot :deep(.btn) {
    flex: 1;
    height: 44px;
    padding: 0 12px;
  }

  .att-foot__pos {
    display: none;
  }

  .att-sheet-trigger {
    display: inline-flex;
    flex: none;
  }
}
</style>
