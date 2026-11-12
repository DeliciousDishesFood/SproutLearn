<!-- 金句打字机：30ms/字逐字显示，点击换一句；接口失败静默回落本地句池。 -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Quote, RefreshCw } from 'lucide-vue-next'
import { quotesApi } from '@/api/quotes'
import type { QuoteResult } from '@/api/types'

const props = withDefaults(
  defineProps<{
    type?: string
  }>(),
  {
    type: '',
  },
)

const CHAR_INTERVAL_MS = 30

/** 本地兜底 20 句：接口不可用时仍能正常显示，不向用户报错。 */
const LOCAL_QUOTES: Array<Pick<QuoteResult, 'text' | 'from'>> = [
  { text: '学而不思则罔，思而不学则殆。', from: '《论语》' },
  { text: '知之者不如好之者，好之者不如乐之者。', from: '《论语》' },
  { text: '不积跬步，无以至千里。', from: '荀子' },
  { text: '业精于勤，荒于嬉。', from: '韩愈' },
  { text: '读书百遍，而义自见。', from: '《三国志》' },
  { text: '敏而好学，不耻下问。', from: '《论语》' },
  { text: '纸上得来终觉浅，绝知此事要躬行。', from: '陆游' },
  { text: '问渠那得清如许？为有源头活水来。', from: '朱熹' },
  { text: '黑发不知勤学早，白首方悔读书迟。', from: '颜真卿' },
  { text: '少壮不努力，老大徒伤悲。', from: '《长歌行》' },
  { text: '会当凌绝顶，一览众山小。', from: '杜甫' },
  { text: '长风破浪会有时，直挂云帆济沧海。', from: '李白' },
  { text: '锲而不舍，金石可镂。', from: '荀子' },
  { text: '博学之，审问之，慎思之，明辨之，笃行之。', from: '《中庸》' },
  { text: '三人行，必有我师焉。', from: '《论语》' },
  { text: '温故而知新，可以为师矣。', from: '《论语》' },
  { text: '读书破万卷，下笔如有神。', from: '杜甫' },
  { text: '千里之行，始于足下。', from: '《道德经》' },
  { text: '天行健，君子以自强不息。', from: '《周易》' },
  { text: '路漫漫其修远兮，吾将上下而求索。', from: '屈原' },
]

const current = ref<QuoteResult>({
  text: LOCAL_QUOTES[0].text,
  from: LOCAL_QUOTES[0].from,
  source: 'local',
})
const shown = ref('')
const switching = ref(false)

let timer: number | null = null
let requestSeq = 0
let localIndex = 0

const typing = computed(() => shown.value.length < current.value.text.length)
const shownText = computed(() => shown.value)

function stopTyping(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function play(text: string): void {
  stopTyping()
  shown.value = ''
  const chars = Array.from(text)
  if (chars.length === 0) return
  let cursor = 0
  timer = window.setInterval(() => {
    cursor += 1
    shown.value = chars.slice(0, cursor).join('')
    if (cursor >= chars.length) stopTyping()
  }, CHAR_INTERVAL_MS)
}

function applyQuote(quote: Pick<QuoteResult, 'text' | 'from' | 'source'>): void {
  current.value = { text: quote.text, from: quote.from, source: quote.source }
  play(quote.text)
}

function applyLocalNext(): void {
  localIndex = (localIndex + 1) % LOCAL_QUOTES.length
  const quote = LOCAL_QUOTES[localIndex]
  applyQuote({ ...quote, source: 'local' })
}

async function fetchQuote(manual: boolean): Promise<void> {
  if (manual) switching.value = true
  const seq = ++requestSeq
  try {
    const result = await quotesApi.random(props.type || undefined)
    if (seq !== requestSeq) return
    if (!result || typeof result.text !== 'string' || result.text.trim() === '') {
      if (manual) applyLocalNext()
      return
    }
    if (manual && result.text.trim() === current.value.text.trim()) {
      // 后端本地句池可能连续命中同一句；手动点击时保证一定换一句。
      applyLocalNext()
      return
    }
    applyQuote(result)
  } catch {
    // 接口失败不报错：保持当前句子或切到下一句本地句。
    if (manual && seq === requestSeq) applyLocalNext()
  } finally {
    if (seq === requestSeq) switching.value = false
  }
}

function switchQuote(): void {
  if (switching.value) return
  void fetchQuote(true)
}

onMounted(() => {
  play(current.value.text)
  void fetchQuote(false)
})

onBeforeUnmount(() => {
  stopTyping()
  requestSeq += 1
})
</script>

<template>
  <button
    class="quote-card"
    type="button"
    aria-label="换一句金句"
    :aria-busy="switching"
    @click="switchQuote"
  >
    <span class="quote-card__mark" aria-hidden="true">
      <Quote :size="18" :stroke-width="1.8" />
    </span>

    <span class="quote-card__body">
      <span class="quote-card__text" :class="{ 'quote-card__text--typing': typing }">
        {{ shownText }}<span v-if="typing" class="quote-card__caret" aria-hidden="true" />
      </span>
      <span class="quote-card__from">—— {{ current.from }}</span>
    </span>

    <span class="quote-card__hint">
      <RefreshCw :size="13" :stroke-width="1.8" :class="{ 'quote-card__hint-icon--spin': switching }" />
      {{ switching ? '取句中' : '点击换一句' }}
    </span>
  </button>
</template>

<style scoped>
.quote-card {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  width: 100%;
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--color-accent) 10%, transparent) 0, transparent 46%),
    var(--color-surface-alt);
  color: var(--color-text);
  text-align: left;
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
}

.quote-card:hover {
  border-color: color-mix(in srgb, var(--color-accent) 38%, var(--color-border));
  box-shadow: var(--shadow-1);
}

.quote-card__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: var(--radius-xs);
  color: color-mix(in srgb, var(--color-accent) 82%, var(--color-text));
  background: color-mix(in srgb, var(--color-accent) 13%, var(--color-surface));
}

.quote-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  min-width: 0;
  flex: 1;
}

.quote-card__text {
  min-height: 2.9em;
  font-size: var(--fs-lg);
  line-height: 1.7;
  letter-spacing: 0.01em;
  overflow-wrap: anywhere;
}

.quote-card__caret {
  display: inline-block;
  width: 1px;
  height: 1em;
  margin-left: 2px;
  background: var(--color-accent);
  vertical-align: -0.1em;
  animation: quote-caret 1s steps(2, start) infinite;
}

@keyframes quote-caret {
  50% {
    opacity: 0;
  }
}

.quote-card__from {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.quote-card__hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: 10px;
  white-space: nowrap;
}

.quote-card__hint-icon--spin {
  animation: quote-spin 900ms linear infinite;
}

@keyframes quote-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
