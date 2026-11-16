<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { docsApi } from '@/api/bot'
import { toUserMessage } from '@/api/client'
import type { DocDetail, DocListItem } from '@/api/contract'
import { formatDateTime } from '@/utils/format'

const docs = ref<DocListItem[]>([])
const activeSlug = ref('')
const detail = ref<DocDetail | null>(null)
const loadingList = ref(true)
const loadingDetail = ref(false)
const errorText = ref('')

const rendered = computed(() => {
  if (!detail.value) return ''
  const markdown = detail.value.markdown?.trim()
  if (markdown) {
    const html = marked.parse(markdown, { async: false })
    return DOMPurify.sanitize(typeof html === 'string' ? html : '')
  }
  const content = detail.value.content?.trim() ?? ''
  if (!content) return '<p>这篇文档暂无正文。</p>'
  const escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br />')
  return `<p>${escaped}</p>`
})

async function openDoc(slug: string): Promise<void> {
  if (!slug) return
  activeSlug.value = slug
  loadingDetail.value = true
  errorText.value = ''
  try {
    detail.value = await docsApi.detail(slug)
  } catch (error) {
    detail.value = null
    errorText.value = toUserMessage(error)
  } finally {
    loadingDetail.value = false
  }
}

async function load(): Promise<void> {
  loadingList.value = true
  errorText.value = ''
  try {
    docs.value = await docsApi.list()
    if (docs.value.length) await openDoc(docs.value[0].slug)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loadingList.value = false
  }
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">资料 · 文档中心</p>
      <h1>文档中心</h1>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <div class="docs-layout">
    <aside class="card">
      <header class="card__head"><h2>目录</h2></header>
      <p v-if="loadingList" class="loading-line">正在读取目录…</p>
      <p v-else-if="docs.length === 0" class="notice">暂无文档。</p>
      <nav v-else class="doc-nav" style="margin-top: 10px">
        <button
          v-for="item in docs"
          :key="item.slug"
          type="button"
          class="doc-nav__item"
          :class="{ 'is-active': activeSlug === item.slug }"
          style="border: 0; background: none; text-align: left; cursor: pointer; width: 100%"
          @click="openDoc(item.slug)"
        >
          <span>{{ item.title }}</span>
          <em>{{ item.updated_at ? formatDateTime(item.updated_at) : '—' }}</em>
        </button>
      </nav>
    </aside>

    <section class="card">
      <p v-if="loadingDetail" class="loading-line">正在读取正文…</p>
      <template v-else-if="detail">
        <header class="card__head" style="display: block">
          <h2 style="font-size: 18px">{{ detail.title }}</h2>
          <p class="small muted" style="margin-top: 4px">{{ detail.summary }}</p>
        </header>
        <hr class="divider" style="margin: 12px 0 16px" />
        <article class="doc-body" v-html="rendered" />
      </template>
      <p v-else class="empty-block">请选择左侧文档。</p>
    </section>
  </div>
</template>
