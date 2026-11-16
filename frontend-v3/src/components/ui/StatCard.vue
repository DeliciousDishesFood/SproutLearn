<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    tag?: string
    tagTone?: 'lime' | 'soft' | 'warn'
  }>(),
  { hint: '', tag: '', tagTone: 'soft' },
)
</script>

<template>
  <article class="stat">
    <div class="stat__label">
      <span v-if="$slots.icon" class="stat__icon" aria-hidden="true"><slot name="icon" /></span>
      {{ label }}
    </div>
    <div class="stat__row">
      <span class="stat__value">{{ value }}</span>
      <span
        v-if="tag"
        class="stat__delta"
        :class="{
          'stat__delta--soft': tagTone === 'soft',
          'stat__delta--warn': tagTone === 'warn',
        }"
      >
        {{ tag }}
      </span>
    </div>
    <p v-if="hint" class="stat__hint">{{ hint }}</p>
  </article>
</template>
