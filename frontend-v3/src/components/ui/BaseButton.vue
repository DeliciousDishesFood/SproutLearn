<script setup lang="ts">
import { computed } from 'vue'
import { Loader2 } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'md' | 'sm'
    block?: boolean
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit' | 'reset'
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    block: false,
    loading: false,
    disabled: false,
    type: 'button',
  },
)

defineEmits<{ (event: 'click', payload: MouseEvent): void }>()

const classes = computed(() => [
  'btn',
  {
    'btn--primary': props.variant === 'primary',
    'btn--ghost': props.variant === 'ghost',
    'btn--danger': props.variant === 'danger',
    'btn--sm': props.size === 'sm',
    'btn--block': props.block,
  },
])
</script>

<template>
  <button
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    @click="$emit('click', $event)"
  >
    <Loader2 v-if="loading" :size="14" class="spin" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.spin {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
