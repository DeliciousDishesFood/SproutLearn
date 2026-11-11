<!-- 基础卡片：统一描边、表面色与内边距，页面不重复写容器样式。 -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    padding?: 'none' | 'sm' | 'md' | 'lg'
    interactive?: boolean
  }>(),
  {
    padding: 'md',
    interactive: false,
  },
)
</script>

<template>
  <article
    class="app-card"
    :class="[`app-card--${padding}`, { 'app-card--interactive': interactive }]"
  >
    <slot />
  </article>
</template>

<style scoped>
.app-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.app-card--none {
  padding: 0;
}

.app-card--sm {
  padding: var(--sp-3);
}

.app-card--md {
  padding: var(--sp-5);
}

.app-card--lg {
  padding: var(--sp-6);
}

.app-card--interactive {
  transition: border-color 170ms ease-out, box-shadow 170ms ease-out, transform 170ms ease-out;
}

.app-card--interactive:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-2);
  transform: translateY(-1px);
}
</style>
