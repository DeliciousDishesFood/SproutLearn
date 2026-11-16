<script setup lang="ts">
import { computed } from 'vue'
import CountUpNumber from '@/components/ui/CountUpNumber.vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    tag?: string
    tagTone?: 'lime' | 'soft' | 'warn'
  }>(),
  { hint: '', tag: '', tagTone: 'soft' },
)

// 数字走滚动动效；字符串（如「79%」）保持原样。
const isNumeric = computed(() => typeof props.value === 'number' && Number.isFinite(props.value))
</script>

<template>
  <article class="stat">
    <div class="stat__label">
      <span v-if="$slots.icon" class="stat__icon" aria-hidden="true"><slot name="icon" /></span>
      {{ label }}
    </div>
    <div class="stat__row">
      <span class="stat__value">
        <CountUpNumber v-if="isNumeric" :value="Number(value)" />
        <template v-else>{{ value }}</template>
      </span>
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
