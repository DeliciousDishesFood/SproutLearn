<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: string
    items: Array<{ key: string; label: string }>
  }>(),
  {},
)

defineEmits<{ (event: 'update:modelValue', value: string): void }>()
</script>

<template>
  <div class="tabs" role="tablist">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      role="tab"
      class="tabs__item"
      :class="{ 'is-active': item.key === modelValue }"
      :aria-selected="item.key === modelValue"
      @click="$emit('update:modelValue', item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>
