<!-- 切片预览：400 字折叠、章节/页码元信息、分页由父级控制。 -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { ChevronDown, ChevronUp, Layers3 } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import type { KnowledgeChunk } from '@/api/types'
import { CHUNK_PREVIEW_CHARS } from '@/utils/constants'

const props = defineProps<{
  chunks: KnowledgeChunk[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  error?: string
}>()

const emit = defineEmits<{
  (event: 'update:page', page: number): void
  (event: 'retry'): void
}>()

const expanded = ref<Set<number>>(new Set())

watch(
  () => props.chunks,
  () => {
    expanded.value = new Set()
  },
)

function isLong(content: string): boolean {
  return content.length > CHUNK_PREVIEW_CHARS
}

function preview(content: string): string {
  return isLong(content) ? `${content.slice(0, CHUNK_PREVIEW_CHARS)}…` : content
}

function toggle(chunkId: number): void {
  const next = new Set(expanded.value)
  if (next.has(chunkId)) {
    next.delete(chunkId)
  } else {
    next.add(chunkId)
  }
  expanded.value = next
}

function goToPage(nextPage: number): void {
  emit('update:page', nextPage)
}
</script>

<template>
  <section class="chunk-preview">
    <div v-if="loading" class="chunk-preview__loading">
      <div v-for="index in 3" :key="index" class="chunk-skeleton">
        <div class="chunk-skeleton__head">
          <AppSkeleton variant="text" width="64px" />
          <AppSkeleton variant="text" width="120px" />
        </div>
        <AppSkeleton variant="text" :rows="3" />
      </div>
    </div>

    <AppEmpty
      v-else-if="error"
      error
      title="切片暂时无法加载"
      :description="error"
    >
      <template #action>
        <AppButton variant="secondary" size="sm" @click="emit('retry')">重新加载切片</AppButton>
      </template>
    </AppEmpty>

    <template v-else-if="chunks.length > 0">
      <header class="chunk-preview__head">
        <span class="chunk-preview__count">
          <Layers3 :size="16" :stroke-width="1.8" aria-hidden="true" />
          共 <strong class="tabular">{{ total }}</strong> 个切片
        </span>
        <span class="chunk-preview__page muted tabular">第 {{ page }} 页</span>
      </header>

      <ol class="chunk-list">
        <li v-for="chunk in chunks" :key="chunk.id" class="chunk-card fade-up">
          <div class="chunk-card__head">
            <span class="chunk-index mono">#{{ chunk.chunk_index }}</span>
            <span v-if="chunk.chapter_title" class="chunk-chapter truncate" :title="chunk.chapter_title">
              {{ chunk.chapter_title }}
            </span>
            <span v-else class="chunk-chapter chunk-chapter--empty">未识别章节</span>
            <span class="chunk-meta tabular">
              <span v-if="chunk.page_no !== null">第 {{ chunk.page_no }} 页</span>
              <span>{{ chunk.char_count }} 字符</span>
            </span>
          </div>
          <p class="chunk-content">{{ expanded.has(chunk.id) ? chunk.content : preview(chunk.content) }}</p>
          <button
            v-if="isLong(chunk.content)"
            class="chunk-toggle"
            type="button"
            :aria-expanded="expanded.has(chunk.id)"
            @click="toggle(chunk.id)"
          >
            <component :is="expanded.has(chunk.id) ? ChevronUp : ChevronDown" :size="14" :stroke-width="1.9" />
            {{ expanded.has(chunk.id) ? '收起全文' : '展开全文' }}
          </button>
        </li>
      </ol>

      <footer class="chunk-preview__foot">
        <AppPagination
          :total="total"
          :page="page"
          :page-size="pageSize"
          :show-page-size="false"
          @update:page="goToPage"
        />
      </footer>
    </template>

    <AppEmpty
      v-else
      title="暂无切片"
      description="文档尚未完成解析，或切片内容为空。可稍后刷新查看。"
    />
  </section>
</template>

<style scoped>
.chunk-preview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.chunk-preview__loading {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.chunk-skeleton {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.chunk-skeleton__head {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-3);
}

.chunk-preview__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.chunk-preview__count {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-sm);
  color: var(--color-text-muted);
}

.chunk-preview__count strong {
  color: var(--color-text);
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.chunk-card {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-left: 3px solid color-mix(in srgb, var(--color-primary) 40%, var(--color-border));
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  transition: border-color 160ms ease-out, box-shadow 160ms ease-out;
}

.chunk-card:hover {
  border-color: color-mix(in srgb, var(--color-primary) 38%, var(--color-border));
  border-left-color: var(--color-primary);
  box-shadow: var(--shadow-1);
}

.chunk-card__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  margin-bottom: var(--sp-2);
}

.chunk-index {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.chunk-chapter {
  min-width: 0;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.chunk-chapter--empty {
  color: var(--color-text-muted);
  font-weight: 400;
}

.chunk-meta {
  display: inline-flex;
  gap: var(--sp-3);
  flex-shrink: 0;
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.chunk-content {
  color: var(--color-text);
  font-size: var(--fs-sm);
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chunk-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--sp-2);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.chunk-toggle:hover {
  color: var(--color-primary-hover);
}

.chunk-preview__foot {
  padding-top: var(--sp-2);
  border-top: 1px solid var(--color-border);
}
</style>
