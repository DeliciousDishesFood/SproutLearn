<!-- 学生答题：服务端截止时间倒计时、800ms 防抖自动保存、切题/失焦冲刷、提交锁卷。 -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  RefreshCw,
  Send,
  ShieldCheck,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppCard from '@/components/base/AppCard.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import QuestionAnswerInput from '@/components/business/QuestionAnswerInput.vue'
import { attemptsApi } from '@/api/attempts'
import { papersApi } from '@/api/papers'
import { isApiError, toUserMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { ATTEMPT_STATUS_META, BLANK_MODE_META, QUESTION_TYPE_META } from '@/utils/constants'
import { formatCountdown, formatDateTime, parseDateTime } from '@/utils/format'
import { isAnswerEmpty } from '@/utils/questions'
import {
  ATTEMPT_SAVE_DEBOUNCE_MS,
  buildInitialAnswers,
  clearAttemptDraft,
  readAttemptDraft,
  writeAttemptDraft,
} from '@/utils/attemptDraft'
import type { AttemptDetail, AttemptQuestion, AttemptResult } from '@/api/types'

type SaveState = 'idle' | 'pending' | 'saving' | 'saved' | 'error'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const attemptId = Number(route.params.id)
const paperId = Number(route.query.paper_id)

const attempt = ref<AttemptDetail | null>(null)
const answers = ref<Record<number, unknown>>({})
const saveStates = reactive<Record<number, SaveState>>({})
const saveErrors = reactive<Record<number, string>>({})
const savedTimes = reactive<Record<number, string>>({})

const loading = ref(true)
const loadError = ref('')
const currentIndex = ref(0)
const submitting = ref(false)
const submitError = ref('')
const confirmOpen = ref(false)
const submittedOpen = ref(false)
const submitResult = ref<AttemptResult | null>(null)
const autoSubmitted = ref(false)
const timeUp = ref(false)

const remainingSeconds = ref<number | null>(null)
const deadlineTimestamp = ref<number | null>(null)
const now = ref(Date.now())
/** 服务端时钟偏移：server_now - Date.now()，抵消本机时钟误差。 */
let serverOffsetMs = 0
/** 服务端下发的剩余秒数与其对应的服务端时间戳，作为倒计时基准。 */
let remainingBase: number | null = null
let remainingBaseAt = 0

const timers = new Map<number, number>()
const inflight = new Map<number, Promise<void>>()
const versions = new Map<number, number>()
let ticker: number | null = null

const questions = computed<AttemptQuestion[]>(() => attempt.value?.questions ?? [])
const currentQuestion = computed<AttemptQuestion | null>(
  () => questions.value[currentIndex.value] ?? null,
)
const answeredCount = computed(
  () => questions.value.filter((question) => !isAnswerEmpty(question.type, answers.value[question.id])).length,
)
const unansweredQuestions = computed(() =>
  questions.value.filter((question) => isAnswerEmpty(question.type, answers.value[question.id])),
)
const progressPercent = computed(() => {
  const total = questions.value.length
  return total === 0 ? 0 : Math.round((answeredCount.value / total) * 100)
})
const lockedByServer = computed(() => Boolean(attempt.value && attempt.value.status !== 'doing'))
const inputLocked = computed(() => lockedByServer.value || timeUp.value)
const isUrgent = computed(
  () => remainingSeconds.value !== null && remainingSeconds.value > 0 && remainingSeconds.value <= 60,
)
const isOver = computed(() => remainingSeconds.value !== null && remainingSeconds.value <= 0)
const remainingText = computed(() =>
  remainingSeconds.value === null ? '不限时' : formatCountdown(remainingSeconds.value),
)
const deadlineLabel = computed(() => formatDateTime(attempt.value?.deadline_at))
const statusMeta = computed(() =>
  attempt.value ? ATTEMPT_STATUS_META[attempt.value.status] : null,
)
const blankMeta = computed(() =>
  attempt.value ? BLANK_MODE_META[attempt.value.paper.blank_mode] : null,
)
const pendingSaveCount = computed(
  () => questions.value.filter((question) => saveStates[question.id] === 'pending').length,
)
const errorSaveCount = computed(
  () => questions.value.filter((question) => saveStates[question.id] === 'error').length,
)
const lastSavedTime = computed(() => {
  const times = questions.value
    .map((question) => savedTimes[question.id])
    .filter((value): value is string => Boolean(value))
    .sort()
  return times.length > 0 ? times[times.length - 1] : ''
})
const pendingReviewNotice = computed(() => {
  if (!submitResult.value) return ''
  return submitResult.value.attempt.needs_review
    ? '本卷含低置信作答，最终分数以教师复核后为准。'
    : '本卷已完成自动判分。'
})

function mapError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  if (isApiError(err) && err.code === 40911) return '试卷当前状态不允许该操作'
  if (isApiError(err) && err.code === 40910) return '本次作答已提交，不能再修改答案'
  return toUserMessage(err)
}

