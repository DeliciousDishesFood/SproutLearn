<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { banksApi } from '@/api/banks'
import { toUserMessage } from '@/api/client'
import type { QuestionBank } from '@/api/contract'
import { formatDateTime } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const ui = useUiStore()
const toast = useToast()
const classId = computed(() => Number(route.params.classId))

const banks = ref<QuestionBank[]>([])
const loading = ref(true)
const errorText = ref('')
const modalOpen = ref(false)
const editing = ref<QuestionBank | null>(null)
const saving = ref(false)
const form = reactive({ name: '', description: '' })

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    banks.value = await banksApi.list(classId.value)
    ui.setCurrentClassId(classId.value)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.name = ''
  form.description = ''
  errorText.value = ''
  modalOpen.value = true
}

function openEdit(bank: QuestionBank): void {
  editing.value = bank
  form.name = bank.name
  form.description = bank.description ?? ''
  errorText.value = ''
  modalOpen.value = true
}

async function save(): Promise<void> {
  if (!form.name.trim()) {
    errorText.value = '题库名称不能为空'
    return
  }
  saving.value = true
  errorText.value = ''
  try {
    if (editing.value) {
      await banksApi.update(editing.value.id, {
        name: form.name.trim(),
        description: form.description.trim() || null,
      })
      toast.success('题库已更新')
    } else {
      await banksApi.create(classId.value, {
        name: form.name.trim(),
        description: form.description.trim() || null,
      })
      toast.success('题库已创建')
    }
    modalOpen.value = false
    await load()
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    saving.value = false
  }
}

async function remove(bank: QuestionBank): Promise<void> {
  if (!window.confirm(`确定删除题库「${bank.name}」吗？`)) return
  try {
    await banksApi.remove(bank.id)
    toast.success('题库已删除')
    await load()
  } catch (error) {
    toast.error(toUserMessage(error))
  }
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> · 题库
      </p>
      <h1>题库</h1>
      <p class="page-head__lede">按知识点分库管理题目，组卷时可从指定题库抽题。</p>
    </div>
    <div class="page-head__actions">
      <BaseButton variant="primary" @click="openCreate">
        <Plus :size="14" aria-hidden="true" />新建题库
      </BaseButton>
    </div>
  </header>

  <p v-if="errorText && !modalOpen" class="notice notice--danger">{{ errorText }}</p>

  <p v-if="loading" class="loading-line">正在读取题库…</p>
  <EmptyState
    v-else-if="banks.length === 0"
    title="还没有题库"
    description="先建一个题库，再把题目导入或手动维护到题库里。"
    action-label="新建题库"
    @action="openCreate"
  />
  <div v-else class="grid-3">
    <article v-for="bank in banks" :key="bank.id" class="card stack">
      <header class="card__head">
        <h2>{{ bank.name }}</h2>
        <span class="badge badge--lime">{{ bank.question_count }} 题</span>
      </header>
      <p class="small muted" style="min-height: 18px">{{ bank.description || '暂无描述' }}</p>
      <p class="small tertiary">更新于 {{ formatDateTime(bank.updated_at) }}</p>
      <div class="row row--wrap">
        <RouterLink
          class="btn btn--sm"
          :to="`/teacher/classes/${classId}/questions?bank_id=${bank.id}`"
        >
          查看题目
        </RouterLink>
        <button class="btn btn--sm" type="button" @click="openEdit(bank)">重命名</button>
        <button class="btn btn--sm btn--danger" type="button" @click="remove(bank)">删除</button>
      </div>
    </article>
  </div>

  <BaseModal
    :open="modalOpen"
    :title="editing ? '编辑题库' : '新建题库'"
    description="题库名称在班级内唯一。"
    @close="modalOpen = false"
  >
    <div class="form">
      <BaseField label="题库名称" required>
        <input v-model="form.name" class="input" type="text" placeholder="例如 函数与导数" />
      </BaseField>
      <BaseField label="描述（选填）">
        <textarea v-model="form.description" class="input" placeholder="这个题库覆盖哪些知识点" />
      </BaseField>
      <p v-if="errorText" class="form-error">{{ errorText }}</p>
    </div>
    <template #footer>
      <BaseButton @click="modalOpen = false">取消</BaseButton>
      <BaseButton variant="primary" :loading="saving" @click="save">保存</BaseButton>
    </template>
  </BaseModal>
</template>
