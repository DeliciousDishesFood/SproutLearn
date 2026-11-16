<script setup lang="ts">
import { computed } from 'vue'
import { Check, LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'

type SaveStateValue = 'idle' | 'saving' | 'saved' | 'error'

const props = defineProps<{ state: SaveStateValue }>()
defineEmits<{ (event: 'retry'): void }>()

const label = computed(() => {
  if (props.state === 'saving') return '保存中'
  if (props.state === 'saved') return '已保存'
  if (props.state === 'error') return '保存失败'
  return '自动保存已开启'
})
</script>

<template>
  <span class="save-state" :class="`is-${state}`">
    <span class="save-state__main">
      <LoaderCircle v-if="state === 'saving'" :size="13" class="save-state__spin" aria-hidden="true" />
      <Check v-else-if="state === 'saved'" :size="13" aria-hidden="true" />
      <TriangleAlert v-else-if="state === 'error'" :size="13" aria-hidden="true" />
      <i v-else class="save-state__dot" aria-hidden="true" />
      <span class="save-state__text">{{ label }}</span>
    </span>
    <button v-if="state === 'error'" class="save-state__retry" type="button" @click="$emit('retry')">
      <RefreshCw :size="12" aria-hidden="true" />
      重试
    </button>
    <span class="sr-only" role="status" aria-live="polite">{{ label }}</span>
  </span>
</template>

<style scoped>
.save-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.save-state__main {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.is-saved {
  color: var(--text);
}

.is-saved svg {
  color: var(--lime-text);
}

.is-error {
  padding: 2px 8px 2px 7px;
  border: 1px solid var(--danger-line);
  border-radius: 6px;
  background: var(--danger-soft);
  color: var(--danger);
}

.save-state__dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--line-strong);
}

.is-saved .save-state__dot {
  background: var(--lime);
}

.save-state__spin {
  animation: save-spin 900ms linear infinite;
  color: var(--lime-text);
}

@keyframes save-spin {
  to {
    transform: rotate(360deg);
  }
}

.save-state__retry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--btn-line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.save-state__retry:hover {
  background: var(--surface-alt);
}

@media (max-width: 900px) {
  .save-state__retry {
    height: 32px;
  }
}
</style>
