<!-- 题目讲评弹窗：SSE 流式读取，首个内容立即渲染；Markdown 净化后展示，失败保留已收内容。 -->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { AlertCircle, RefreshCw, Sparkles } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { questionsApi, type ExplainStreamHandle } from '@/api/questions'
import { toUserMessage } from '@/api/client'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  modelValue: boolean
  questionId: number | null
  questionStem?: string
  studentAnswer?: unknown
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const streaming = ref(false)
const content = ref('')
const engine = ref('')
const model = ref('')
const elapsedMs = ref<number | null>(null)
const degraded = ref(false)
const error = ref('')

let handle: ExplainStreamHandle | null = null

const html = computed(() => renderMarkdown(content.value))
const engineLabel = computed(() => (engine.value === 'llm' ? 'AI 讲评' : '模板讲评'))

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError'
}

function stopStream(): void {
  if (handle) {
    handle.abort()
    handle = null
  }
}

/** 流式接口不可用时退回同步讲评，保证讲评功能始终可用。 */
async function fallbackExplain(questionId: number): Promise<boolean> {
  try {
    const result = await questionsApi.explain(questionId, props.studentAnswer)
    const text = result.explanation || result.content || ''
    if (!text) return false
    content.value = text
    engine.value = result.engine || 'template'
    degraded.value = Boolean(result.degraded)
    return true
  } catch {
    return false
  }
}

async function load(): Promise<void> {
  const questionId = props.questionId
  if (questionId === null || streaming.value) return
  stopStream()
  streaming.value = true
  error.value = ''
  content.value = ''
  engine.value = ''
  model.value = ''
  elapsedMs.value = null
  degraded.value = false

  const current = questionsApi.explainStream(
    questionId,
    {
      onMeta: (payload) => {
        if (payload.engine) engine.value = payload.engine
      },
      onDelta: (chunk) => {
        if (chunk) content.value += chunk
      },
      onDone: (payload) => {
        if (payload.engine) engine.value = payload.engine
        degraded.value = Boolean(payload.degraded)
        elapsedMs.value = typeof payload.elapsed_ms === 'number' ? payload.elapsed_ms : null
      },
    },
    props.studentAnswer,
  )
  handle = current

  try {
    await current.promise
    if (!content.value) error.value = '讲评内容为空，请重试'
  } catch (err) {
    if (!isAbortError(err)) {
      // 首个内容到达前断流：退回同步接口，避免整块讲评不可用。
      if (!content.value) await fallbackExplain(questionId)
      if (!content.value) error.value = toUserMessage(err)
      else error.value = '讲评流已中断，以上为已生成内容'
    }
  } finally {
    if (handle === current) {
      handle = null
      streaming.value = false
    }
  }
}

watch(
  () => [props.modelValue, props.questionId] as const,
  ([open, questionId]) => {
    if (open && questionId !== null) void load()
    if (!open) stopStream()
  },
  { immediate: true },
)

onBeforeUnmount(stopStream)

function close(): void {
  emit('update:modelValue', false)
}
</script>

<template>
  <AppModal
    :model-value="modelValue"
    title="题目讲评"
    description="结合题干、标准答案与解析给出的复习提示。"
    width="620px"
    hide-footer
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="explain">
      <p v-if="questionStem" class="explain__stem">{{ questionStem }}</p>

      <div v-if="streaming && !content && !error" class="explain__loading" aria-busy="true">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="4" />
      </div>

      <div v-else-if="error && !content" class="explain__error" role="alert">
        <AlertCircle :size="18" :stroke-width="1.9" aria-hidden="true" />
        <div class="grow">
          <p class="explain__error-title">讲评暂时没有生成</p>
          <p class="explain__error-text">{{ error }}</p>
        </div>
        <AppButton variant="secondary" size="sm" @click="load">
          <RefreshCw :size="14" :stroke-width="1.8" />
          重试
        </AppButton>
      </div>

      <template v-else>
        <div class="explain__meta">
          <AppTag :tone="engine === 'llm' ? 'accent' : 'neutral'" dot>{{ engineLabel }}</AppTag>
          <AppTag v-if="degraded" tone="warning">AI 补充失败，已展示模板</AppTag>
          <span v-if="model" class="muted text-xs">{{ model }}</span>
          <span v-if="elapsedMs !== null" class="muted text-xs tabular">{{ elapsedMs }} ms</span>
          <span v-if="streaming" class="explain__streaming" role="status">AI 正在补充…</span>
        </div>

        <!-- 内容先 accumulated 再统一经 renderMarkdown 净化 -->
        <div class="explain__markdown" v-html="html" />

        <p v-if="error" class="explain__interrupted" role="status">
          <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
          {{ error }}
          <button class="explain__retry" type="button" @click="load">重新生成</button>
        </p>
      </template>

      <footer class="explain__foot">
        <span class="muted text-xs">
          <Sparkles :size="13" :stroke-width="1.8" />
          讲评失败不会影响作答与成绩
        </span>
        <AppButton variant="ghost" size="sm" @click="close">关闭</AppButton>
      </footer>
    </div>
  </AppModal>
</template>

<style scoped>
.explain {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.explain__stem {
  padding: var(--sp-3) var(--sp-4);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.explain__loading {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-height: 130px;
}

.explain__error {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-4);
  border: 1px solid color-mix(in srgb, var(--color-danger) 26%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-danger) 6%, transparent);
  color: var(--color-danger);
}

.explain__error-title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.explain__error-text {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.explain__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.explain__streaming {
  color: var(--color-primary);
  font-size: var(--fs-xs);
}

.explain__markdown {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text);
  font-size: var(--fs-base);
  line-height: 1.85;
  overflow-wrap: anywhere;
}

.explain__markdown :deep(h1),
.explain__markdown :deep(h2),
.explain__markdown :deep(h3),
.explain__markdown :deep(h4) {
  margin: var(--sp-4) 0 var(--sp-2);
  font-size: var(--fs-lg);
  line-height: 1.5;
}

.explain__markdown :deep(h1:first-child),
.explain__markdown :deep(h2:first-child),
.explain__markdown :deep(h3:first-child) {
  margin-top: 0;
}

.explain__markdown :deep(p) {
  margin: var(--sp-2) 0;
}

.explain__markdown :deep(ul),
.explain__markdown :deep(ol) {
  margin: var(--sp-2) 0;
  padding-left: var(--sp-5);
}

.explain__markdown :deep(li) {
  margin: 2px 0;
}

.explain__markdown :deep(code) {
  padding: 1px 5px;
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}

.explain__markdown :deep(pre) {
  margin: var(--sp-3) 0;
  padding: var(--sp-3) var(--sp-4);
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.explain__markdown :deep(pre code) {
  padding: 0;
  background: transparent;
  font-size: var(--fs-xs);
  line-height: 1.7;
}

.explain__markdown :deep(table) {
  display: block;
  width: 100%;
  margin: var(--sp-3) 0;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.explain__markdown :deep(th),
.explain__markdown :deep(td) {
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--color-border);
  text-align: left;
}

.explain__markdown :deep(th) {
  background: var(--color-surface);
  font-weight: 600;
}

.explain__markdown :deep(blockquote) {
  margin: var(--sp-3) 0;
  padding-left: var(--sp-3);
  border-left: 3px solid var(--color-border-strong);
  color: var(--color-text-muted);
}

.explain__interrupted {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--color-warning);
  font-size: var(--fs-xs);
}

.explain__retry {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.explain__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.explain__foot .muted {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
</style>
