<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    meta?: string
    flush?: boolean
  }>(),
  { title: '', meta: '', flush: false },
)
</script>

<template>
  <section class="card" :class="{ 'card--flush': flush }">
    <header v-if="title || $slots.actions" class="card__head">
      <h2>{{ title }}</h2>
      <div class="row">
        <span v-if="meta" class="card__meta">{{ meta }}</span>
        <slot name="actions" />
      </div>
    </header>
    <slot />
  </section>
</template>
