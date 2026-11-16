<script setup lang="ts">
// 自定义勾选框：隐藏原生 input 保留键盘/无障碍语义，视觉用 SVG 方块。
import { Check } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    disabled?: boolean
    ariaLabel?: string
  }>(),
  { disabled: false, ariaLabel: '' },
)

const model = defineModel<boolean>({ default: false })

function onChange(event: Event): void {
  model.value = (event.target as HTMLInputElement).checked
}
</script>

<template>
  <span class="checkbox" :class="{ 'is-checked': model, 'is-disabled': disabled }">
    <input
      class="checkbox__input"
      type="checkbox"
      :checked="model"
      :disabled="disabled"
      :aria-label="ariaLabel || undefined"
      @change="onChange"
    />
    <span class="checkbox__box" aria-hidden="true">
      <Check v-if="model" :size="11" :stroke-width="3" />
    </span>
  </span>
</template>
