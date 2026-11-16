<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { knowledgeApi } from '@/api/knowledge'
import { toUserMessage } from '@/api/client'
import type { KnowledgeChunk, KnowledgeDocDetail } from '@/api/contract'
import { DOC_STATUS_LABEL, docStatusTone, formatDateTime, formatFileSize } from '@/utils/format'

const route = useRoute()
const classId = computed(() => Number(route.params.classId))
const docId = computed(() => Number(route.params.docId))

const detail = ref<KnowledgeDocDetail | null>(null)
const chunks = ref<KnowledgeChunk[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 8
const loading = ref(true)
const errorText = ref('')

async function loadDetail(): Promise<void> {
  try {
    detail.value = await knowledgeApi.detail(docId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
}

async function loadChunks(): Promise<void> {
  try {
    const result = await knowledgeApi.chunks(docId.value, { page: page.value, page_size: pageSize })
    chunks.value = result.list
    total.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  }
}

watch(page, () => void loadChunks())

onMounted(async () => {
  loading.value = true
  await Promise.all([loadDetail(), loadChunks()])
  loading.value = false
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> ·
        <RouterLink :to="`/teacher/classes/${classId}/knowledge`">知识库</RouterLink> ·
        文档详情
      </p>
      <h1>{{ detail?.title ?? '文档详情' }}</h1>
      <p class="page-head__lede">{{ detail?.file_name ?? '—' }}</p>
    </div>
    <div class="page-head__actions">
      <RouterLink class="btn" :to="`/teacher/classes/${classId}/knowledge`">返回列表</RouterLink>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section v-if="detail" class="card stack">
    <div class="row row--between row--wrap">
      <div class="kv">
        <span>状态：<BaseBadge :tone="docStatusTone(detail.status)">{{ DOC_STATUS_LABEL[detail.status] }}</BaseBadge></span>
        <span>切片：<b>{{ detail.chunk_count }}</b></span>
        <span>页数：<b>{{ detail.page_count ?? '—' }}</b></span>
        <span>大小：<b>{{ formatFileSize(detail.file_size) }}</b></span>
        <span>上传：<b>{{ formatDateTime(detail.created_at) }}</b></span>
      </div>
    </div>
    <p v-if="detail.error_message" class="notice notice--danger">
      解析失败原因：{{ detail.error_message }}
    </p>
    <p v-else-if="detail.status !== 2" class="notice">
      文档仍在处理中，可稍后刷新查看切片。
    </p>
  </section>

  <section class="card">
    <header class="card__head">
      <h2>文档切片</h2>
      <span class="card__meta">共 {{ total }} 个</span>
    </header>

    <p v-if="loading" class="loading-line">正在读取切片…</p>
    <EmptyState
      v-else-if="chunks.length === 0"
      title="暂无可用切片"
      description="文档解析完成后，切片会出现在这里。"
    />
    <div v-else class="stack" style="margin-top: 12px">
      <article v-for="chunk in chunks" :key="chunk.id" class="notice" style="padding: 12px 14px">
        <div class="row row--between row--wrap">
          <span class="strong">
            #{{ chunk.chunk_index }}
            <template v-if="chunk.chapter_title"> · {{ chunk.chapter_title }}</template>
          </span>
          <span class="small tertiary">
            <template v-if="chunk.page_no">第 {{ chunk.page_no }} 页 · </template>
            {{ chunk.char_count }} 字
          </span>
        </div>
        <p style="margin-top: 6px; white-space: pre-wrap; line-height: 1.7">{{ chunk.content }}</p>
      </article>
      <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
    </div>
  </section>
</template>
