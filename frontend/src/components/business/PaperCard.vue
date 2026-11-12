<!-- 试卷卡片：状态徽标、题量/总分/时长/严格度与发布、撤回、成绩入口。 -->
<script setup lang="ts">
import { computed } from 'vue'
import {
  ArrowRight,
  Clock3,
  ListChecks,
  Send,
  Undo2,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppCard from '@/components/base/AppCard.vue'
import AppTag from '@/components/base/AppTag.vue'
import {
  BLANK_MODE_META,
  PAPER_KIND_META,
  PAPER_MODE_LABEL,
  PAPER_STATUS_META,
} from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import type { PaperItem } from '@/api/types'

const props = defineProps<{
  paper: PaperItem
}>()

const emit = defineEmits<{
  (event: 'open', paper: PaperItem): void
  (event: 'publish', paper: PaperItem): void
  (event: 'withdraw', paper: PaperItem): void
}>()

const statusMeta = computed(() => PAPER_STATUS_META[props.paper.status])
const kindMeta = computed(() => PAPER_KIND_META[props.paper.kind ?? 'practice'])
const blankMeta = computed(
  () => BLANK_MODE_META[props.paper.blank_mode] ?? BLANK_MODE_META.smart,
)
const canPublish = computed(() => props.paper.status !== 'published')
const canWithdraw = computed(() => props.paper.status === 'published')
</script>

<template>
  <AppCard class="paper-card" padding="md">
    <header class="paper-card__head">
      <div class="paper-card__title-wrap">
        <h3 class="paper-card__title">{{ paper.title }}</h3>
        <p class="paper-card__meta">
          {{ PAPER_MODE_LABEL[paper.mode] }} · {{ blankMeta.label }}
          <template v-if="paper.shuffle"> · 题目乱序</template>
        </p>
      </div>
      <div class="paper-card__tags">
        <AppTag :tone="kindMeta.tone">{{ kindMeta.label }}</AppTag>
        <AppTag :tone="statusMeta.tone" dot>{{ statusMeta.label }}</AppTag>
      </div>
    </header>

    <dl class="paper-card__stats">
      <div>
        <dt>题量</dt>
        <dd class="tabular">{{ paper.question_count }}</dd>
      </div>
      <div>
        <dt>总分</dt>
        <dd class="tabular">{{ paper.total_score }}</dd>
      </div>
      <div>
        <dt>时长</dt>
        <dd class="tabular">
          <Clock3 :size="13" :stroke-width="1.8" aria-hidden="true" />
          {{ paper.duration_minutes > 0 ? `${paper.duration_minutes} 分钟` : '不限时' }}
        </dd>
      </div>
      <div>
        <dt>严格度</dt>
        <dd>{{ blankMeta.short }}</dd>
      </div>
    </dl>

    <p class="paper-card__time">
      <ListChecks :size="13" :stroke-width="1.8" aria-hidden="true" />
      {{ paper.published_at ? `发布于 ${formatDateTime(paper.published_at)}` : `创建于 ${formatDateTime(paper.created_at)}` }}
    </p>

    <footer class="paper-card__actions">
      <AppButton variant="ghost" size="sm" @click="emit('open', paper)">
        查看详情
        <ArrowRight :size="14" :stroke-width="1.9" />
      </AppButton>
      <span class="spacer" />
      <AppButton
        v-if="canWithdraw"
        variant="danger-outline"
        size="sm"
        @click="emit('withdraw', paper)"
      >
        <Undo2 :size="14" :stroke-width="1.8" />
        撤回
      </AppButton>
      <AppButton
        v-if="canPublish"
        variant="primary"
        size="sm"
        @click="emit('publish', paper)"
      >
        <Send :size="14" :stroke-width="1.8" />
        {{ paper.status === 'closed' ? '重新发布' : '发布' }}
      </AppButton>
    </footer>
  </AppCard>
</template>

<style scoped>
.paper-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.paper-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-3);
}

.paper-card__title-wrap {
  min-width: 0;
}

.paper-card__tags {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  flex-shrink: 0;
}

.paper-card__title {
  font-size: var(--fs-lg);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.paper-card__meta {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-card__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-2);
  padding: var(--sp-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.paper-card__stats dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-card__stats dd {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: var(--fs-base);
  font-weight: 600;
}

.paper-card__time {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.paper-card__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

@media (max-width: 560px) {
  .paper-card__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
