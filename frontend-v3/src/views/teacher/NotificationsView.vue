<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { classesApi } from '@/api/classes'
import { notificationsApi } from '@/api/notifications'
import { toUserMessage } from '@/api/client'
import type { ClassListItem, NotificationItem } from '@/api/contract'
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

const classes = ref<ClassListItem[]>([])
const announceClassId = ref('')
const announceTitle = ref('')
const announceBody = ref('')
const announcing = ref(false)
const announceError = ref('')

const canAnnounce = computed(
  () => Boolean(announceClassId.value) && announceTitle.value.trim() && announceBody.value.trim(),
)

const classOptions = computed(() =>
  classes.value.map((item) => ({ label: item.class_name, value: String(item.id) })),
)

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

/**
 * 防御性目标映射：后端现有 target_path 可能仍是 /student/...，教师侧换算到教师路由；
 * 未确认教师通知是否真的下发 /student/...，命中不了时返回 null，不跳转。
 */
function resolveTeacherTarget(path: string | null): string | null {
  if (!path) return null
  if (path.startsWith('/teacher/')) return path
  const paper = path.match(/^\/student\/papers\/(\d+)$/)
  if (paper) return `/teacher/papers/${paper[1]}`
  const attempt = path.match(/^\/student\/attempts\/(\d+)\/result$/)
  if (attempt) return `/teacher/attempts/${attempt[1]}/result`
  if (path === '/student/notifications') return '/teacher/notifications'
  return null
}

async function markRead(item: NotificationItem): Promise<void> {
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
  const target = resolveTeacherTarget(item.target_path)
  if (target) void router.push(target)
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

async function loadClasses(): Promise<void> {
  try {
    const result = await classesApi.list({ page: 1, page_size: 50 })
    classes.value = result.list
    if (result.list.length) announceClassId.value = String(result.list[0].id)
  } catch {
    // 公告所需班级列表失败时保留空态
  }
}

async function announce(): Promise<void> {
  if (!canAnnounce.value) {
    announceError.value = '请填写班级、标题和正文'
    return
  }
  announcing.value = true
  announceError.value = ''
  try {
    const result = await notificationsApi.announce(Number(announceClassId.value), {
      title: announceTitle.value.trim(),
      body: announceBody.value.trim(),
    })
    toast.success(`公告已发送给 ${result.recipient_count} 名学生`)
    announceTitle.value = ''
    announceBody.value = ''
    await load()
  } catch (error) {
    announceError.value = toUserMessage(error)
  } finally {
    announcing.value = false
  }
}

watch(page, () => void load())

onMounted(async () => {
  await Promise.all([load(), loadClasses()])
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">管理 · 消息</p>
      <h1>通知与公告</h1>
      <p class="page-head__lede">查看系统通知，向班级发送公告。</p>
    </div>
    <div class="page-head__actions">
      <BaseButton :disabled="unread === 0" @click="readAll">全部已读</BaseButton>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <div class="columns">
    <section class="card">
      <header class="card__head">
        <h2>通知</h2>
        <span class="card__meta">未读 {{ unread }} 条</span>
      </header>
      <div class="chips">
        <button class="chip" :class="{ 'is-active': !unreadOnly }" type="button" @click="unreadOnly = false; page = 1; load()">
          全部
        </button>
        <button class="chip" :class="{ 'is-active': unreadOnly }" type="button" @click="unreadOnly = true; page = 1; load()">
          仅未读
        </button>
      </div>

      <p v-if="loading" class="loading-line">正在读取通知…</p>
      <EmptyState v-else-if="items.length === 0" title="暂无通知" description="新的系统通知会出现在这里。" />
      <template v-else>
        <div class="notice-list">
          <button
            v-for="item in items"
            :key="item.id"
            type="button"
            class="notice-item"
            style="border: 0; background: transparent; text-align: left; cursor: pointer; width: 100%"
            @click="markRead(item)"
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

    <section class="card stack">
      <header class="card__head"><h2>发公告</h2></header>
      <BaseField label="班级" required>
        <BaseSelect v-model="announceClassId" :options="classOptions" placeholder="请选择班级" aria-label="公告班级" />
      </BaseField>
      <BaseField label="标题" required>
        <input v-model="announceTitle" class="input" type="text" placeholder="公告标题" />
      </BaseField>
      <BaseField label="正文" required>
        <textarea v-model="announceBody" class="input" rows="5" placeholder="要通知学生的内容" />
      </BaseField>
      <p v-if="announceError" class="form-error">{{ announceError }}</p>
      <BaseButton variant="primary" :loading="announcing" :disabled="!canAnnounce" @click="announce">
        发送公告
      </BaseButton>
      <p class="small tertiary">公告会进入班级学生的通知中心，不会自动发到 QQ 群。</p>
    </section>
  </div>
</template>
