<!-- 文档中心：左侧 manifest 目录 + 前端标题过滤，右侧 Markdown 渲染（净化后 v-html）。 -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, BookOpen, RefreshCw } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import { isApiError } from '@/api/client'
import { docsApi } from '@/api/docs'
import type { DocDetail, DocListItem } from '@/api/types'
import { renderMarkdown } from '@/utils/markdown'

const route = useRoute()

const manifest = ref<DocListItem[]>([])
const loading = ref(false)
const loadError = ref('')
const keyword = ref('')

const detail = ref<DocDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const bodyEl = ref<HTMLElement | null>(null)

const activeSlug = computed(() => String(route.params.slug || ''))
const filteredDocs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return manifest.value
  return manifest.value.filter(
    (doc) =>
      doc.title.toLowerCase().includes(query) ||
      doc.slug.toLowerCase().includes(query),
  )
})
const rendered = computed(() => {
  if (!detail.value) return ''
  const html = renderMarkdown(detail.value.content || detail.value.markdown)
  // 正文首个 H1 与页头标题重复，去掉以免出现两个同名大标题。
  return html.replace(/^\s*<h1[^>]*>[\s\S]*?<\/h1>\s*/i, '')
})

function friendlyError(err: unknown, fallback: string): string {
  if (isApiError(err)) return err.friendlyMessage || fallback
  return fallback
}

async function loadManifest(): Promise<void> {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    manifest.value = await docsApi.list()
  } catch (err) {
    loadError.value = friendlyError(err, '文档目录暂时无法加载')
  } finally {
    loading.value = false
  }
}

async function loadDetail(slug: string): Promise<void> {
  if (!slug) {
    detail.value = null
    detailError.value = ''
    return
  }
  detailLoading.value = true
  detailError.value = ''
  try {
    detail.value = await docsApi.detail(slug)
  } catch (err) {
    detail.value = null
    detailError.value = friendlyError(err, '文档不存在或暂时无法加载')
  } finally {
    detailLoading.value = false
  }
}

/** marked 不生成标题 id，这里在净化后的 DOM 上补锚点，支持文内跳转。 */
async function decorateHeadings(): Promise<void> {
  await nextTick()
  const root = bodyEl.value
  if (!root) return
  const used = new Set<string>()
  root.querySelectorAll<HTMLElement>('h1, h2, h3, h4').forEach((heading) => {
    if (heading.id) {
      used.add(heading.id)
      return
    }
    const base =
      (heading.textContent || '')
        .trim()
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, '-')
        .replace(/^-+|-+$/g, '') || 'section'
    let id = base
    let index = 2
    while (used.has(id)) {
      id = `${base}-${index}`
      index += 1
    }
    used.add(id)
    heading.id = id
  })
}

watch(activeSlug, (slug) => {
  void loadDetail(slug)
})

watch(rendered, (html) => {
  if (html) void decorateHeadings()
})

onMounted(async () => {
  await loadManifest()
  if (activeSlug.value) await loadDetail(activeSlug.value)
})
</script>

