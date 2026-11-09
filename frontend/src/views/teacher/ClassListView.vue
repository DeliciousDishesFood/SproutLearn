<!-- 班级列表：卡片展示全部班级 + 新建班级表单（40907 就地上报）。 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, Plus, RefreshCw } from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppModal from '@/components/base/AppModal.vue'
import AppSkeleton from '@/components/base/AppSkeleton.vue'
import ClassCard from '@/components/business/ClassCard.vue'
import { isApiError } from '@/api/client'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import {
  DASHBOARD_PAGE_SIZE,
  ERROR_CODE,
  ERROR_MESSAGES,
  MAX_CLASSES_PER_TEACHER,
  TEXT_FIELD_MAX_LEN,
} from '@/utils/constants'

const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const createOpen = ref(false)
const creating = ref(false)
const formError = ref('')
const form = reactive({
  className: '',
  courseName: '',
})
const errors = reactive<Record<string, string>>({
  className: '',
  courseName: '',
})

const classCount = computed(() => classStore.classes.filter((item) => item.status === 1).length)
const reachedLimit = computed(() => classCount.value >= MAX_CLASSES_PER_TEACHER)

async function loadClasses(): Promise<void> {
  try {
    await classStore.fetchClasses({ page: 1, pageSize: DASHBOARD_PAGE_SIZE })
  } catch {
    // store.error 已保存可展示文案
  }
}

function openCreate(): void {
  formError.value = ''
  errors.className = ''
  errors.courseName = ''
  form.className = ''
  form.courseName = ''
  createOpen.value = true
}

function closeCreate(): void {
  if (creating.value) return
  createOpen.value = false
}

function clearCreateField(field: 'className' | 'courseName'): void {
  errors[field] = ''
  formError.value = ''
}

function validate(): boolean {
  errors.className = ''
  errors.courseName = ''
  formError.value = ''

  const className = form.className.trim()
  const courseName = form.courseName.trim()

  if (!className) {
    errors.className = '请输入班级名称'
  } else if (className.length > TEXT_FIELD_MAX_LEN) {
    errors.className = `班级名称不能超过 ${TEXT_FIELD_MAX_LEN} 个字符`
  }

  if (!courseName) {
    errors.courseName = '请输入课程名称'
  } else if (courseName.length > TEXT_FIELD_MAX_LEN) {
    errors.courseName = `课程名称不能超过 ${TEXT_FIELD_MAX_LEN} 个字符`
  }

  return !errors.className && !errors.courseName
}

async function submitCreate(): Promise<void> {
  if (creating.value || !validate()) return
  creating.value = true
  try {
    const created = await classStore.createClass({
      class_name: form.className.trim(),
      course_name: form.courseName.trim(),
    })
    ui.success(`班级「${created.class_name}」已创建`)
    createOpen.value = false
    await router.push(`/teacher/classes/${created.id}`)
  } catch (err) {
    if (isApiError(err)) {
      if (err.code === ERROR_CODE.CLASS_LIMIT) {
        formError.value = ERROR_MESSAGES[ERROR_CODE.CLASS_LIMIT]
      } else if (err.code === ERROR_CODE.VALIDATION) {
        formError.value = '班级名称或课程名称不符合要求，请检查长度后重试'
      } else {
        formError.value = err.friendlyMessage
      }
    } else {
      formError.value = '网络连接失败，请检查网络后重试'
    }
  } finally {
    creating.value = false
  }
}

onMounted(loadClasses)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">CLASSES</p>
        <h2 class="page-title">我的班级</h2>
        <p class="page-subtitle">每个班级拥有永久不变的班级编号，以及可随时重置的邀请码。</p>
      </div>
      <AppButton
        variant="primary"
        :disabled="reachedLimit"
        :title="reachedLimit ? `已达到 ${MAX_CLASSES_PER_TEACHER} 个班级上限` : undefined"
        @click="openCreate"
      >
        <Plus :size="16" :stroke-width="2" aria-hidden="true" />
        新建班级
      </AppButton>
    </header>

    <p v-if="reachedLimit" class="form-hint limit-hint">
      你已创建 {{ classCount }} 个班级，达到 {{ MAX_CLASSES_PER_TEACHER }} 个上限。归档旧班后可继续创建。
    </p>

    <div v-if="classStore.loading" class="class-grid" aria-busy="true">
      <AppSkeleton v-for="index in 3" :key="index" variant="card" />
    </div>

    <div v-else-if="classStore.error" class="panel">
      <AppEmpty error title="班级列表暂时无法加载" :description="classStore.error">
        <template #action>
          <AppButton variant="secondary" @click="loadClasses">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </div>

    <div v-else-if="classStore.classes.length > 0" class="class-grid">
      <ClassCard
        v-for="classItem in classStore.classes"
        :key="classItem.id"
        :class-item="classItem"
        class="fade-up"
      />
    </div>

    <div v-else class="panel">
      <AppEmpty
        title="还没有班级"
        description="创建第一个班级，把邀请码发给学生，课堂知识库就可以开始生长了。"
      >
        <template #action>
          <AppButton variant="primary" @click="openCreate">
            <Plus :size="16" :stroke-width="2" />
            创建第一个班级
          </AppButton>
        </template>
      </AppEmpty>
    </div>

    <AppModal
      v-model="createOpen"
      title="新建班级"
      description="班级名称与课程名称会展示在学生端，创建后可随时使用邀请码邀请学生。"
      confirm-text="创建班级"
      :confirm-loading="creating"
      @confirm="submitCreate"
    >
      <form class="create-form" novalidate @submit.prevent="submitCreate">
        <AppInput
          v-model="form.className"
          label="班级名称"
          placeholder="例如 2026级计算机1班"
          :maxlength="TEXT_FIELD_MAX_LEN"
          :error="errors.className"
          @update:model-value="clearCreateField('className')"
        />
        <AppInput
          v-model="form.courseName"
          label="课程名称"
          placeholder="例如 计算机网络"
          :maxlength="TEXT_FIELD_MAX_LEN"
          :error="errors.courseName"
          hint="创建后会生成 6 位班级编号与首个邀请码。"
          @update:model-value="clearCreateField('courseName')"
        />
        <p v-if="formError" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ formError }}</span>
        </p>
        <button class="visually-hidden" type="submit">提交</button>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.class-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-4);
}

.limit-hint {
  margin-bottom: var(--sp-4);
  color: var(--color-warning);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

@media (max-width: 1180px) {
  .class-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .class-grid {
    grid-template-columns: 1fr;
  }
}
</style>
