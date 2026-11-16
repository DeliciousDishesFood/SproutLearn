<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sparkles, Sprout } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import AskSproutPanel from '@/components/business/AskSproutPanel.vue'
import { attemptsApi } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'
import type { AttemptQuestion, AttemptResume, QuestionOption } from '@/api/contract'
import { QUESTION_TYPE_LABEL, formatAnswer } from '@/utils/format'
import { useAskSproutSelection } from '@/composables/useAskSproutSelection'
import { useCountdown } from '@/composables/useCountdown'
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
const pendingSaves = new Set<number>()
const inflight = new Map<number, Promise<void>>()
const versions = new Map<number, number>()
const timers = new Map<number, number>()

const askEnabled = computed(
  () => attempt.value?.paper.kind === 'practice' && attempt.value?.status === 'doing',
)
const { state: selection, clear: clearSelection } = useAskSproutSelection(qScope, askEnabled)

const serverNow = computed(() => attempt.value?.server_now ?? null)
const remainingSeconds = computed(() => attempt.value?.remaining_seconds ?? null)
const { label: timerLabel, expired, warning } = useCountdown(serverNow, remainingSeconds)

const questions = computed<AttemptQuestion[]>(() => attempt.value?.questions ?? [])
const currentQuestion = computed<AttemptQuestion | null>(() => questions.value[currentIndex.value] ?? null)
const answeredCount = computed(
  () => questions.value.filter((question) => isAnswered(question.id)).length,
)
const progressPercent = computed(() =>
  questions.value.length ? Math.round((answeredCount.value / questions.value.length) * 100) : 0,
)

function answerValue(questionId: number): unknown {
  return answers[String(questionId)]
}

function isAnswered(questionId: number): boolean {
  const value = answerValue(questionId)
  if (Array.isArray(value)) return value.length > 0
  return value !== undefined && value !== null && value !== ''
}

function isChosen(question: AttemptQuestion, option: QuestionOption): boolean {
  const value = answerValue(question.id)
  if (question.type === 'multiple') {
    return Array.isArray(value) && value.map(String).includes(option.key)
  }
  return String(value ?? '') === option.key
}

function choose(question: AttemptQuestion, option: QuestionOption): void {
  if (expired.value || attempt.value?.status !== 'doing') return
  if (question.type === 'multiple') {
    const current = Array.isArray(answerValue(question.id))
      ? (answerValue(question.id) as string[]).map(String)
      : []
    const next = current.includes(option.key)
      ? current.filter((item) => item !== option.key)
      : [...current, option.key]
    setAnswer(question.id, next)
  } else {
    setAnswer(question.id, option.key)
  }
}

function chooseJudge(question: AttemptQuestion, value: boolean): void {
  if (expired.value || attempt.value?.status !== 'doing') return
  setAnswer(question.id, value)
}