function persist(): void {
  if (!attempt.value) return
  writeAttemptDraft(attempt.value, answers.value)
}

function firstUnansweredIndex(): number {
  const index = questions.value.findIndex((question) =>
    isAnswerEmpty(question.type, answers.value[question.id]),
  )
  return index >= 0 ? index : 0
}

function saveStateOf(questionId: number): SaveState {
  return saveStates[questionId] ?? 'idle'
}

function clearTimer(questionId: number): void {
  const timer = timers.get(questionId)
  if (timer !== undefined) {
    window.clearTimeout(timer)
    timers.delete(questionId)
  }
}

function scheduleSave(questionId: number, delayMs = ATTEMPT_SAVE_DEBOUNCE_MS): void {
  clearTimer(questionId)
  timers.set(
    questionId,
    window.setTimeout(() => {
      timers.delete(questionId)
      void saveQuestion(questionId)
    }, delayMs),
  )
}

function lockFromServer(): void {
  if (!attempt.value) return
  attempt.value = { ...attempt.value, status: 'submitted' }
  stopTicker()
  ui.warning('本次作答已提交，页面已锁定')
}

async function saveQuestion(questionId: number): Promise<void> {
  if (!attempt.value || attempt.value.status !== 'doing' || !attempt.value.questions.length) return
  clearTimer(questionId)
  const existing = inflight.get(questionId)
  if (existing) return existing
  if (saveStates[questionId] === 'saved' || saveStates[questionId] === 'idle') return

  const version = versions.get(questionId) ?? 0
  const value = answers.value[questionId]
  saveStates[questionId] = 'saving'
  saveErrors[questionId] = ''

  const job = (async (): Promise<void> => {
    try {
      await attemptsApi.saveAnswer(attemptId, questionId, value)
    } catch (firstErr) {
      if (isApiError(firstErr) && firstErr.code === 40910) {
        lockFromServer()
        return
      }
      try {
        await attemptsApi.saveAnswer(attemptId, questionId, value)
      } catch (retryErr) {
        if (isApiError(retryErr) && retryErr.code === 40910) {
          lockFromServer()
          return
        }
        saveStates[questionId] = 'error'
        saveErrors[questionId] = mapError(retryErr)
        return
      }
    }
    if ((versions.get(questionId) ?? 0) === version) {
      saveStates[questionId] = 'saved'
      savedTimes[questionId] = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    } else {
      saveStates[questionId] = 'pending'
    }
  })()

  inflight.set(questionId, job)
  try {
    await job
  } finally {
    inflight.delete(questionId)
    if (saveStateOf(questionId) === 'pending' && !timers.has(questionId)) {
      scheduleSave(questionId, 40)
    }
  }
}

function handleAnswerChange(questionId: number, value: unknown): void {
  if (inputLocked.value) return
  answers.value[questionId] = value
  versions.set(questionId, (versions.get(questionId) ?? 0) + 1)
  saveStates[questionId] = 'pending'
  saveErrors[questionId] = ''
  persist()
  scheduleSave(questionId)
}

