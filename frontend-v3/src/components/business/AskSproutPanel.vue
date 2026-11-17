<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Send, X } from 'lucide-vue-next'
import xiaoyaBot from '@/assets/brand/xiaoya-bot.png'
import { attemptsApi, type AskSproutHistoryMessage, type AskSproutSource } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'
import { useFocusTrap } from '@/composables/useFocusTrap'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: AskSproutSource[]
  failed?: boolean
}

const QUICK_PROMPTS = ['这题考什么？', '为什么这样选？', '帮我梳理思路']

const props = defineProps<{
  open: boolean
  attemptId: number
  questionId: number | null
  selectedText: string
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'clear-selection'): void
}>()

const messages = ref<ChatMessage[]>([])
const input = ref('')
const chip = ref('')
const sending = ref(false)
const errorText = ref('')
const cooldown = ref(0)
const lastFailed = ref<{ message: string; chip: string } | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const panelEl = ref<HTMLElement | null>(null)
const threadEl = ref<HTMLElement | null>(null)
let cooldownTimer: number | null = null
let prefillPrefix = ''

// 侧滑抽屉与弹窗共用焦点陷阱：焦点圈定、Escape、关闭恢复、锁定滚动。
useFocusTrap({
  active: () => props.open,
  container: panelEl,
  onEscape: () => emit('close'),
  initialFocus: () => inputEl.value,
})

const canSend = computed(
  () =>
    Boolean(props.questionId) &&
    !sending.value &&
    cooldown.value === 0 &&
    input.value.trim().length > 0,
)

function startCooldown(seconds: number): void {
  cooldown.value = seconds
  if (cooldownTimer !== null) window.clearInterval(cooldownTimer)
  cooldownTimer = window.setInterval(() => {
    cooldown.value = Math.max(0, cooldown.value - 1)
    if (cooldown.value === 0 && cooldownTimer !== null) {
      window.clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

function prefill(): void {
  chip.value = props.selectedText
  prefillPrefix = props.selectedText ? `关于我选中的“${props.selectedText}”，` : ''
  input.value = prefillPrefix
  void nextTick(() => {
    inputEl.value?.focus()
    const length = input.value.length
    inputEl.value?.setSelectionRange(length, length)
  })
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      errorText.value = ''
      prefill()
    }
  },
  { immediate: true },
)

watch(
  () => props.selectedText,
  (text) => {
    if (props.open) chip.value = text
  },
)

function clearChip(): void {
  chip.value = ''
  if (prefillPrefix && input.value.startsWith(prefillPrefix)) {
    input.value = input.value.slice(prefillPrefix.length)
  }
  prefillPrefix = ''
  emit('clear-selection')
  inputEl.value?.focus()
}

function fillPrompt(text: string): void {
  input.value = text
  void nextTick(() => {
    inputEl.value?.focus()
    inputEl.value?.setSelectionRange(text.length, text.length)
  })
}

const threadSignature = computed(() => `${messages.value.length}:${sending.value}`)

watch(threadSignature, () => {
  void nextTick(() => {
    const el = threadEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
})

function markLastFailed(message: string): void {
  const next = [...messages.value]
  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index].role === 'user' && next[index].content === message) {
      next[index] = { ...next[index], failed: true }
      break
    }
  }
  messages.value = next
}

/** 从当前对话构造历史；始终排除最后一条待发送的用户消息，避免重试重复。 */
function historyPayload(): AskSproutHistoryMessage[] {
  return messages.value
    .slice(0, -1)
    .filter((item) => item.content.trim())
    .slice(-6)
    .map((item) => ({ role: item.role, content: item.content }))
}

async function request(message: string, chipText: string): Promise<void> {
  if (!props.questionId) return
  sending.value = true
  errorText.value = ''
  try {
    const result = await attemptsApi.ask(props.attemptId, {
      question_id: props.questionId,
      selected_text: chipText,
      message,
      history: historyPayload(),
    })
    messages.value = [
      ...messages.value,
      { role: 'assistant', content: result.answer, sources: result.sources ?? [] },
    ]
    lastFailed.value = null
  } catch (error) {
    markLastFailed(message)
    lastFailed.value = { message, chip: chipText }
    if (isApiError(error) && error.code === 42901) {
      errorText.value = '问得太快，请稍后再试'
      startCooldown(3)
    } else if (isApiError(error) && error.code === 50301) {
      errorText.value = '小芽暂时不可用，请稍后重试'
    } else {
      errorText.value = toUserMessage(error)
    }
  } finally {
    sending.value = false
  }
}

async function submit(): Promise<void> {
  if (!canSend.value) return
  const message = input.value.trim()
  if (!message) return
  const chipText = chip.value.trim()
  messages.value = [...messages.value, { role: 'user', content: message }]
  input.value = ''
  prefillPrefix = ''
  lastFailed.value = null
  await request(message, chipText)
}

/** 原地重试：复用失败消息，不再次插入用户气泡。 */
async function retry(): Promise<void> {
  if (!lastFailed.value || sending.value || cooldown.value > 0) return
  await request(lastFailed.value.message, lastFailed.value.chip)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void submit()
  }
}

