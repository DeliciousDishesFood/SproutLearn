<script setup lang="ts">
withDefaults(
  defineProps<{
    height?: string
    count?: number
  }>(),
  { height: '14px', count: 1 },
)
</script>

<template>
  <div class="stack" style="gap: 8px">
    <div
      v-for="index in count"
      :key="index"
      class="skeleton"
      :style="{ height, width: index === count && count > 1 ? '62%' : '100%' }"
    />
  </div>
</template>