function handleAnswerBlur(questionId: number): void {
  if (inputLocked.value) return
  const state = saveStates[questionId]
  if (state === 'pending' || state === 'error') void saveQuestion(questionId)
}

function goToQuestion(index: number): void {
  if (index < 0 || index >= questions.value.length || index === currentIndex.value) return
  const previous = currentQuestion.value
  if (previous) {
    clearTimer(previous.id)
    const state = saveStates[previous.id]
    if (state === 'pending' || state === 'error') void saveQuestion(previous.id)
  }
  currentIndex.value = index
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function prevQuestion(): void {
  goToQuestion(currentIndex.value - 1)
}

function nextQuestion(): void {
  goToQuestion(currentIndex.value + 1)
}

async function flushAll(includeErrors = true): Promise<boolean> {
  for (const question of questions.value) clearTimer(question.id)
  const needsSave = (): number[] =>
    questions.value
      .filter((question) => {
        const state = saveStates[question.id]
        return (
          state === 'pending' ||
          state === 'saving' ||
          inflight.has(question.id) ||
          (includeErrors && state === 'error')
        )
      })
      .map((question) => question.id)

  await Promise.all(needsSave().map((questionId) => saveQuestion(questionId)))
  const remaining = needsSave()
  if (remaining.length > 0) {
    await Promise.all(remaining.map((questionId) => saveQuestion(questionId)))
  }
  return !questions.value.some((question) => saveStates[question.id] === 'error')
}

function startTicker(): void {
  stopTicker()
  tick()
  ticker = window.setInterval(tick, 1000)
}

function stopTicker(): void {
  if (ticker !== null) {
    window.clearInterval(ticker)
    ticker = null
  }
}

/**
 * 用服务端时间校准倒计时：offset = server_now - Date.now()，
 * 剩余秒数从 remaining_seconds 按服务端流逝时间递减。
 * 响应缺字段（旧后端/草稿兜底）时退回 deadline_at 与本机时钟。
 */
function syncServerClock(
  serverNow: string | undefined,
  remaining: number | null | undefined,
  deadlineAt: string | null,
): void {
  const serverTimestamp = parseDateTime(serverNow)
  if (serverTimestamp !== null && remaining !== undefined) {
    serverOffsetMs = serverTimestamp - Date.now()
    remainingBase = remaining
    remainingBaseAt = serverTimestamp
    deadlineTimestamp.value = null
    remainingSeconds.value = remaining
    return
  }
  serverOffsetMs = 0
  remainingBase = null
  deadlineTimestamp.value = parseDateTime(deadlineAt)
  remainingSeconds.value = null
}

function tick(): void {
  now.value = Date.now()
  if (remainingBase !== null) {
    const elapsed = Math.floor((now.value + serverOffsetMs - remainingBaseAt) / 1000)
    remainingSeconds.value = Math.max(0, remainingBase - elapsed)
  } else if (deadlineTimestamp.value !== null) {
    remainingSeconds.value = Math.max(
      0,
      Math.ceil((deadlineTimestamp.value - (now.value + serverOffsetMs)) / 1000),
    )
  } else {
    remainingSeconds.value = null
    return
  }
  if (remainingSeconds.value === 0 && !timeUp.value) {
    timeUp.value = true
    stopTicker()
    void submitNow(true)
  }
}

async function submitNow(auto: boolean): Promise<void> {
  if (!attempt.value || submitting.value || attempt.value.status !== 'doing') return
  submitting.value = true
  submitError.value = ''
  try {
    const saved = await flushAll(true)
    if (!saved && !auto) {
      submitError.value = '仍有答案未保存，请检查网络后点击“重试保存”再提交。'
      return
    }
    if (!saved && auto) {
      submitError.value = '部分答案未能保存，已先为你提交已保存内容；可稍后联系老师。'
    }
    const result = await attemptsApi.submit(attemptId)
    submitResult.value = result
    autoSubmitted.value = auto
    attempt.value = {
      ...attempt.value,
      status: result.attempt.status,
      total_score: result.attempt.total_score,
      full_score: result.attempt.full_score,
      submitted_at: result.attempt.submitted_at,
    }
    confirmOpen.value = false
    submittedOpen.value = true
    stopTicker()
    clearAttemptDraft(attemptId)
    if (auto) ui.warning('考试时间已到，系统已自动提交')
    else ui.success('试卷已提交')
  } catch (err) {
    if (isApiError(err) && err.code === 40910) {
      confirmOpen.value = false
      ui.warning('本次作答已提交，正在打开成绩页')
      await goResult()
      return
    }
    submitError.value = mapError(err)
  } finally {
    submitting.value = false
  }
}

function openConfirm(): void {
  if (!attempt.value || inputLocked.value) return
  submitError.value = ''
  confirmOpen.value = true
}

function retrySave(questionId: number): void {
  saveStates[questionId] = 'pending'
  void saveQuestion(questionId)
}

function retryAutoSubmit(): void {
  void submitNow(true)
}

async function goResult(): Promise<void> {
  await router.push({
    name: 'student-attempt-result',
    params: { id: String(attemptId) },
  })
}

function backToPapers(): void {
  void router.push('/student/papers')
}

async function resyncCachedAnswers(): Promise<void> {
  if (!attempt.value) return
  const targets = questions.value.filter(
    (question) => !isAnswerEmpty(question.type, answers.value[question.id]),
  )
  await Promise.allSettled(
    targets.map(async (question) => {
      try {
        await attemptsApi.saveAnswer(attemptId, question.id, answers.value[question.id])
      } catch (err) {
        if (isApiError(err) && err.code === 40910) lockFromServer()
      }
    }),
  )
}

/** 把作答数据落到页面状态；返回 false 表示已给出错误提示或已跳转成绩页。 */
async function hydrate(
  data: AttemptDetail,
  serverAnswers: Record<string, unknown> | null,
): Promise<boolean> {
  if (data.id !== attemptId) {
    loadError.value = '作答记录与试卷不匹配，请从试卷列表重新进入'
    return false
  }
  if (data.status !== 'doing') {
    await router.replace({
      name: 'student-attempt-result',
      params: { id: String(attemptId) },
    })
    return false
  }
  attempt.value = data
  const initial = buildInitialAnswers(data.questions)
  if (serverAnswers) {
    for (const question of data.questions) {
      const value = serverAnswers[String(question.id)]
      if (value !== undefined) initial[question.id] = value
    }
  }
  answers.value = initial
  for (const question of data.questions) {
    saveStates[question.id] = isAnswerEmpty(question.type, initial[question.id]) ? 'idle' : 'saved'
  }
  currentIndex.value = firstUnansweredIndex()
  persist()
  return true
}

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  attempt.value = null
  answers.value = {}
  remainingBase = null
  deadlineTimestamp.value = null
  if (!Number.isFinite(attemptId) || attemptId <= 0) {
    loadError.value = '作答地址无效'
    loading.value = false
    return
  }
  const studentId = auth.user?.role === 'student' ? auth.user.id : 0
  if (!studentId) {
    loadError.value = '当前账号不是学生，无法作答'
    loading.value = false
    return
  }

  const cached = readAttemptDraft(attemptId)
  try {
    // 服务端是唯一事实来源：进入即拉取已存答案与服务端时钟。
    const data = await attemptsApi.resume(attemptId)
    if (!(await hydrate(data, data.answers))) return
    syncServerClock(data.server_now, data.remaining_seconds, data.deadline_at)
    startTicker()
  } catch (err) {
    if (isApiError(err) && (err.code === 40301 || err.code === 40302)) {
      loadError.value = mapError(err)
      return
    }
    // 断网兜底：草稿仅供还原界面，联网后由自动保存回写服务端。
    try {
      const fallback =
        cached?.attempt ??
        (Number.isFinite(paperId) && paperId > 0 ? await papersApi.startAttempt(paperId) : null)
      if (!fallback) {
        loadError.value = '缺少试卷信息，请从试卷列表进入答题页'
        return
      }
      if (cached && cached.attempt.id === attemptId) {
        if (!(await hydrate(fallback, cached.answers))) return
        syncServerClock(fallback.server_now, fallback.remaining_seconds, fallback.deadline_at)
        startTicker()
        if (targetsHaveAnswers()) void resyncCachedAnswers()
        return
      }
      if (!(await hydrate(fallback, null))) return
      syncServerClock(fallback.server_now, fallback.remaining_seconds, fallback.deadline_at)
      startTicker()
    } catch (fallbackErr) {
      loadError.value = mapError(fallbackErr)
    }
  } finally {
    loading.value = false
  }
}

