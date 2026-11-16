<script setup lang="ts">
// 数字滚动：只写 textContent，卸载/刷新时取消旧动画，避免旧值覆盖新值。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { countUp } from '@/utils/countUp'

const props = withDefaults(
  defineProps<{
    value: number
    decimals?: number
    suffix?: string
    duration?: number
  }>(),
  { decimals: 0, suffix: '', duration: 190 },
)

const el = ref<HTMLSpanElement | null>(null)
let cancel: (() => void) | null = null

function run(): void {
  cancel?.()
  cancel = null
  if (!el.value) return
  cancel = countUp(el.value, props.value, { duration: props.duration, decimals: props.decimals })
}

onMounted(run)

watch(() => [props.value, props.decimals, props.duration], run, { flush: 'post' })

onBeforeUnmount(() => {
  cancel?.()
  cancel = null
})
</script>

<template>
  <span ref="el" class="count-up" :aria-label="`${value}${suffix}`" />
</template>

<style scoped>
.count-up {
  font-variant-numeric: tabular-nums;
}
</style>
