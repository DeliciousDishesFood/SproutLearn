<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    page: number
    pageSize: number
    total: number
  }>(),
  { pageSize: 10 },
)

const emit = defineEmits<{ (event: 'change', page: number): void }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(1, props.pageSize))))
const canPrev = computed(() => props.page > 1)
const canNext = computed(() => props.page < totalPages.value)
</script>

<template>
  <div v-if="total > 0" class="pagination">
    <span>共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</span>
    <button type="button" :disabled="!canPrev" @click="emit('change', page - 1)">上一页</button>
    <button type="button" :disabled="!canNext" @click="emit('change', page + 1)">下一页</button>
  </div>
</template>