<template>
  <div class="docs-page">
    <aside class="docs-sidebar">
      <div class="docs-sidebar__head">
        <p class="eyebrow">DOCUMENTATION</p>
        <h1 class="docs-sidebar__title">文档中心</h1>
        <p class="docs-sidebar__note">机器人、题库导入与判分复核的操作说明。</p>
      </div>

      <AppInput v-model="keyword" type="search" placeholder="搜索文档标题" />

      <p v-if="loading" class="docs-sidebar__status">正在加载目录…</p>
      <p v-else-if="loadError" class="docs-sidebar__status docs-sidebar__status--error">
        {{ loadError }}
        <button type="button" class="docs-retry" @click="loadManifest">
          <RefreshCw :size="12" :stroke-width="1.9" />
          重试
        </button>
      </p>

      <nav v-else-if="manifest.length > 0" class="docs-list" aria-label="文档目录">
        <RouterLink
          v-for="doc in filteredDocs"
          :key="doc.slug"
          :to="`/docs/${doc.slug}`"
          class="docs-list__item"
          active-class="docs-list__item--active"
        >
          <span class="docs-list__title">{{ doc.title }}</span>
          <span class="docs-list__summary">{{ doc.summary }}</span>
        </RouterLink>
        <p v-if="filteredDocs.length === 0" class="docs-sidebar__status">没有匹配的文档</p>
      </nav>

      <p v-else class="docs-sidebar__status">文档整理中</p>
    </aside>

    <section class="docs-content">
      <div v-if="!activeSlug" class="panel docs-welcome">
        <div v-if="manifest.length === 0 && !loading" class="docs-welcome__copy">
          <span class="docs-welcome__icon" aria-hidden="true">
            <BookOpen :size="22" :stroke-width="1.7" />
          </span>
          <h2 class="docs-welcome__title">文档整理中</h2>
          <p>文档正文由运营与开发直接维护，整理完成后会出现在左侧目录。</p>
        </div>
        <div v-else class="docs-welcome__copy">
          <span class="docs-welcome__icon" aria-hidden="true">
            <BookOpen :size="22" :stroke-width="1.7" />
          </span>
          <h2 class="docs-welcome__title">从左侧选择一篇文档</h2>
          <p>先读一篇配置说明，再动手；也可以从 QQ 机器人配置开始。</p>
          <RouterLink class="docs-welcome__link" to="/docs/qq-bot-setup">
            打开「QQ 机器人配置」
            <ArrowRight :size="14" :stroke-width="1.9" />
          </RouterLink>
        </div>
      </div>

      <div v-else-if="detailLoading" class="panel panel-body" aria-busy="true">
        <AppSkeleton variant="title" />
        <AppSkeleton variant="text" :rows="6" />
      </div>

      <div v-else-if="detailError" class="panel">
        <AppEmpty error title="文档暂时无法打开" :description="detailError">
          <template #action>
            <div class="docs-error-actions">
              <AppButton variant="secondary" @click="loadDetail(activeSlug)">
                <RefreshCw :size="14" :stroke-width="1.8" />
                重新加载
              </AppButton>
              <RouterLink to="/docs">
                <AppButton variant="ghost">返回目录</AppButton>
              </RouterLink>
            </div>
          </template>
        </AppEmpty>
      </div>

      <article v-else-if="detail" class="panel docs-article">
        <header class="docs-article__head">
          <p class="eyebrow">DOC</p>
          <h1 class="docs-article__title">{{ detail.title }}</h1>
          <p class="docs-article__summary">{{ detail.summary }}</p>
          <p v-if="detail.updated_at" class="docs-article__meta">更新于 {{ detail.updated_at }}</p>
        </header>
        <div ref="bodyEl" class="docs-article__body" v-html="rendered" />
      </article>
    </section>
  </div>
</template>

<style scoped>
.docs-page {
  display: grid;
  grid-template-columns: 272px minmax(0, 1fr);
  gap: var(--sp-5);
  align-items: start;
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: var(--sp-5) var(--sp-6) var(--sp-7);
}

.docs-sidebar {
  position: sticky;
  top: calc(var(--topbar-h) + var(--sp-4));
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
}

.docs-sidebar__head {
  padding: var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--color-accent) 10%, transparent) 0, transparent 46%),
    var(--color-surface);
  box-shadow: var(--shadow-1);
}

.docs-sidebar__title {
  font-size: var(--fs-xl);
}

