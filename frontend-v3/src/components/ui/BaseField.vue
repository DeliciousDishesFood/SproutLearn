<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    hint?: string
    error?: string
    required?: boolean
  }>(),
  { hint: '', error: '', required: false },
)
</script>

<template>
  <label class="field">
    <span>{{ label }}<b v-if="required" aria-hidden="true"> *</b></span>
    <slot />
    <span v-if="error" class="field__error">{{ error }}</span>
    <span v-else-if="hint" class="field__hint">{{ hint }}</span>
  </label>
</template>
