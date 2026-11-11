<!-- 题目讲评弹窗：按需请求 LLM/模板，失败展示可重试错误，不白屏。 -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { AlertCircle, RefreshCw, Sparkles } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import AppTag from '@/components/base/AppTag.vue'
import { questionsApi } from '@/api/questions'
import { toUserMessage } from '@/api/client'

const props = defineProps<{
  modelValue: boolean
  questionId: number | null
  questionStem?: string
  studentAnswer?: unknown
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const loading = ref(false)
const content = ref('')
const engine = ref('')
const error = ref('')

async function load(): Promise<void> {
  if (props.questionId === null || loading.value) return
  loading.value = true
  error.value = ''
  content.value = ''
  engine.value = ''
  try {
    const result = await questionsApi.explain(props.questionId, props.studentAnswer)
    content.value = result.explanation || result.content || ''
    engine.value = result.engine || 'template'
    if (!content.value) error.value = '讲评内容为空，请重试'
  } catch (err) {
    error.value = toUserMessage(err)
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.questionId] as const,
  ([open, questionId]) => {
    if (open && questionId !== null) void load()
  },
  { immediate: true },
)

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

      <div v-if="loading" class="explain__loading" aria-busy="true">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="4" />
      </div>

      <div v-else-if="error" class="explain__error" role="alert">
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
          <AppTag :tone="engine === 'llm' ? 'accent' : 'neutral'" dot>
            {{ engine === 'llm' ? 'AI 讲评' : '模板讲评' }}
          </AppTag>
          <span class="muted text-xs">可复制到课堂笔记</span>
        </div>
        <p class="explain__content">{{ content }}</p>
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
}

.explain__content {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-text);
  font-size: var(--fs-base);
  line-height: 1.85;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
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
