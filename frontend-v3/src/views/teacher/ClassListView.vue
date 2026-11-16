<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Users } from 'lucide-vue-next'
import ClassCard from '@/components/business/ClassCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PaginationBar from '@/components/ui/PaginationBar.vue'
import { classesApi } from '@/api/classes'
import { toUserMessage } from '@/api/client'
import type { ClassListItem } from '@/api/contract'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const ui = useUiStore()
const toast = useToast()

const classes = ref<ClassListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const errorText = ref('')
const modalOpen = ref(false)
const creating = ref(false)
const createdInvite = ref('')
const form = reactive({ class_name: '', course_name: '' })

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const result = await classesApi.list({ page: page.value, page_size: pageSize })
    classes.value = result.list
    total.value = result.total
    if (classes.value.length && !ui.currentClassId) {
      ui.setCurrentClassId(classes.value[0].id)
    }
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loading.value = false
  }
}

watch(page, () => void load())

function openCreate(): void {
  form.class_name = ''
  form.course_name = ''
  createdInvite.value = ''
  modalOpen.value = true
}

async function create(): Promise<void> {
  if (!form.class_name.trim() || !form.course_name.trim()) {
    errorText.value = '班级名称和课程名称均为必填'
    return
  }
  creating.value = true
  errorText.value = ''
  try {
    const result = await classesApi.create({
      class_name: form.class_name.trim(),
      course_name: form.course_name.trim(),
    })
    createdInvite.value = result.invite_code
    ui.setCurrentClassId(result.id)
    toast.success('班级已创建')
    if (page.value === 1) {
      await load()
    } else {
      page.value = 1
    }
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    creating.value = false
  }
}

function copyInvite(): void {
  if (!createdInvite.value) return
  navigator.clipboard?.writeText(createdInvite.value).then(
    () => toast.success('邀请码已复制'),
    () => toast.error('复制失败，请手动复制'),
  )
}

function openClass(item: ClassListItem): void {
  ui.setCurrentClassId(item.id)
  void router.push(`/teacher/classes/${item.id}`)
}

onMounted(load)
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">教学 · 班级</p>
      <h1>班级</h1>
    </div>
    <div class="page-head__actions">
      <BaseButton variant="primary" @click="openCreate">
        <Plus :size="14" aria-hidden="true" />创建班级
      </BaseButton>
    </div>
  </header>

  <p v-if="errorText && !modalOpen" class="notice notice--danger">{{ errorText }}</p>

  <div v-if="loading" class="grid-3">
    <div v-for="index in 3" :key="index" class="skeleton card-skeleton" />
  </div>
  <EmptyState v-else-if="classes.length === 0" title="还没有班级" />
  <div v-else class="grid-3">
    <ClassCard v-for="item in classes" :key="item.id" :item="item" @click.prevent="openClass(item)" />
  </div>
  <PaginationBar :page="page" :page-size="pageSize" :total="total" @change="page = $event" />

  <BaseModal
    :open="modalOpen"
    title="创建班级"
    description="班级创建成功后会生成邀请码，交给学生即可加入。"
    @close="modalOpen = false"
  >
    <div v-if="!createdInvite" class="form">
      <BaseField label="班级名称" required>
        <input v-model="form.class_name" type="text" placeholder="例如 高二(2)班" />
      </BaseField>
      <BaseField label="课程名称" required>
        <input v-model="form.course_name" type="text" placeholder="例如 Python 程序设计" />
      </BaseField>
      <p v-if="errorText" class="form-error">{{ errorText }}</p>
    </div>
    <div v-else class="stack">
      <p class="notice notice--lime">班级创建成功，把邀请码发给学生即可加入。</p>
      <div class="copy-code">
        <span>邀请码</span>
        <code>{{ createdInvite }}</code>
        <button class="btn btn--sm" type="button" @click="copyInvite">复制</button>
      </div>
    </div>
    <template #footer>
      <template v-if="!createdInvite">
        <BaseButton @click="modalOpen = false">取消</BaseButton>
        <BaseButton variant="primary" :loading="creating" @click="create">创建</BaseButton>
      </template>
      <BaseButton v-else variant="primary" @click="modalOpen = false; router.push('/teacher/classes')">
        完成
      </BaseButton>
    </template>
  </BaseModal>

  <p class="foot"><Users :size="12" aria-hidden="true" /> 共 {{ total }} 个班级</p>
</template>
