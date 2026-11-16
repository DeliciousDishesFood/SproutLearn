<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import BaseTabs from '@/components/ui/BaseTabs.vue'
import BotConfigForm from '@/components/business/BotConfigForm.vue'
import XpConfigForm from '@/components/business/XpConfigForm.vue'
import { classesApi } from '@/api/classes'
import { toUserMessage } from '@/api/client'
import type { ClassDetail } from '@/api/contract'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()
const classId = computed(() => Number(route.params.classId))
const tab = ref('bot')
const detail = ref<ClassDetail | null>(null)
const errorText = ref('')

const tabs = [
  { key: 'bot', label: 'QQ 机器人' },
  { key: 'xp', label: '成长经验' },
]

onMounted(async () => {
  ui.setCurrentClassId(classId.value)
  try {
    detail.value = await classesApi.detail(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">{{ detail?.class_name ?? '班级' }}</RouterLink>
        · 设置
      </p>
      <h1>班级设置</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/classes/${classId}`">返回班级</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <BaseTabs v-model="tab" :items="tabs" />

  <BotConfigForm v-if="tab === 'bot'" :class-id="classId" />
  <XpConfigForm v-else :class-id="classId" />
</template>
