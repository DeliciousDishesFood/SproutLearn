<script setup lang="ts">
import { Users } from 'lucide-vue-next'
import type { ClassListItem } from '@/api/contract'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { formatDate } from '@/utils/format'

const props = defineProps<{ item: ClassListItem }>()

const emit = defineEmits<{ (event: 'toggle-archive', item: ClassListItem): void }>()
</script>

<template>
  <div class="card class-card" :class="{ 'class-card--archived': props.item.status === 0 }">
    <RouterLink class="class-card__body" :to="`/teacher/classes/${item.id}`">
      <header class="class-card__head">
        <div>
          <h2>{{ item.class_name }}</h2>
          <p class="small muted">{{ item.course_name }} · {{ item.class_code }}</p>
        </div>
        <div class="class-card__marks">
          <BaseBadge v-if="item.status === 0" tone="plain">已归档</BaseBadge>
          <span class="class-card__mark" aria-hidden="true"><Users :size="16" /></span>
        </div>
      </header>
      <div class="class-card__stats">
        <div>
          <strong>{{ item.student_count }}</strong>
          <span>学生</span>
        </div>
        <div>
          <strong>{{ item.doc_count }}</strong>
          <span>资料</span>
        </div>
        <div>
          <strong>{{ formatDate(item.created_at) }}</strong>
          <span>创建</span>
        </div>
      </div>
    </RouterLink>
    <footer class="class-card__foot" @click.stop>
      <BaseButton
        size="sm"
        :variant="item.status === 0 ? 'primary' : 'danger'"
        @click="emit('toggle-archive', item)"
      >
        {{ item.status === 0 ? '恢复班级' : '归档班级' }}
      </BaseButton>
    </footer>
  </div>
</template>

<style scoped>
.class-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow 140ms ease, border-color 140ms ease;
}

.class-card:hover {
  border-color: var(--line-strong);
  box-shadow: 0 2px 10px rgba(16, 24, 40, 0.06);
}

.class-card--archived {
  background: var(--surface-alt);
}

.class-card__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: inherit;
  text-decoration: none;
}

.class-card__body:hover {
  text-decoration: none;
}

.class-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.class-card__head h2 {
  font-size: 15px;
  font-weight: 600;
}

.class-card__marks {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}

.class-card__mark {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--lime-soft);
  color: var(--lime-text);
  flex: 0 0 auto;
}

.class-card__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.class-card__stats div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.class-card__stats strong {
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.class-card__stats span {
  color: var(--text-3);
  font-size: 11.5px;
}

.class-card__foot {
  display: flex;
  justify-content: flex-end;
}
</style>
