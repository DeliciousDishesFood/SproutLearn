<!-- 分页：页码窗口 + 每页条数，全部交互事件由父级控制。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { PAGE_SIZE_OPTIONS } from '@/utils/constants'

const props = withDefaults(
  defineProps<{
    total: number
    page: number
    pageSize: number
    pageSizeOptions?: number[]
    showPageSize?: boolean
  }>(),
  {
    pageSizeOptions: () => PAGE_SIZE_OPTIONS,
    showPageSize: true,
  },
)

const emit = defineEmits<{
  (event: 'update:page', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'change', page: number, pageSize: number): void
}>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const currentPage = computed(() => Math.min(Math.max(1, props.page), pageCount.value))

const pages = computed<(number | 'ellipsis')[]>(() => {
  const count = pageCount.value
  const page = currentPage.value
  if (count <= 7) {
    return Array.from({ length: count }, (_value, index) => index + 1)
  }
  const start = Math.max(2, page - 2)
  const end = Math.min(count - 1, page + 2)
  const result: (number | 'ellipsis')[] = [1]
  if (start > 2) result.push('ellipsis')
  for (let index = start; index <= end; index += 1) result.push(index)
  if (end < count - 1) result.push('ellipsis')
  result.push(count)
  return result
})

function goTo(nextPage: number): void {
  if (nextPage < 1 || nextPage > pageCount.value || nextPage === currentPage.value) return
  emit('update:page', nextPage)
  emit('change', nextPage, props.pageSize)
}

function changePageSize(event: Event): void {
  const nextSize = Number((event.target as HTMLSelectElement).value)
  if (!Number.isFinite(nextSize) || nextSize <= 0) return
  emit('update:pageSize', nextSize)
  emit('update:page', 1)
  emit('change', 1, nextSize)
}
</script>

<template>
  <div v-if="total > 0" class="app-pagination">
    <span class="app-pagination__summary tabular">
      共 {{ total }} 条 · 第 {{ currentPage }} / {{ pageCount }} 页
    </span>

    <div class="app-pagination__controls">
      <button
        class="app-pagination__nav"
        type="button"
        aria-label="上一页"
        :disabled="currentPage <= 1"
        @click="goTo(currentPage - 1)"
      >
        <ChevronLeft :size="16" :stroke-width="1.9" />
      </button>

      <template v-for="(item, index) in pages" :key="`${item}-${index}`">
        <span v-if="item === 'ellipsis'" class="app-pagination__ellipsis">…</span>
        <button
          v-else
          class="app-pagination__page"
          :class="{ 'app-pagination__page--active': item === currentPage }"
          type="button"
          :aria-current="item === currentPage ? 'page' : undefined"
          @click="goTo(item)"
        >
          {{ item }}
        </button>
      </template>

      <button
        class="app-pagination__nav"
        type="button"
        aria-label="下一页"
        :disabled="currentPage >= pageCount"
        @click="goTo(currentPage + 1)"
      >
        <ChevronRight :size="16" :stroke-width="1.9" />
      </button>

      <label v-if="showPageSize" class="app-pagination__size">
        <span class="visually-hidden">每页条数</span>
        <select :value="pageSize" @change="changePageSize">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
        </select>
      </label>
    </div>
  </div>
</template>

<style scoped>
.app-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
  padding: var(--sp-3) var(--sp-4);
}

.app-pagination__summary {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.app-pagination__controls {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}

.app-pagination__nav,
.app-pagination__page {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 30px;
  padding: 0 var(--sp-2);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
  transition: background-color 160ms ease-out, color 160ms ease-out, border-color 160ms ease-out;
}

.app-pagination__nav:hover:not(:disabled),
.app-pagination__page:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.app-pagination__page--active {
  color: var(--color-text-inverse);
  background: var(--color-primary);
  border-color: var(--color-primary);
  font-weight: 600;
}

.app-pagination__page--active:hover {
  color: var(--color-text-inverse);
  background: var(--color-primary-hover);
}

.app-pagination__nav:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.app-pagination__ellipsis {
  min-width: 22px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.app-pagination__size select {
  height: 30px;
  padding: 0 var(--sp-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.app-pagination__size select:focus {
  border-color: var(--color-primary);
}
</style>
