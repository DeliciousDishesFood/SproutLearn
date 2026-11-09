<!-- 空态/错误态：插画 + 标题 + 说明 + 主动作，三态页面统一复用。 -->
<script setup lang="ts">
import { CircleAlert, Sprout } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    title?: string
    description?: string
    error?: boolean
    compact?: boolean
  }>(),
  {
    title: '这里还没有内容',
    description: '',
    error: false,
    compact: false,
  },
)
</script>

<template>
  <div class="app-empty" :class="{ 'app-empty--compact': compact, 'app-empty--error': error }">
    <div class="app-empty__art" aria-hidden="true">
      <CircleAlert v-if="error" :size="30" :stroke-width="1.6" />
      <Sprout v-else :size="30" :stroke-width="1.6" />
    </div>
    <h3 class="app-empty__title">{{ title }}</h3>
    <p v-if="description" class="app-empty__desc">{{ description }}</p>
    <div v-if="$slots.action" class="app-empty__action">
      <slot name="action" />
    </div>
    <slot />
  </div>
</template>

<style scoped>
.app-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  padding: var(--sp-7) var(--sp-5);
  text-align: center;
}

.app-empty--compact {
  padding: var(--sp-6) var(--sp-4);
}

.app-empty__art {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--sp-2);
  border: 1px dashed color-mix(in srgb, var(--color-primary) 30%, transparent);
  border-radius: 999px;
  color: var(--color-primary);
  background:
    radial-gradient(circle at 50% 55%, var(--color-primary-soft) 0, transparent 68%),
    var(--color-surface-alt);
}

.app-empty--error .app-empty__art {
  border-color: color-mix(in srgb, var(--color-danger) 30%, transparent);
  color: var(--color-danger);
  background:
    radial-gradient(circle at 50% 55%, color-mix(in srgb, var(--color-danger) 9%, transparent) 0, transparent 68%),
    var(--color-surface-alt);
}

.app-empty__title {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.app-empty__desc {
  max-width: 420px;
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.app-empty__action {
  margin-top: var(--sp-3);
}

.app-empty--error .app-empty__title {
  color: var(--color-danger);
}
</style>
