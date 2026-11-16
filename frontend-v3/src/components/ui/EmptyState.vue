<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    title: string
    description?: string
    actionLabel?: string
  }>(),
  { description: '', actionLabel: '' },
)

defineEmits<{ (event: 'action'): void }>()
</script>

<template>
  <div class="empty-card">
    <span class="empty-card__icon" aria-hidden="true">
      <slot name="icon"><Inbox :size="18" /></slot>
    </span>
    <div>
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
      <button v-if="actionLabel" class="btn btn--sm" type="button" @click="$emit('action')">
        {{ actionLabel }}
      </button>
      <slot />
    </div>
  </div>
</template>
