<script setup lang="ts">
import type { StudentListItem } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { formatDateTime } from '@/utils/format'

defineProps<{ items: StudentListItem[]; readonly?: boolean }>()

const emit = defineEmits<{
  (event: 'reset-password', item: StudentListItem): void
  (event: 'toggle-status', item: StudentListItem): void
}>()
</script>

<template>
  <div class="student-table-block">
    <p class="table-scroll-hint">左右滑动查看更多列</p>
    <div class="table-wrap table-wrap--students is-scrollable">
      <table class="table student-table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>状态</th>
            <th class="num">等级</th>
            <th class="num">XP</th>
            <th>QQ 绑定</th>
            <th>最近登录</th>
            <th class="num">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="mono">{{ item.student_no }}</td>
            <td class="student-table__name">{{ item.name }}</td>
            <td>
              <BaseBadge :tone="item.status === 0 ? 'plain' : 'lime'">
                {{ item.status === 0 ? '停用' : '正常' }}
              </BaseBadge>
            </td>
            <td class="num">Lv.{{ item.level }}</td>
            <td class="num">{{ item.xp_total }}</td>
            <td>
              <BaseBadge :tone="item.qq_bound ? 'lime' : 'plain'">
                {{ item.qq_bound ? '已绑定' : '未绑定' }}
              </BaseBadge>
            </td>
            <td class="muted">{{ formatDateTime(item.last_login_at) }}</td>
            <td class="student-table__actions">
              <div v-if="!readonly" class="actions">
                <BaseButton size="sm" @click="emit('reset-password', item)">重置密码</BaseButton>
                <BaseButton
                  size="sm"
                  :variant="item.status === 0 ? 'primary' : 'danger'"
                  @click="emit('toggle-status', item)"
                >
                  {{ item.status === 0 ? '恢复' : '停用' }}
                </BaseButton>
              </div>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
