<script setup lang="ts">
// 打字机：文本由接口提供（不拉 hitokoto、不循环）；reduced-motion 直接显示全文。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ text: string; speed?: number }>(), { speed: 42 })

const shown = ref('')
let timer: number | null = null

function stop(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function start(): void {
  stop()
  shown.value = ''
  if (!props.text) return
  if (reducedMotion()) {
    shown.value = props.text
    return
  }
  let index = 0
  timer = window.setInterval(() => {
    index += 1
    shown.value = props.text.slice(0, index)
    if (index >= props.text.length) stop()
  }, props.speed)
}

onMounted(start)
watch(() => props.text, start)
onBeforeUnmount(stop)
</script>

<template>
  <span class="typewriter" :aria-label="text">
    <span aria-hidden="true">{{ shown }}</span>
    <i v-if="shown.length < text.length" class="typewriter__caret" aria-hidden="true">|</i>
  </span>
</template>

<style scoped>
.typewriter {
  display: inline;
}

.typewriter__caret {
  margin-left: 1px;
  color: var(--lime-text);
  font-style: normal;
  animation: caret-blink 900ms steps(1) infinite;
}

@keyframes caret-blink {
  50% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .typewriter__caret {
    display: none;
    animation: none;
  }
}
</style>
