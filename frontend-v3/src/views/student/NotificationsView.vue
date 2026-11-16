<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { notificationsApi } from '@/api/notifications'
import { toUserMessage } from '@/api/client'
import type { NotificationItem } from '@/api/contract'
import { formatDateTime } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const ui = useUiStore()
const toast = useToast()

const items = ref<NotificationItem[]>([])
const unread = ref(0)
const total = ref(0)
const page = ref(1)
const pageSize = 15
const unreadOnly = ref(false)
const loading = ref(true)
const errorText = ref('')

const hasUnread = computed(() => unread.value > 0)

function resolveTarget(item: NotificationItem): string {
  const path = item.target_path ?? ''
  if (/^\/student\/papers\/\d+$/.test(path)) {
    const paperId = path.split('/').pop()
    return `/student/papers?paper=${paperId}`
  }
  if (/^\/student\/attempts\/\d+\/result$/.test(path)) return path
  if (path === '/student/notifications') return path
  if (path.startsWith('/student/attempts/')) return path
  return '/student/notifications'
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await notificationsApi.list({
      page: page.value,
      page_size: pageSize,
      unread_only: unreadOnly.value,
    })
    items.value = result.items?.length ? result.items : result.list
    unread.value = result.unread_count
    total.value = result.total
    ui.setUnreadCount(result.unread_count)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

async function open(item: NotificationItem): Promise<void> {
  if (!item.is_read) {
    try {
      await notificationsApi.read(item.id)
      item.is_read = true
      unread.value = Math.max(0, unread.value - 1)
      ui.setUnreadCount(unread.value)
    } catch (error) {
      toast.error(toUserMessage(error))
    }
  }
  await router.push(resolveTarget(item))
}

async function readAll(): Promise<void> {
  try {
    const result = await notificationsApi.readAll()
    toast.success(`已全部标记为已读（${result.count}）`)
    await load()
  } catch (error) {
    toast.error(toUserMessage(error))
  }
}

watch(page, () => void load())
onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">我的 · 通知</p>
      <h1>通知</h1>
      <p class="page-head__lede">作业提醒、复核结果和老师公告都会出现在这里。</p>
    </div>
    <div class="page-head__actions">
      <BaseButton :disabled="!hasUnread" @click="readAll">全部已读</BaseButton>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <section class="card">
    <header class="card__head">
      <h2>消息列表</h2>
      <span class="card__meta">未读 {{ unread }} 条</span>
    </header>
    <div class="chips">
      <button
        class="chip"
        :class="{ 'is-active': !unreadOnly }"
        type="button"
        @click="unreadOnly = false; page = 1; load()"
      >
        全部
      </button>
      <button
        class="chip"
        :class="{ 'is-active': unreadOnly }"
        type="button"
        @click="unreadOnly = true; page = 1; load()"
      >
        仅未读
      </button>
    </div>

    <p v-if="loading" class="loading-line">正在读取通知…</p>
    <EmptyState v-else-if="items.length === 0" title="暂无通知" description="新的作业和公告会出现在这里。" />
    <template v-else>
      <div class="notice-list">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="notice-item"
          style="border: 0; background: transparent; text-align: left; cursor: pointer; width: 100%"
          @click="open(item)"
        >
          <span class="notice-item__dot" :class="{ 'is-read': item.is_read }" />
          <span class="notice-item__body">
            <strong>{{ item.title }}</strong>
            <p>{{ item.body }}</p>
            <span class="notice-item__meta">
              {{ formatDateTime(item.created_at) }}
              <BaseBadge v-if="!item.is_read" tone="lime">未读</BaseBadge>
            </span>
          </span>
        </button>
      </div>
      <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />
    </template>
  </section>
</template>
