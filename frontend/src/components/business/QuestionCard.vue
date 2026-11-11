<!-- 题库题目卡片：题型、难度、标签、选项、答案与操作入口。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { MessageSquareText, PencilLine, Trash2 } from 'lucide-vue-next'
import AppCard from '@/components/base/AppCard.vue'
import AppTag from '@/components/base/AppTag.vue'
import {
  DIFFICULTY_META,
  QUESTION_STATUS_META,
  QUESTION_TYPE_META,
} from '@/utils/constants'
import { formatAnswer } from '@/utils/questions'
import type { QuestionItem } from '@/api/types'

const props = defineProps<{
  question: QuestionItem
}>()

const emit = defineEmits<{
  (event: 'edit', question: QuestionItem): void
  (event: 'remove', question: QuestionItem): void
  (event: 'explain', question: QuestionItem): void
}>()

const typeMeta = computed(() => QUESTION_TYPE_META[props.question.type])
const difficultyMeta = computed(() => DIFFICULTY_META[props.question.difficulty])
const statusMeta = computed(() => QUESTION_STATUS_META[props.question.status])
const answerText = computed(() =>
  formatAnswer(props.question.answer, props.question.type, props.question.options),
)
</script>

<template>
  <AppCard class="question-card" padding="md">
    <header class="question-card__head">
      <div class="question-card__tags">
        <AppTag :tone="typeMeta.tone">{{ typeMeta.label }}</AppTag>
        <AppTag :tone="difficultyMeta.tone">{{ difficultyMeta.label }}</AppTag>
        <AppTag tone="neutral">{{ question.knowledge_tag }}</AppTag>
        <AppTag :tone="statusMeta.tone" dot>{{ statusMeta.label }}</AppTag>
      </div>
      <span class="question-card__id mono">Q-{{ question.id }}</span>
    </header>

    <p class="question-card__stem">{{ question.stem }}</p>

    <ol v-if="question.options?.length" class="question-card__options">
      <li v-for="option in question.options" :key="option.key">
        <span class="question-card__option-key mono">{{ option.key }}</span>
        <span>{{ option.text }}</span>
      </li>
    </ol>

    <dl class="question-card__answer">
      <div>
        <dt>标准答案</dt>
        <dd>{{ answerText }}</dd>
      </div>
      <div v-if="question.analysis">
        <dt>解析</dt>
        <dd class="question-card__analysis">{{ question.analysis }}</dd>
      </div>
    </dl>

    <footer class="question-card__actions">
      <button class="text-action" type="button" @click="emit('explain', question)">
        <MessageSquareText :size="14" :stroke-width="1.8" />
        讲评
      </button>
      <button class="text-action" type="button" @click="emit('edit', question)">
        <PencilLine :size="14" :stroke-width="1.8" />
        编辑
      </button>
      <button class="text-action text-action--danger" type="button" @click="emit('remove', question)">
        <Trash2 :size="14" :stroke-width="1.8" />
        删除
      </button>
    </footer>
  </AppCard>
</template>

<style scoped>
.question-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.question-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
}

.question-card__tags {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.question-card__id {
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.question-card__stem {
  font-size: var(--fs-base);
  font-weight: 600;
  line-height: 1.7;
}

.question-card__options {
  display: grid;
  gap: var(--sp-1);
}

.question-card__options li {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.question-card__option-key {
  display: inline-flex;
  justify-content: center;
  min-width: 20px;
  font-weight: 600;
  color: var(--color-primary);
}

.question-card__answer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.question-card__answer div {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
}

.question-card__answer dt {
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.question-card__answer dd {
  color: var(--color-text);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.question-card__analysis {
  color: var(--color-text-muted);
}

.question-card__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.text-action:hover {
  background: var(--color-primary-soft);
}

.text-action--danger {
  color: var(--color-danger);
}

.text-action--danger:hover {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}
</style>
