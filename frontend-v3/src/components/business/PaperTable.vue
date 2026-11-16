<script setup lang="ts">
import type { PaperItem } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import {
  PAPER_KIND_LABEL,
  PAPER_STATUS_LABEL,
  formatDateTime,
  paperStatusTone,
} from '@/utils/format'

defineProps<{ rows: PaperItem[] }>()
</script>

<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>试卷</th>
          <th>用途</th>
          <th>状态</th>
          <th class="num">题量</th>
          <th class="num">总分</th>
          <th>截止</th>
          <th class="num">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>
            <span class="row-title">
              <strong>{{ row.title }}</strong>
              <em>{{ formatDateTime(row.created_at) }}</em>
            </span>
          </td>
          <td>{{ PAPER_KIND_LABEL[row.kind] ?? row.kind }}</td>
          <td>
            <BaseBadge :tone="paperStatusTone(row.status)">
              {{ PAPER_STATUS_LABEL[row.status] ?? row.status }}
            </BaseBadge>
          </td>
          <td class="num">{{ row.question_count }}</td>
          <td class="num">{{ row.total_score }}</td>
          <td class="tertiary">{{ row.due_at ? formatDateTime(row.due_at) : '未设置截止' }}</td>
          <td>
            <div class="actions">
              <RouterLink class="btn btn--sm" :to="`/teacher/papers/${row.id}`">详情</RouterLink>
              <RouterLink
                v-if="row.status !== 'draft'"
                class="btn btn--sm"
                :to="`/teacher/papers/${row.id}/attempts`"
              >
                批改
              </RouterLink>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