function setBlank(question: AttemptQuestion, event: Event): void {
  if (expired.value || attempt.value?.status !== 'doing') return
  setAnswer(question.id, (event.target as HTMLTextAreaElement).value)
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

function goTo(index: number): void {
  if (index < 0 || index >= questions.value.length) return
  currentIndex.value = index
  clearSelection()
  askOpen.value = false
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

async function submit(): Promise<void> {
  if (submitting.value) return
  const unanswered = questions.value.length - answeredCount.value
  const message =
    unanswered > 0
      ? `还有 ${unanswered} 道题未作答，提交后不可修改。确定提交吗？`
      : '提交后试卷锁定，不可修改答案。确定提交吗？'
  if (!window.confirm(message)) return
  submitting.value = true
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

async function exit(): Promise<void> {
  if (!window.confirm('退出后已保存的答案会保留，未保存的修改将丢失。确定退出吗？')) return
  try {
    await flushSaves()
  } catch {
    if (!window.confirm('仍有答案未保存成功，仍要退出吗？')) return
  }
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
})
</script>

<template>
  <div class="practice-body">
    <header class="topbar">
      <RouterLink class="brand" to="/student">
        <span class="brand__mark" aria-hidden="true"><Sprout :size="19" /></span>
        <span class="brand__text">青芽 <em>SproutLearn</em></span>
      </RouterLink>
      <div v-if="attempt" class="practice-title">
        <strong>{{ attempt.paper.title }}</strong>
        <span>第 {{ currentIndex + 1 }} 题 / 共 {{ questions.length }} 题</span>
      </div>
      <div class="top-actions">
        <span class="timer" :class="{ 'is-danger': warning || expired }">{{ timerLabel }}</span>
        <button class="btn btn--ghost" type="button" @click="exit">退出</button>
      </div>
    </header>

    <main class="practice">
      <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
      <p v-if="loading" class="loading-line">正在恢复作答…</p>
      <p v-if="attempt && expired" class="notice notice--warn">
        本次作答已截止，输入已锁定；你可以提交已保存的答案，或退出作答。
      </p>

      <template v-if="attempt && currentQuestion">
        <div class="practice-head">
          <div>
            <p class="eyebrow">
              {{ attempt.paper.kind === 'practice' ? 'PRACTICE' : attempt.paper.kind === 'homework' ? 'HOMEWORK' : 'EXAM' }}
              · {{ attempt.paper.title }}
            </p>
            <h1>{{ attempt.paper.title }}</h1>
          </div>
          <div class="progress" aria-label="答题进度">
            <span class="progress__bar"><i :style="{ width: `${progressPercent}%` }" /></span>
            <span class="progress__text">已答 {{ answeredCount }} / {{ questions.length }}</span>
          </div>
        </div>

        <div class="practice-grid">
          <section class="q-card">
            <div class="q-meta">
              <span class="q-index">第 {{ currentQuestion.seq }} 题</span>
              <span class="tag">{{ QUESTION_TYPE_LABEL[currentQuestion.type] }}</span>
              <span class="tag">{{ currentQuestion.knowledge_tag }}</span>
              <span class="tag">{{ currentQuestion.score }} 分</span>
              <span class="tag">
                保存：{{ saveState === 'saving' ? '保存中…' : saveState === 'error' ? '保存失败，重试' : saveState === 'saved' ? '已保存' : '自动保存' }}
              </span>
            </div>

            <div ref="qScope" class="q-scope" tabindex="-1">
              <p class="q-stem">{{ currentQuestion.stem }}</p>

              <div v-if="currentQuestion.type === 'judge'" class="q-options" role="radiogroup">
                <button
                  class="option"
                  :class="{ 'is-selected': answerValue(currentQuestion.id) === true }"
                  type="button"
                  role="radio"
                  :aria-checked="answerValue(currentQuestion.id) === true"
                  :disabled="expired"
                  @click="chooseJudge(currentQuestion, true)"
                >
                  <span class="option__key">✓</span><span class="option__text">正确</span>
                </button>
                <button
                  class="option"
                  :class="{ 'is-selected': answerValue(currentQuestion.id) === false }"
                  type="button"
                  role="radio"
                  :aria-checked="answerValue(currentQuestion.id) === false"
                  :disabled="expired"
                  @click="chooseJudge(currentQuestion, false)"
                >
                  <span class="option__key">✕</span><span class="option__text">错误</span>
                </button>
              </div>

              <div
                v-else-if="currentQuestion.options && currentQuestion.options.length"
                class="q-options"
                :role="currentQuestion.type === 'multiple' ? 'group' : 'radiogroup'"
              >
                <button
                  v-for="option in currentQuestion.options"
                  :key="option.key"
                  class="option"
                  :class="{ 'is-selected': isChosen(currentQuestion, option) }"
                  type="button"
                  :role="currentQuestion.type === 'multiple' ? 'checkbox' : 'radio'"
                  :aria-checked="isChosen(currentQuestion, option)"
                  :disabled="expired"
                  @click="choose(currentQuestion, option)"
                >
                  <span class="option__key">{{ option.key }}</span>
                  <span class="option__text">{{ option.text }}</span>
                </button>
              </div>

              <div v-else class="blank-input">
                <label class="field">
                  <span>你的答案</span>
                  <textarea
                    :value="answerValue(currentQuestion.id) === undefined ? '' : String(answerValue(currentQuestion.id))"
                    class="input"
                    rows="3"
                    placeholder="在这里填写答案"
                    :disabled="expired"
                    @input="setBlank(currentQuestion, $event)"
                  />
                </label>
              </div>
            </div>

            <div class="q-foot">
              <button class="btn" type="button" :disabled="currentIndex === 0" @click="goTo(currentIndex - 1)">
                上一题
              </button>
              <span class="q-foot__count">{{ currentIndex + 1 }} / {{ questions.length }}</span>
              <button
                class="btn btn--primary"
                type="button"
                :disabled="currentIndex >= questions.length - 1"
                @click="goTo(currentIndex + 1)"
              >
                下一题
              </button>
            </div>
          </section>

          <aside class="side-card">
            <header class="panel__head">
              <h2>答题卡</h2>
              <span class="panel__meta">{{ saveState === 'saved' ? '已自动保存' : '自动保存已开启' }}</span>
            </header>
            <div class="sheet" aria-label="题号">
              <button
                v-for="(question, index) in questions"
                :key="question.id"
                class="sheet__dot"
                :class="{
                  'is-done': isAnswered(question.id) && index !== currentIndex,
                  'is-current': index === currentIndex,
                }"
                type="button"
                :aria-current="index === currentIndex ? 'step' : undefined"
                @click="goTo(index)"
              >
                {{ index + 1 }}
              </button>
            </div>
            <div class="legend">
              <span><i class="legend__dot is-done" />已答</span>
              <span><i class="legend__dot is-current" />当前</span>
              <span><i class="legend__dot" />未答</span>
            </div>
            <BaseButton variant="primary" block :loading="submitting" @click="submit">提交试卷</BaseButton>
            <p class="side-note">
              提交前会自动保存；提交后试卷锁定，无法修改答案。
              <template v-if="attempt.paper.kind === 'practice'">练习中可选中题干或选项，问问小芽。</template>
            </p>
          </aside>
        </div>
      </template>

      <p v-else-if="!loading" class="empty-block">
        {{ errorText || '没有可作答的题目。' }}
      </p>
    </main>

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
  </div>
</template>