function targetsHaveAnswers(): boolean {
  return questions.value.some((question) => !isAnswerEmpty(question.type, answers.value[question.id]))
}

function beforeUnload(): void {
  persist()
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  void load()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnload)
  stopTicker()
  for (const questionId of timers.keys()) clearTimer(questionId)
})
</script>

<template>
  <div class="page attempt-page">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">ANSWER SHEET</p>
        <h1 class="page-title">{{ attempt?.paper.title || '答题' }}</h1>
        <p class="page-subtitle">
          <template v-if="attempt">
            {{ attempt.questions.length }} 题 · 满分 {{ attempt.full_score }} 分 ·
            {{ blankMeta?.label }}
          </template>
          <template v-else>正在准备试卷…</template>
        </p>
      </div>
      <AppButton variant="ghost" @click="backToPapers">
        <ArrowLeft :size="15" :stroke-width="1.9" />
        返回试卷
      </AppButton>
    </header>

    <section v-if="loading" class="content-stack" aria-busy="true">
      <div class="panel panel-body">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="8" />
      </div>
    </section>

    <section v-else-if="loadError" class="panel">
      <AppEmpty error title="答题页暂时无法打开" :description="loadError">
        <template #action>
          <AppButton variant="secondary" @click="load">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <template v-else-if="attempt">
      <section v-if="lockedByServer || timeUp" class="locked-banner" role="status">
        <ShieldCheck :size="18" :stroke-width="1.9" aria-hidden="true" />
        <div class="grow">
          <strong>{{ timeUp ? '考试时间已到，试卷已锁定' : '试卷已提交并锁定' }}</strong>
          <p v-if="timeUp && submitError">{{ submitError }}</p>
          <p v-else>所有答案不可再修改。倒计时已停止，可以进入成绩页查看判分结果。</p>
        </div>
        <AppButton v-if="timeUp && submitError" variant="secondary" size="sm" :loading="submitting" @click="retryAutoSubmit">
          重新提交
        </AppButton>
        <AppButton variant="primary" size="sm" @click="goResult">查看成绩</AppButton>
      </section>

      <div class="attempt-layout">
        <main class="attempt-main">
          <section class="attempt-timer panel panel-body" aria-live="polite">
            <div class="timer-block">
              <span class="timer-block__label">
                <Clock3 :size="14" :stroke-width="1.9" />
                剩余时间
              </span>
              <strong
                class="timer-block__value tabular"
                :class="{ 'timer-block__value--urgent': isUrgent, 'timer-block__value--over': isOver }"
              >
                {{ remainingText }}
              </strong>
              <span class="timer-block__deadline">
                截止 {{ deadlineLabel }}（服务端 deadline_at）
              </span>
            </div>

            <div class="timer-progress">
              <span class="timer-progress__text">
                已答 <strong class="tabular">{{ answeredCount }}</strong> /
                {{ questions.length }}
              </span>
              <div class="timer-progress__track" aria-hidden="true">
                <span class="timer-progress__fill" :style="{ width: `${progressPercent}%` }" />
              </div>
            </div>

            <div class="timer-save">
              <AppTag v-if="errorSaveCount > 0" tone="danger" dot>{{ errorSaveCount }} 题未保存</AppTag>
              <AppTag v-else-if="pendingSaveCount > 0" tone="warning" dot>保存中…</AppTag>
              <AppTag v-else tone="success" dot>已自动保存</AppTag>
              <small v-if="lastSavedTime" class="muted text-xs">最近 {{ lastSavedTime }}</small>
            </div>
          </section>

          <AppCard v-if="currentQuestion" class="question-panel" padding="md">
            <header class="question-panel__head">
              <div class="question-panel__title">
                <span class="question-panel__index tabular">
                  第 {{ currentQuestion.seq }} 题
                </span>
                <AppTag :tone="QUESTION_TYPE_META[currentQuestion.type].tone">
                  {{ QUESTION_TYPE_META[currentQuestion.type].label }}
                </AppTag>
                <AppTag tone="neutral">{{ currentQuestion.knowledge_tag }}</AppTag>
                <span class="question-panel__score tabular">{{ currentQuestion.score }} 分</span>
              </div>

              <div class="question-panel__save">
                <span v-if="saveStates[currentQuestion.id] === 'pending'" class="save-chip save-chip--pending">
                  待保存
                </span>
                <span v-else-if="saveStates[currentQuestion.id] === 'saving'" class="save-chip save-chip--pending">
                  保存中…
                </span>
                <span v-else-if="saveStates[currentQuestion.id] === 'saved'" class="save-chip save-chip--ok">
                  <CheckCircle2 :size="13" :stroke-width="2" />
                  已保存
                </span>
                <span v-else-if="saveStates[currentQuestion.id] === 'error'" class="save-chip save-chip--error">
                  <AlertCircle :size="13" :stroke-width="2" />
                  未保存
                  <button class="save-chip__retry" type="button" @click="retrySave(currentQuestion.id)">
                    重试
                  </button>
                </span>
              </div>
            </header>

            <p class="question-panel__stem">{{ currentQuestion.stem }}</p>

            <QuestionAnswerInput
              :question="currentQuestion"
              :model-value="answers[currentQuestion.id]"
              :disabled="submitting"
              :locked="inputLocked"
              @update:model-value="handleAnswerChange(currentQuestion.id, $event)"
              @blur="handleAnswerBlur(currentQuestion.id)"
            />

            <p v-if="saveErrors[currentQuestion.id]" class="question-panel__save-error" role="alert">
              <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
              {{ saveErrors[currentQuestion.id] }}
            </p>

            <footer class="question-panel__foot">
              <AppButton
                variant="ghost"
                :disabled="currentIndex === 0 || submitting"
                @click="prevQuestion"
              >
                <ArrowLeft :size="15" :stroke-width="1.9" />
                上一题
              </AppButton>
              <span class="muted text-xs tabular">
                {{ currentIndex + 1 }} / {{ questions.length }}
              </span>
              <AppButton
                v-if="currentIndex < questions.length - 1"
                variant="secondary"
                :disabled="submitting"
                @click="nextQuestion"
              >
                下一题
                <ArrowRight :size="15" :stroke-width="1.9" />
              </AppButton>
              <AppButton
                v-else
                variant="primary"
                :disabled="inputLocked || submitting"
                @click="openConfirm"
              >
                <Send :size="15" :stroke-width="1.9" />
                提交试卷
              </AppButton>
            </footer>
          </AppCard>

          <p v-if="submitError && !confirmOpen" class="form-error" role="alert">
            <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ submitError }}</span>
          </p>
        </main>

        <aside class="attempt-side">
          <div class="panel panel-body side-card">
            <div class="side-card__head">
              <h2 class="section-title">答题卡</h2>
              <AppTag tone="primary" dot>{{ answeredCount }} / {{ questions.length }}</AppTag>
            </div>

            <p v-if="pendingSaveCount || errorSaveCount" class="side-card__save-note">
              <AlertCircle v-if="errorSaveCount" :size="13" :stroke-width="2" />
              <Clock3 v-else :size="13" :stroke-width="2" />
              {{ errorSaveCount ? `${errorSaveCount} 题未保存` : `正在保存 ${pendingSaveCount} 题…` }}
            </p>
            <p v-else class="side-card__save-note side-card__save-note--ok">
              <CheckCircle2 :size="13" :stroke-width="2" />
              答案已自动保存
            </p>

            <ol class="question-nav">
              <li v-for="(question, index) in questions" :key="question.id">
                <button
                  class="question-nav__item"
                  :class="{
                    'question-nav__item--current': index === currentIndex,
                    'question-nav__item--answered': !isAnswerEmpty(question.type, answers[question.id]),
                    'question-nav__item--error': saveStates[question.id] === 'error',
                  }"
                  type="button"
                  :aria-label="`第 ${question.seq} 题`"
                  @click="goToQuestion(index)"
                >
                  {{ question.seq }}
                </button>
              </li>
            </ol>

            <dl class="save-legend">
              <div>
                <dt><span class="legend-dot legend-dot--answered" />已作答</dt>
                <dd class="tabular">{{ answeredCount }}</dd>
              </div>
              <div>
                <dt><span class="legend-dot legend-dot--todo" />未作答</dt>
                <dd class="tabular">{{ questions.length - answeredCount }}</dd>
              </div>
            </dl>

            <AppButton
              variant="primary"
              block
              :disabled="inputLocked || submitting"
              :loading="submitting"
              @click="openConfirm"
            >
              <Send v-if="!submitting" :size="15" :stroke-width="1.9" />
              提交试卷
            </AppButton>
            <p class="side-card__note">提交前会自动保存；提交后试卷锁定，无法修改答案。</p>
          </div>
        </aside>
      </div>
    </template>

    <AppModal
      v-model="confirmOpen"
      title="确认提交试卷？"
      description="提交后本次作答立即判分并锁定，所有答案不可再修改。"
      confirm-text="提交试卷"
      cancel-text="继续作答"
      :confirm-loading="submitting"
      :close-on-overlay="!submitting"
      @confirm="submitNow(false)"
    >
      <div class="confirm-body">
        <dl class="confirm-stats">
          <div>
            <dt>已作答</dt>
            <dd class="tabular">{{ answeredCount }} / {{ questions.length }}</dd>
          </div>
          <div>
            <dt>未作答</dt>
            <dd class="tabular">{{ unansweredQuestions.length }}</dd>
          </div>
          <div>
            <dt>未保存</dt>
            <dd class="tabular">{{ errorSaveCount }}</dd>
          </div>
        </dl>

        <div v-if="unansweredQuestions.length > 0" class="confirm-warn">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <div>
            <strong>还有 {{ unansweredQuestions.length }} 题未作答</strong>
            <p>
              <template v-for="(question, index) in unansweredQuestions.slice(0, 12)" :key="question.id">
                第 {{ question.seq }} 题<template v-if="index < Math.min(unansweredQuestions.length, 12) - 1">、</template>
              </template>
              <template v-if="unansweredQuestions.length > 12">…</template>
              提交后将按未作答计 0 分。
            </p>
          </div>
        </div>

        <p v-if="submitError" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ submitError }}</span>
        </p>
      </div>
    </AppModal>

    <AppModal
      :model-value="submittedOpen"
      :title="autoSubmitted ? '考试时间已到，试卷已自动提交' : '试卷已提交'"
      :description="pendingReviewNotice"
      confirm-text="查看成绩"
      cancel-text="留在本页"
      @update:model-value="submittedOpen = $event"
      @confirm="goResult"
    >
      <div class="submitted-body">
        <span class="submitted-icon" aria-hidden="true">
          <ShieldCheck :size="30" :stroke-width="1.7" />
        </span>
        <dl v-if="submitResult" class="submitted-stats">
          <div>
            <dt>已保存答案</dt>
            <dd class="tabular">{{ submitResult.answers.filter((item) => item.answer_record_id !== null).length }} 题</dd>
          </div>
          <div>
            <dt>判分耗时</dt>
            <dd class="tabular">{{ submitResult.grading_ms ?? '—' }} ms</dd>
          </div>
          <div>
            <dt>待复核</dt>
            <dd class="tabular">{{ submitResult.attempt.needs_review ? '是' : '否' }}</dd>
          </div>
        </dl>
        <p class="muted text-sm">此刻起答案不可修改，关闭本页也会保留已提交成绩。</p>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.locked-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  margin-bottom: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
  border: 1px solid color-mix(in srgb, var(--color-warning) 32%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  color: var(--color-warning);
}

