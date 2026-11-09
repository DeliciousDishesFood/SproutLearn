<!-- 上传结果：成功/失败两段清单，失败项展示可操作原因并提示删除重传。 -->
<script setup lang="ts">
import { CheckCircle2, CircleX, FileText, RotateCcw } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import type { UploadResult } from '@/api/types'
import { ERROR_CODE, ERROR_MESSAGES } from '@/utils/constants'
import { formatNumber } from '@/utils/format'

const props = defineProps<{
  result: UploadResult
}>()

const emit = defineEmits<{
  (event: 'open-doc', docId: number): void
  (event: 'retry'): void
}>()

function failMessage(code: number, message: string): string {
  const known = ERROR_MESSAGES[code]
  if (code === ERROR_CODE.FILE_TOO_LARGE || code === ERROR_CODE.UNSUPPORTED_FORMAT) {
    return known || message
  }
  return message || known || '文件处理失败，请重新上传'
}
</script>

<template>
  <section class="upload-result fade-up" aria-live="polite">
    <header class="upload-result__head">
      <div>
        <p class="eyebrow">UPLOAD REPORT</p>
        <h2 class="section-title">本次上传结果</h2>
        <p class="upload-result__summary">
          共 <strong class="tabular">{{ formatNumber(result.total) }}</strong> 个文件，
          <span class="is-success">成功 {{ result.success_list.length }}</span> 个，
          <span class="is-danger">失败 {{ result.fail_list.length }}</span> 个
        </p>
      </div>
      <AppButton v-if="result.fail_list.length > 0" variant="ghost" size="sm" @click="emit('retry')">
        <RotateCcw :size="14" :stroke-width="1.9" />
        重新选择
      </AppButton>
    </header>

    <div v-if="result.success_list.length > 0" class="upload-result__section">
      <h3 class="upload-result__section-title">
        <CheckCircle2 :size="16" :stroke-width="1.9" aria-hidden="true" />
        已入库文档
        <span>{{ result.success_list.length }}</span>
      </h3>
      <ul class="result-list">
        <li v-for="item in result.success_list" :key="item.doc_id" class="result-row result-row--success">
          <FileText class="result-row__icon" :size="17" :stroke-width="1.7" aria-hidden="true" />
          <span class="result-row__name truncate" :title="item.file_name">{{ item.file_name }}</span>
          <span class="result-row__meta tabular">{{ item.chunk_count }} 个切片</span>
          <span v-if="item.page_count !== null" class="result-row__meta tabular">{{ item.page_count }} 页</span>
          <button class="result-row__link" type="button" @click="emit('open-doc', item.doc_id)">查看切片</button>
        </li>
      </ul>
    </div>

    <div v-if="result.fail_list.length > 0" class="upload-result__section">
      <h3 class="upload-result__section-title upload-result__section-title--danger">
        <CircleX :size="16" :stroke-width="1.9" aria-hidden="true" />
        未入库文件
        <span>{{ result.fail_list.length }}</span>
      </h3>
      <ul class="result-list">
        <li v-for="(item, index) in result.fail_list" :key="`${item.file_name}-${index}`" class="result-row result-row--fail">
          <CircleX class="result-row__icon" :size="17" :stroke-width="1.7" aria-hidden="true" />
          <span class="result-row__name truncate" :title="item.file_name">{{ item.file_name }}</span>
          <span class="result-row__error">{{ failMessage(item.error_code, item.error_message) }}</span>
        </li>
      </ul>
      <p class="upload-result__note">失败文件不会影响其他文档入库。请按提示调整文件后删除重传。</p>
    </div>

    <p v-if="result.success_list.length === 0 && result.fail_list.length === 0" class="upload-result__empty">
      本次没有可处理的文件。
    </p>
  </section>
</template>

<style scoped>
.upload-result {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.upload-result__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
}

.upload-result__summary {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.upload-result__summary strong {
  color: var(--color-text);
}

.is-success {
  color: var(--color-success);
  font-weight: 600;
}

.is-danger {
  color: var(--color-danger);
  font-weight: 600;
}

.upload-result__section {
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
}

.upload-result__section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--sp-2);
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--color-success);
}

.upload-result__section-title span {
  margin-left: 2px;
  padding: 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}

.upload-result__section-title--danger {
  color: var(--color-danger);
}

.upload-result__section-title--danger span {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.result-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-height: 38px;
  padding: var(--sp-1) var(--sp-3);
  border-radius: var(--radius-xs);
  font-size: var(--fs-sm);
}

.result-row--success {
  background: color-mix(in srgb, var(--color-success) 6%, transparent);
}

.result-row--fail {
  background: color-mix(in srgb, var(--color-danger) 6%, transparent);
}

.result-row__icon {
  flex-shrink: 0;
}

.result-row--success .result-row__icon {
  color: var(--color-success);
}

.result-row--fail .result-row__icon {
  color: var(--color-danger);
}

.result-row__name {
  min-width: 0;
  flex: 1 1 auto;
  font-weight: 500;
}

.result-row__meta {
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.result-row__error {
  min-width: 0;
  flex: 1 1 auto;
  color: var(--color-danger);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.result-row__link {
  flex-shrink: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.result-row__link:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.upload-result__note {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.65;
}

.upload-result__empty {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

@media (max-width: 720px) {
  .upload-result__head {
    flex-direction: column;
  }

  .result-row {
    flex-wrap: wrap;
  }

  .result-row__name {
    flex-basis: calc(100% - 60px);
  }

  .result-row__error {
    flex-basis: 100%;
  }
}
</style>
