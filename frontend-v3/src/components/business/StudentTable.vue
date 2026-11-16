<script setup lang="ts">
import type { StudentListItem } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import { formatDateTime } from '@/utils/format'

defineProps<{ items: StudentListItem[] }>()
</script>

<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>学号</th>
          <th>姓名</th>
          <th class="num">等级</th>
          <th class="num">XP</th>
          <th>QQ 绑定</th>
          <th>最近登录</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td class="mono">{{ item.student_no }}</td>
          <td>{{ item.name }}</td>
          <td class="num">Lv.{{ item.level }}</td>
          <td class="num">{{ item.xp_total }}</td>
          <td>
            <BaseBadge :tone="item.qq_bound ? 'lime' : 'plain'">
              {{ item.qq_bound ? '已绑定' : '未绑定' }}
            </BaseBadge>
          </td>
          <td class="tertiary">{{ formatDateTime(item.last_login_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