.locked-banner strong {
  font-size: var(--fs-sm);
}

.locked-banner p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.attempt-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 288px;
  gap: var(--sp-5);
  align-items: start;
}

.attempt-main {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  min-width: 0;
}

.attempt-timer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
}

.timer-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.timer-block__label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.timer-block__value {
  font-family: var(--font-mono);
  font-size: var(--fs-2xl);
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 0.02em;
}

.timer-block__value--urgent {
  color: var(--color-danger);
}

.timer-block__deadline {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.timer-progress {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  min-width: 180px;
}


.timer-progress__text {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.timer-progress__text strong {
  color: var(--color-primary);
}

.timer-progress__track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-surface-alt);
}

.timer-progress__fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--color-primary);
  transition: width 220ms ease-out;
}

.timer-save {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.question-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.question-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.question-panel__title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.question-panel__index {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--color-text-muted);
}

.question-panel__score {
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.question-panel__save {
  display: flex;
  align-items: center;
  min-height: 22px;
}

.save-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  font-weight: 600;
}

.save-chip--ok {
  color: var(--color-success);
}

.save-chip--pending {
  color: var(--color-text-muted);
}

.save-chip__retry {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.save-chip--error {
  color: var(--color-danger);
}

.save-chip--error::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--color-danger);
}

