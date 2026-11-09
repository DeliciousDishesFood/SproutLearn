<!-- 基础表格：表头字重区分、斑马纹、行高 token；内置加载/空态。 -->
<script setup lang="ts">
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import type { TableColumn } from '@/types'

const props = withDefaults(
  defineProps<{
    columns: TableColumn[]
    rows: any[]
    rowKey?: string
    loading?: boolean
    skeletonRows?: number
    emptyTitle?: string
    emptyDescription?: string
    minWidth?: string
    striped?: boolean
  }>(),
  {
    rowKey: 'id',
    loading: false,
    skeletonRows: 5,
    emptyTitle: '暂无数据',
    emptyDescription: '',
    minWidth: '640px',
    striped: true,
  },
)

function keyOf(row: any, index: number): string | number {
  const value = row[props.rowKey]
  return value === undefined || value === null ? index : (value as string | number)
}
</script>

<template>
  <div class="app-table">
    <div class="app-table__scroll">
      <table :style="{ minWidth }">
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              :style="{ width: column.width, textAlign: column.align || 'left' }"
              :class="column.className"
              scope="col"
            >
              {{ column.title }}
            </th>
          </tr>
        </thead>
        <tbody v-if="loading">
          <tr v-for="rowIndex in skeletonRows" :key="`skeleton-${rowIndex}`">
            <td v-for="column in columns" :key="column.key">
              <AppSkeleton variant="text" width="72%" />
            </td>
          </tr>
        </tbody>
        <tbody v-else-if="rows.length > 0">
          <tr
            v-for="(row, rowIndex) in rows"
            :key="keyOf(row, rowIndex)"
            :class="{ 'app-table__row--striped': striped && rowIndex % 2 === 1 }"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              :style="{ textAlign: column.align || 'left' }"
              :class="column.className"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]" :index="rowIndex">
                {{ row[column.key] ?? '—' }}
              </slot>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td :colspan="columns.length" class="app-table__empty-cell">
              <slot name="empty">
                <AppEmpty :title="emptyTitle" :description="emptyDescription" compact>
                  <template v-if="$slots['empty-action']" #action>
                    <slot name="empty-action" />
                  </template>
                </AppEmpty>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.app-table__scroll {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

th {
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-align: left;
  white-space: nowrap;
}

td {
  height: var(--row-h);
  padding: var(--sp-2) var(--sp-4);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: var(--fs-sm);
  vertical-align: middle;
}

tbody tr:last-child td {
  border-bottom: 0;
}

.app-table__row--striped td {
  background: var(--color-surface-alt);
}

tbody tr:hover td {
  background: color-mix(in srgb, var(--color-primary-soft) 55%, var(--color-surface));
}

.app-table__empty-cell {
  height: auto;
  padding: 0;
}

.app-table__empty-cell:hover {
  background: transparent;
}
</style>