.docs-sidebar__note {
  margin-top: var(--sp-1);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.docs-sidebar__status {
  padding: var(--sp-3);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.docs-sidebar__status--error {
  color: var(--color-danger);
}

.docs-retry {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: var(--sp-2);
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.docs-list__item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: var(--sp-3);
  border: 1px solid transparent;
  border-left: 2px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--color-text);
  transition: background-color 160ms ease-out, border-color 160ms ease-out;
}

.docs-list__item:hover {
  background: var(--color-surface);
  border-color: var(--color-border);
}

.docs-list__item--active {
  border-color: var(--color-border);
  border-left-color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
}

.docs-list__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.docs-list__item--active .docs-list__title {
  color: var(--color-primary);
}

.docs-list__summary {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.docs-content {
  min-width: 0;
}

.docs-welcome {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 420px;
  padding: var(--sp-6);
}

.docs-welcome__copy {
  max-width: 420px;
  text-align: center;
}

.docs-welcome__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  margin-bottom: var(--sp-3);
  border-radius: var(--radius-md);
  color: var(--color-accent);
  background: var(--color-primary);
}

.docs-welcome__title {
  font-size: var(--fs-xl);
}

.docs-welcome__copy p {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.docs-welcome__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--sp-4);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.docs-error-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.docs-article {
  padding: var(--sp-6);
}

.docs-article__head {
  padding-bottom: var(--sp-4);
  margin-bottom: var(--sp-5);
  border-bottom: 1px solid var(--color-border);
}

.docs-article__title {
  margin-top: var(--sp-1);
  font-size: var(--fs-2xl);
  line-height: 1.35;
}

.docs-article__summary {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
}

.docs-article__meta {
  margin-top: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}

.docs-article__body {
  color: var(--color-text);
  font-size: var(--fs-base);
  line-height: 1.8;
  overflow-wrap: anywhere;
}

.docs-article__body :deep(h1),
.docs-article__body :deep(h2),
.docs-article__body :deep(h3),
.docs-article__body :deep(h4) {
  margin: 1.6em 0 0.6em;
  line-height: 1.4;
  scroll-margin-top: calc(var(--topbar-h) + var(--sp-4));
}

.docs-article__body :deep(h1) {
  font-size: var(--fs-2xl);
}

.docs-article__body :deep(h2) {
  padding-bottom: 6px;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--fs-xl);
}

.docs-article__body :deep(h3) {
  font-size: var(--fs-lg);
}

.docs-article__body :deep(h4) {
  font-size: var(--fs-base);
}

.docs-article__body :deep(p) {
  margin: 0.7em 0;
}

.docs-article__body :deep(ul),
.docs-article__body :deep(ol) {
  margin: 0.7em 0;
  padding-left: 1.4em;
}

.docs-article__body :deep(li) {
  margin: 0.3em 0;
}

.docs-article__body :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.docs-article__body :deep(blockquote) {
  margin: 1em 0;
  padding: var(--sp-3) var(--sp-4);
  border-left: 3px solid var(--color-primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
}

.docs-article__body :deep(blockquote p) {
  margin: 0.2em 0;
}

.docs-article__body :deep(code) {
  padding: 1px 5px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-surface-alt);
  font-family: var(--font-mono);
  font-size: 0.92em;
}

.docs-article__body :deep(pre) {
  margin: 1em 0;
  padding: var(--sp-3) var(--sp-4);
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  line-height: 1.6;
}

.docs-article__body :deep(pre code) {
  padding: 0;
  border: 0;
  background: transparent;
  font-size: var(--fs-sm);
}

.docs-article__body :deep(table) {
  width: 100%;
  margin: 1em 0;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.docs-article__body :deep(th),
.docs-article__body :deep(td) {
  padding: 9px var(--sp-3);
  border: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}

.docs-article__body :deep(th) {
  background: var(--color-surface-alt);
  font-weight: 600;
  white-space: nowrap;
}

.docs-article__body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
}

.docs-article__body :deep(hr) {
  margin: 1.6em 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 1023px) {
  .docs-page {
    grid-template-columns: 1fr;
    padding: var(--sp-4);
  }

  .docs-sidebar {
    position: static;
  }

  .docs-list {
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: var(--sp-1);
  }

  .docs-list__item {
    min-width: 200px;
  }

  .docs-article {
    padding: var(--sp-4);
  }
}
</style>
