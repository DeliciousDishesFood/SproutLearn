<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: 'default' | 'lime' | 'amber' | 'danger' | 'plain'
  }>(),
  { tone: 'default' },
)
</script>

<template>
  <span
    class="badge"
    :class="{
      'badge--lime': tone === 'lime',
      'badge--amber': tone === 'amber',
      'badge--danger': tone === 'danger',
      'badge--plain': tone === 'plain',
    }"
  >
    <slot />
  </span>
</template>
