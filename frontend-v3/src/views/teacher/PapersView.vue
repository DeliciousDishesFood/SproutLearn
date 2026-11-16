<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import PaperTable from '@/components/business/PaperTable.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { PaperItem } from '@/api/contract'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()
const classId = computed(() => Number(route.params.classId))

const papers = ref<PaperItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const errorText = ref('')

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await papersApi.list(classId.value, { page: page.value, page_size: pageSize })
    papers.value = result.list
    total.value = result.total
    ui.setCurrentClassId(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

watch(page, () => void load())

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> · 试卷
      </p>
      <h1>试卷</h1>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/classes/${classId}/questions`">去题库</RouterLink>
      <RouterLink class="btn btn--primary" :to="`/teacher/classes/${classId}/papers/new`">
        <Plus :size="14" aria-hidden="true" />新建试卷
      </RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="card">
    <header class="card__head">
      <h2>全部试卷</h2>
      <span class="card__meta">共 {{ total }} 份</span>
    </header>

    <div v-if="loading" class="stack">
      <div v-for="index in 5" :key="index" class="skeleton row-skeleton" />
    </div>
    <EmptyState v-else-if="papers.length === 0" title="还没有试卷" />
    <template v-else>
      <PaperTable :rows="papers" />
      <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
    </template>
  </section>

  <p class="foot">
    <BaseButton size="sm" @click="load">刷新列表</BaseButton>
  </p>
</template>
