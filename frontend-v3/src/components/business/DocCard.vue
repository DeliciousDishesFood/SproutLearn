<script setup lang="ts">
import { FileText } from 'lucide-vue-next'
import type { KnowledgeDocListItem } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import { DOC_STATUS_LABEL, docStatusTone, formatDateTime, formatFileSize } from '@/utils/format'

defineProps<{ item: KnowledgeDocListItem; classId: number }>()
defineEmits<{ (event: 'delete', item: KnowledgeDocListItem): void }>()
</script>

<template>
  <article class="doc-card card">
    <header class="doc-card__head">
      <span class="doc-card__icon" aria-hidden="true"><FileText :size="16" /></span>
      <div class="doc-card__title">
        <h2>{{ item.title }}</h2>
        <p class="small muted">
          {{ item.file_name }} · {{ formatFileSize(item.file_size) }} · {{ formatDateTime(item.created_at) }}
        </p>
      </div>
      <BaseBadge :tone="docStatusTone(item.status)">{{ DOC_STATUS_LABEL[item.status] ?? '未知' }}</BaseBadge>
    </header>
    <div class="doc-card__meta">
      <span>{{ item.chunk_count }} 个切片</span>
      <span v-if="item.page_count">{{ item.page_count }} 页</span>
      <span v-if="item.error_message" class="doc-card__error">{{ item.error_message }}</span>
    </div>
    <footer class="doc-card__foot">
      <RouterLink class="btn btn--sm" :to="`/teacher/classes/${classId}/knowledge/${item.id}`">
        查看切片
      </RouterLink>
      <button class="btn btn--sm btn--danger" type="button" @click="$emit('delete', item)">删除</button>
    </footer>
  </article>
</template>

<style scoped>
.doc-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.doc-card__head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.doc-card__icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--surface-sunken);
  color: var(--muted);
  flex: 0 0 auto;
}

.doc-card__title {
  flex: 1;
  min-width: 0;
}

.doc-card__title h2 {
  font-size: 13.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  color: var(--text-3);
  font-size: 11.5px;
}

.doc-card__error {
  color: var(--danger);
  word-break: break-word;
}

.doc-card__foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}
</style>
