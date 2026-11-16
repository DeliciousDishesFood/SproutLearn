<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Sparkles, X } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import { attemptsApi, type AskSproutHistoryMessage, type AskSproutSource } from '@/api/attempts'
import { isApiError, toUserMessage } from '@/api/client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: AskSproutSource[]
}

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
const inputEl = ref<HTMLTextAreaElement | null>(null)
let cooldownTimer: number | null = null

const canSend = computed(
  () => !sending.value && cooldown.value === 0 && input.value.trim().length > 0,
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
  input.value = props.selectedText ? `关于我选中的“${props.selectedText}”，` : ''
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
  emit('clear-selection')
  inputEl.value?.focus()
}

function historyPayload(): AskSproutHistoryMessage[] {
  return messages.value
    .filter((item) => item.content.trim())
    .slice(-6)
    .map((item) => ({ role: item.role, content: item.content }))
}

async function send(): Promise<void> {
  if (!props.questionId || !canSend.value) return
  const message = input.value.trim()
  if (!message) return
  sending.value = true
  errorText.value = ''
  messages.value = [...messages.value, { role: 'user', content: message }]
  input.value = ''
  try {
    const result = await attemptsApi.ask(props.attemptId, {
      question_id: props.questionId,
      selected_text: chip.value.trim(),
      message,
      history: historyPayload().slice(0, -1),
    })
    messages.value = [
      ...messages.value,
      { role: 'assistant', content: result.answer, sources: result.sources ?? [] },
    ]
  } catch (error) {
    if (isApiError(error) && error.code === 42901) {
      errorText.value = '问得太快，3 秒后再试'
      startCooldown(3)
    } else if (isApiError(error) && error.code === 50301) {
      errorText.value = '小芽暂时不可用，请稍后重试'
    } else {
      errorText.value = toUserMessage(error)
    }
    // 失败时保留用户消息，允许直接重试
    input.value = message
  } finally {
    sending.value = false
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('close')
    return
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}
</script>

<template>
  <Teleport to="body">
    <template v-if="open">
      <div class="ask-backdrop" @mousedown.self="emit('close')" />
      <aside
        class="ask-panel"
        role="dialog"
        aria-modal="true"
        aria-label="问问小芽"
        @keydown="onKeydown"
      >
        <header class="ask-head">
          <span class="ask-title"><Sparkles :size="17" aria-hidden="true" />问问小芽</span>
          <button class="icon-btn" type="button" aria-label="关闭" @click="emit('close')">
            <X :size="16" />
          </button>
        </header>

        <div v-if="chip" class="ask-chip">
          <span class="ask-chip__text">{{ chip }}</span>
          <button class="ask-chip__x" type="button" aria-label="清除选中文案" @click="clearChip">
            ×
          </button>
        </div>

        <div class="ask-thread">
          <p v-if="messages.length === 0" class="notice">
            选中题干或选项中的文字，可以围绕它向小芽提问。回答只作练习参考，不计入成绩。
          </p>
          <div
            v-for="(item, index) in messages"
            :key="index"
            class="ask-msg"
            :class="item.role === 'user' ? 'ask-msg--user' : 'ask-msg--bot'"
          >
            {{ item.content }}
            <span v-if="item.role === 'assistant' && item.sources && item.sources.length" class="ask-src">
              来源：<span v-for="source in item.sources" :key="source.doc_id">{{ source.doc_name }}</span>
            </span>
          </div>
          <p v-if="sending" class="tertiary small">小芽正在思考…</p>
          <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>
        </div>

        <form class="ask-input" @submit.prevent="send">
          <textarea
            ref="inputEl"
            v-model="input"
            rows="2"
            placeholder="继续追问…"
            aria-label="向小芽提问"
            :disabled="sending"
          />
          <BaseButton
            variant="primary"
            type="submit"
            :loading="sending"
            :disabled="!canSend"
          >
            {{ cooldown > 0 ? `${cooldown}s` : '发送' }}
          </BaseButton>
        </form>
        <p class="ask-note">回答仅作练习参考，不会计入成绩。</p>
      </aside>
    </template>
  </Teleport>
</template>