function closePanel(): void {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <template v-if="open">
      <div class="ask-backdrop" @mousedown.self="closePanel" />
      <aside
        ref="panelEl"
        class="ask-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ask-title"
      >
        <header class="ask-head">
          <div class="ask-id">
            <span class="ask-avatar">
              <img :src="xiaoyaBot" alt="" />
              <i class="ask-avatar__dot" aria-hidden="true" />
            </span>
            <div class="ask-id__text">
              <p id="ask-title" class="ask-id__title">问问小芽</p>
              <p class="ask-id__sub">围绕当前题目追问</p>
            </div>
          </div>
          <button class="ask-close" type="button" aria-label="关闭问问小芽" @click="closePanel">
            <X :size="18" aria-hidden="true" />
          </button>
        </header>

        <div v-if="chip" class="ask-chip">
          <span class="ask-chip__text">{{ chip }}</span>
          <button class="ask-chip__x" type="button" aria-label="清除选中文案" @click="clearChip">
            <X :size="13" aria-hidden="true" />
          </button>
        </div>

        <div ref="threadEl" class="ask-thread">
          <div v-if="messages.length === 0" class="ask-empty">
            <img class="ask-empty__avatar" :src="xiaoyaBot" alt="" />
            <p class="ask-empty__text">选中题干或选项，也可以直接提问。</p>
            <div class="ask-quick" role="group" aria-label="快捷提问">
              <button
                v-for="prompt in QUICK_PROMPTS"
                :key="prompt"
                class="ask-quick__chip"
                type="button"
                @click="fillPrompt(prompt)"
              >
                {{ prompt }}
              </button>
            </div>
            <p class="ask-empty__note">回答仅作练习参考，不计入成绩。</p>
          </div>

          <div
            v-for="(item, index) in messages"
            :key="index"
            class="ask-msg"
            :class="[
              item.role === 'user' ? 'ask-msg--user' : 'ask-msg--bot',
              item.failed ? 'ask-msg--failed' : '',
            ]"
          >
            <p class="ask-msg__text">{{ item.content }}</p>
            <div
              v-if="item.role === 'assistant' && item.sources && item.sources.length"
              class="ask-src"
            >
              <span class="ask-src__label">来源</span>
              <span v-for="source in item.sources" :key="source.doc_id" class="ask-src__tag">
                {{ source.doc_name }}
              </span>
            </div>
          </div>

          <div v-if="sending" class="ask-thinking" role="status">
            <span class="ask-thinking__text">小芽正在思考…</span>
            <span class="ask-thinking__line" aria-hidden="true" />
            <span class="ask-thinking__line ask-thinking__line--short" aria-hidden="true" />
          </div>

          <div v-if="errorText" class="ask-error" role="alert">
            <p class="ask-error__text">{{ errorText }}</p>
            <button
              v-if="lastFailed"
              class="ask-error__retry"
              type="button"
              :disabled="sending || cooldown > 0"
              @click="retry"
            >
              {{ cooldown > 0 ? `${cooldown}s 后重试` : '重试' }}
            </button>
          </div>
        </div>

        <form class="ask-compose" @submit.prevent="submit">
          <div class="ask-compose__box">
            <textarea
              ref="inputEl"
              v-model="input"
              class="ask-compose__input"
              rows="2"
              placeholder="围绕这道题追问小芽…"
              aria-label="向小芽提问"
              :disabled="sending"
              @keydown="onKeydown"
            />
            <button
              class="ask-send"
              type="submit"
              :disabled="!canSend"
              :aria-label="cooldown > 0 ? `冷却中，${cooldown} 秒后可发送` : '发送'"
            >
              <span v-if="cooldown > 0" class="ask-send__count">{{ cooldown }}s</span>
              <Send v-else :size="16" aria-hidden="true" />
            </button>
          </div>
          <p class="ask-note">回答仅作练习参考，不会计入成绩。</p>
        </form>
      </aside>
    </template>
  </Teleport>
</template>
