<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { workbenchApi } from '@/api/workbench'
import { toUserMessage } from '@/api/client'
import type { XpConfigItem } from '@/api/contract'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ classId: number }>()
const toast = useToast()

const items = ref<XpConfigItem[]>([])
const draft = ref<Record<string, boolean>>({})
const loading = ref(false)
const saving = ref(false)
const errorText = ref('')

const changed = computed(() =>
  items.value.some((item) => draft.value[item.code] !== item.enabled),
)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await workbenchApi.xpConfig(props.classId)
    items.value = result.items ?? result.list ?? []
    draft.value = Object.fromEntries(items.value.map((item) => [item.code, item.enabled]))
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  saving.value = true
  errorText.value = ''
  try {
    const payload = items.value.map((item) => ({
      code: item.code,
      enabled: Boolean(draft.value[item.code]),
    }))
    const result = await workbenchApi.updateXpConfig(props.classId, payload)
    items.value = result.items ?? result.list ?? items.value
    draft.value = Object.fromEntries(items.value.map((item) => [item.code, item.enabled]))
    toast.success('经验规则已保存')
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="card stack">
    <header class="card__head">
      <h2>成长经验规则</h2>
      <span class="card__meta">全局等级定义，班级只控制是否发放</span>
    </header>

    <p v-if="loading" class="loading-line">正在读取经验规则…</p>
    <p v-else-if="errorText" class="form-error">{{ errorText }}</p>
    <template v-else>
      <p v-if="items.length === 0" class="notice">当前班级暂无经验规则。</p>
      <div v-for="item in items" :key="item.code" class="toggle-row">
        <span class="toggle-row__text">
          <strong>{{ item.name }}</strong>
          <span>{{ item.code }} · 基础 {{ item.base_xp }} XP{{ item.overridden ? ' · 已覆盖' : '' }}</span>
        </span>
        <label class="switch">
          <input v-model="draft[item.code]" type="checkbox" :aria-label="item.name" />
          <i />
        </label>
      </div>
      <div class="row">
        <BaseButton variant="primary" :loading="saving" :disabled="!changed" @click="save">
          保存经验规则
        </BaseButton>
        <span v-if="changed" class="small tertiary">有未保存的修改</span>
      </div>
    </template>
  </section>
</template>
