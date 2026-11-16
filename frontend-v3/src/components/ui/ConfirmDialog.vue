<script setup lang="ts">
// 产品内确认弹窗：复用 BaseModal，由调用方传入对象名、后果与语气。
import { computed } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    target?: string
    confirmLabel?: string
    cancelLabel?: string
    tone?: 'danger' | 'primary'
    loading?: boolean
  }>(),
  {
    target: '',
    confirmLabel: '确认',
    cancelLabel: '取消',
    tone: 'primary',
    loading: false,
  },
)

const emit = defineEmits<{ (event: 'confirm'): void; (event: 'cancel'): void }>()

const confirmVariant = computed(() => (props.tone === 'danger' ? 'danger' : 'primary'))
</script>

<template>
  <BaseModal :open="open" :title="title" :close-on-mask="!loading" @close="emit('cancel')">
    <div class="confirm">
      <p v-if="target" class="confirm__target">{{ target }}</p>
      <p class="confirm__message">{{ message }}</p>
    </div>
    <template #footer>
      <BaseButton :disabled="loading" @click="emit('cancel')">{{ cancelLabel }}</BaseButton>
      <BaseButton :variant="confirmVariant" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.confirm {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.confirm__target {
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.5;
  word-break: break-word;
}

.confirm__message {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}
</style>