.question-panel__stem {
  font-size: var(--fs-lg);
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.question-panel__save-error {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  color: var(--color-danger);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.question-panel__save-error svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.question-panel__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.attempt-side {
  position: sticky;
  top: calc(var(--topbar-h) + var(--sp-4));
}

.side-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.side-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
}

.side-card__save-note {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--color-warning);
  font-size: var(--fs-xs);
}

.side-card__save-note--ok {
  color: var(--color-success);
}

.question-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--sp-2);
}

.question-nav__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 1;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
}

.question-nav__item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.question-nav__item--answered {
  border-color: color-mix(in srgb, var(--color-primary) 32%, var(--color-border));
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}

.question-nav__item--current {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: 600;
}

.question-nav__item--error::after {
  content: '';
  position: absolute;
  top: 2px;
  right: 2px;
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: var(--color-danger);
}

.save-legend {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding-top: var(--sp-2);
  border-top: 1px dashed var(--color-border);
}

.save-legend div {
  display: flex;
  align-items: center;
  gap: 5px;
}

.save-legend dt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.save-legend dd {
  font-size: var(--fs-xs);
  font-weight: 600;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
}

.legend-dot--answered {
  background: var(--color-primary);
}

.legend-dot--todo {
  background: var(--color-border-strong);
}

.side-card__note {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.confirm-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.confirm-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-2);
}

.confirm-stats div {
  padding: var(--sp-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.confirm-stats dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.confirm-stats dd {
  margin-top: 2px;
  font-size: var(--fs-lg);
  font-weight: 700;
}

.confirm-warn {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 7%, var(--color-surface));
  color: var(--color-warning);
}

.confirm-warn svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.confirm-warn strong {
  font-size: var(--fs-sm);
}

.confirm-warn p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.submitted-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-4);
  padding: var(--sp-2) 0 0;
}

.submitted-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 999px;
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
}

.submitted-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-5);
  width: 100%;
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.submitted-stats dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.submitted-stats dd {
  margin-top: 2px;
  font-size: var(--fs-sm);
  font-weight: 600;
  text-align: center;
}

@media (max-width: 960px) {
  .attempt-layout {
    grid-template-columns: 1fr;
  }

  .attempt-side {
    position: static;
  }
}

@media (max-width: 560px) {
  .attempt-timer {
    align-items: flex-start;
    flex-direction: column;
  }

  .timer-save {
    align-items: flex-start;
  }

  .question-nav {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}
</style>
