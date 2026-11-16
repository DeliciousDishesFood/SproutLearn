<script setup lang="ts">
withDefaults(defineProps<{ text?: string }>(), { text: '加载中…' })
</script>

<template>
  <p class="loading-line" role="status">{{ text }}</p>
</template>
