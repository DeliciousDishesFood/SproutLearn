<!-- 班级卡片：展示班级编号、课程与人数/文档数，整卡可进入详情。 -->
<script setup lang="ts">
import { ArrowUpRight, FileText, Hash, UsersRound } from 'lucide-vue-next'
import type { ClassListItem } from '@/api/types'
import { formatDate } from '@/utils/format'

defineProps<{
  classItem: ClassListItem
}>()
</script>

<template>
  <router-link :to="`/teacher/classes/${classItem.id}`" class="class-card">
    <div class="class-card__top">
      <span class="class-card__status">
        <span class="status-dot" :class="{ 'status-dot--off': classItem.status !== 1 }" />
        {{ classItem.status === 1 ? '进行中' : '已归档' }}
      </span>
      <ArrowUpRight class="class-card__arrow" :size="18" :stroke-width="1.8" aria-hidden="true" />
    </div>

    <h3 class="class-card__name">{{ classItem.class_name }}</h3>
    <p class="class-card__course">{{ classItem.course_name }}</p>

    <div class="class-card__code">
      <Hash :size="14" :stroke-width="1.8" aria-hidden="true" />
      <span class="mono">{{ classItem.class_code }}</span>
      <span class="class-card__code-label">班级编号</span>
    </div>

    <div class="class-card__foot">
      <span class="class-card__metric">
        <UsersRound :size="15" :stroke-width="1.8" aria-hidden="true" />
        <span class="tabular">{{ classItem.student_count }}</span> 名学生
      </span>
      <span class="class-card__metric">
        <FileText :size="15" :stroke-width="1.8" aria-hidden="true" />
        <span class="tabular">{{ classItem.doc_count }}</span> 份文档
      </span>
      <span class="class-card__date">{{ formatDate(classItem.created_at) }} 创建</span>
    </div>
  </router-link>
</template>

<style scoped>
.class-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-5);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-1);
  transition: transform 170ms ease-out, border-color 170ms ease-out, box-shadow 170ms ease-out;
}

.class-card::after {
  content: '';
  position: absolute;
  right: -26px;
  bottom: -34px;
  width: 100px;
  height: 100px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-primary) 5%, transparent);
  pointer-events: none;
}

.class-card:hover {
  color: var(--color-text);
  border-color: color-mix(in srgb, var(--color-primary) 34%, var(--color-border));
  box-shadow: var(--shadow-2);
  transform: translateY(-2px);
}

.class-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.class-card__status {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
}

.status-dot--off {
  background: var(--color-border-strong);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-border-strong) 20%, transparent);
}

.class-card__arrow {
  color: var(--color-text-muted);
  opacity: 0;
  transform: translate(-2px, 2px);
  transition: opacity 170ms ease-out, transform 170ms ease-out, color 170ms ease-out;
}

.class-card:hover .class-card__arrow {
  opacity: 1;
  transform: translate(0, 0);
  color: var(--color-primary);
}

.class-card__name {
  font-size: var(--fs-lg);
  line-height: 1.4;
  padding-right: var(--sp-5);
}

.class-card__course {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.class-card__code {
  display: flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin-top: var(--sp-2);
  padding: 3px var(--sp-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.class-card__code .mono {
  color: var(--color-text);
  font-size: var(--fs-sm);
  letter-spacing: 0.06em;
}

.class-card__code-label {
  color: var(--color-text-muted);
}

.class-card__foot {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
  margin-top: var(--sp-3);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
  font-size: var(--fs-xs);
  color: var(--color-text-muted);
  position: relative;
  z-index: 1;
}

.class-card__metric {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.class-card__date {
  margin-left: auto;
}
</style>
