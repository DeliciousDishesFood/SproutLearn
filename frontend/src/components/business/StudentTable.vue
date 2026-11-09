<!-- 学生表格：服务端分页 + 关键字搜索，QQ 绑定状态由接口派生字段展示。 -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { RefreshCw, Search, UsersRound } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppPagination from '@/components/base/AppPagination.vue'
import AppTable from '@/components/base/AppTable.vue'
import AppTag from '@/components/base/AppTag.vue'
import type { StudentListItem } from '@/api/types'
import type { TableColumn } from '@/types'
import { formatDateTime, formatRelativeTime } from '@/utils/format'

const props = defineProps<{
  students: StudentListItem[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  keyword: string
  error?: string
}>()

const emit = defineEmits<{
  (event: 'search', keyword: string): void
  (event: 'pagination-change', page: number, pageSize: number): void
  (event: 'refresh'): void
}>()

const columns: TableColumn[] = [
  { key: 'student_no', title: '学号', width: '120px' },
  { key: 'name', title: '姓名' },
  { key: 'level', title: '等级', width: '72px', align: 'center' },
  { key: 'xp_total', title: '经验值', width: '88px', align: 'right' },
  { key: 'qq_bound', title: 'QQ 绑定', width: '100px' },
  { key: 'created_at', title: '加入时间', width: '140px' },
  { key: 'last_login_at', title: '最近登录', width: '132px' },
]

const searchText = ref(props.keyword)

watch(
  () => props.keyword,
  (value) => {
    searchText.value = value
  },
)

function submitSearch(): void {
  emit('search', searchText.value.trim())
}

function handlePaginationChange(nextPage: number, nextSize: number): void {
  emit('pagination-change', nextPage, nextSize)
}
</script>

<template>
  <section class="student-table panel">
    <header class="panel-head student-table__head">
      <div>
        <h2 class="section-title">班级学生</h2>
        <p class="section-note">学号在班内唯一，按学号升序排列。</p>
      </div>
      <div class="student-table__tools">
        <form class="student-search" role="search" @submit.prevent="submitSearch">
          <AppInput v-model="searchText" type="search" placeholder="搜索学号或姓名" />
          <AppButton type="submit" variant="ghost" size="sm" aria-label="搜索学生">
            <Search :size="16" :stroke-width="1.9" />
          </AppButton>
        </form>
        <button class="icon-btn" type="button" title="刷新名单" aria-label="刷新名单" @click="emit('refresh')">
          <RefreshCw :size="16" :stroke-width="1.8" />
        </button>
      </div>
    </header>

    <div v-if="error" class="state-error">
      <AppEmpty error title="学生名单暂时无法加载" :description="error">
        <template #action>
          <AppButton variant="secondary" size="sm" @click="emit('refresh')">重新获取名单</AppButton>
        </template>
      </AppEmpty>
    </div>

    <template v-else>
      <AppTable
        :columns="columns"
        :rows="students"
        :loading="loading"
        :skeleton-rows="6"
        empty-title="还没有学生加入"
        empty-description="把邀请码发到班级群，学生加入后就会出现在这里。"
      >
        <template #cell-student_no="{ row }">
          <span class="mono student-no">{{ row.student_no }}</span>
        </template>

        <template #cell-name="{ row }">
          <span class="student-name">{{ row.name }}</span>
        </template>

        <template #cell-level="{ row }">
          <AppTag tone="primary">Lv. {{ row.level }}</AppTag>
        </template>

        <template #cell-xp_total="{ row }">
          <span class="tabular">{{ row.xp_total }}</span>
        </template>

        <template #cell-qq_bound="{ row }">
          <AppTag :tone="row.qq_bound ? 'success' : 'neutral'" dot>
            {{ row.qq_bound ? '已绑定' : '未绑定' }}
          </AppTag>
        </template>

        <template #cell-created_at="{ row }">
          <span class="muted">{{ formatDateTime(row.created_at) }}</span>
        </template>

        <template #cell-last_login_at="{ row }">
          <span v-if="row.last_login_at" class="muted" :title="row.last_login_at">
            {{ formatRelativeTime(row.last_login_at) }}
          </span>
          <span v-else class="muted">从未登录</span>
        </template>

        <template #empty-action>
          <AppButton variant="ghost" size="sm" @click="emit('refresh')">
            <RefreshCw :size="14" :stroke-width="1.8" />
            刷新名单
          </AppButton>
        </template>
      </AppTable>

      <footer class="student-table__foot">
        <span class="student-table__count">
          <UsersRound :size="15" :stroke-width="1.8" />
          共 <strong class="tabular">{{ total }}</strong> 名学生
        </span>
        <AppPagination
          v-if="total > 0"
          :total="total"
          :page="page"
          :page-size="pageSize"
          @change="handlePaginationChange"
        />
      </footer>
    </template>
  </section>
</template>

<style scoped>
.student-table {
  overflow: hidden;
}

.student-table__head {
  flex-wrap: wrap;
}

.student-table__tools {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.student-search {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  width: 250px;
}

.student-search :deep(.app-input) {
  flex: 1;
}

.student-no {
  font-size: var(--fs-sm);
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.student-name {
  font-weight: 600;
  white-space: nowrap;
}

.student-table__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  flex-wrap: wrap;
  padding: var(--sp-4) var(--sp-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-alt);
}

.student-table__count {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.student-table__count strong {
  color: var(--color-text);
  font-weight: 600;
}

@media (max-width: 720px) {
  .student-search {
    width: 100%;
  }

  .student-table__tools {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
