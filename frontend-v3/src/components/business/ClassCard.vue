<script setup lang="ts">
import { Users } from 'lucide-vue-next'
import type { ClassListItem } from '@/api/contract'
import { formatDate } from '@/utils/format'

defineProps<{ item: ClassListItem }>()
</script>

<template>
  <RouterLink class="card class-card" :to="`/teacher/classes/${item.id}`">
    <header class="class-card__head">
      <div>
        <h2>{{ item.class_name }}</h2>
        <p class="small muted">{{ item.course_name }} · {{ item.class_code }}</p>
      </div>
      <span class="class-card__mark" aria-hidden="true"><Users :size="16" /></span>
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
</template>

<style scoped>
.class-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: inherit;
  text-decoration: none;
  transition: box-shadow 140ms ease, border-color 140ms ease;
}

.class-card:hover {
  border-color: var(--line-strong);
  box-shadow: 0 2px 10px rgba(16, 24, 40, 0.06);
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
  color: var(--tertiary);
  font-size: 10.5px;
}
</style>
