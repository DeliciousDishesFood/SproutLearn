<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseField from '@/components/ui/BaseField.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { questionsApi } from '@/api/questions'
import { banksApi } from '@/api/banks'
import { papersApi } from '@/api/papers'
import { toUserMessage } from '@/api/client'
import type { PaperCreatePayload, QuestionBank, QuestionItem } from '@/api/contract'
import { QUESTION_TYPE_LABEL, formatAnswer } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const toast = useToast()
const classId = computed(() => Number(route.params.classId))

const banks = ref<QuestionBank[]>([])
const questions = ref<QuestionItem[]>([])
const loadingBanks = ref(true)
const loadingQuestions = ref(false)
const loadingMore = ref(false)
const questionPage = ref(1)
const questionTotal = ref(0)
const questionKeyword = ref('')
const submitting = ref(false)
const errorText = ref('')

const form = reactive({
  title: '',
  mode: 'fixed' as 'fixed' | 'random',
  kind: 'practice' as 'practice' | 'homework' | 'exam',
  duration_minutes: 30,
  shuffle: false,
  blank_mode: 'smart' as 'smart' | 'strict',
  due_at: '',
  bank_id: '',
  question_ids: [] as number[],
  bank_ids: [] as number[],
  knowledge_tag: '',
  difficulty: '' as '' | 'easy' | 'medium' | 'hard',
  count: 10,
})

const selectedCount = computed(() => form.question_ids.length)
const selectedBank = computed(() => banks.value.find((bank) => String(bank.id) === form.bank_id) ?? null)

const kindOptions = [
  { label: '练习', value: 'practice' },
  { label: '作业', value: 'homework' },
  { label: '考试', value: 'exam' },
]
const modeOptions = [
  { label: '固定题目', value: 'fixed' },
  { label: '随机抽题', value: 'random' },
]
const blankModeOptions = [
  { label: '智能判定', value: 'smart' },
  { label: '严格判定', value: 'strict' },
]
const shuffleOptions = [
  { label: '不打乱', value: false },
  { label: '打乱题序', value: true },
]
const difficultyOptions = [
  { label: '不限', value: '' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]
const bankOptions = computed(() =>
  banks.value.map((bank) => ({ label: `${bank.name}（${bank.question_count} 题）`, value: String(bank.id) })),
)

async function loadBanks(): Promise<void> {
  loadingBanks.value = true
  try {
    banks.value = await banksApi.list(classId.value)
    ui.setCurrentClassId(classId.value)
    if (banks.value.length) {
      form.bank_id = String(banks.value[0].id)
      form.bank_ids = [banks.value[0].id]
    }
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loadingBanks.value = false
  }
}

async function loadQuestions(reset = true): Promise<void> {
  if (form.mode !== 'fixed' || !form.bank_id) {
    questions.value = []
    questionTotal.value = 0
    questionPage.value = 1
    return
  }
  if (reset) questionPage.value = 1
  loadingQuestions.value = true
  loadingMore.value = !reset
  try {
    const result = await questionsApi.list(classId.value, {
      bank_id: Number(form.bank_id),
      keyword: questionKeyword.value.trim() || undefined,
      page: questionPage.value,
      page_size: 50,
    })
    questions.value = reset
      ? result.list
      : [
          ...questions.value,
          ...result.list.filter((item) => !questions.value.some((question) => question.id === item.id)),
        ]
    questionTotal.value = result.total
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    loadingQuestions.value = false
    loadingMore.value = false
  }
}

function searchQuestions(): void {
  questionPage.value = 1
  void loadQuestions(true)
}

function loadMore(): void {
  if (loadingQuestions.value || loadingMore.value) return
  if (questions.value.length >= questionTotal.value) return
  questionPage.value += 1
  void loadQuestions(false)
}

function toggleQuestion(id: number): void {
  form.question_ids = form.question_ids.includes(id)
    ? form.question_ids.filter((item) => item !== id)
    : [...form.question_ids, id]
}

function toggleBank(id: number): void {
  form.bank_ids = form.bank_ids.includes(id)
    ? form.bank_ids.filter((item) => item !== id)
    : [...form.bank_ids, id]
}

function dueAtValue(): string | null {
  return form.due_at ? form.due_at : null
}

async function submit(): Promise<void> {
  errorText.value = ''
  if (!form.title.trim()) {
    errorText.value = '请填写试卷标题'
    return
  }
  const payload: PaperCreatePayload = {
    title: form.title.trim(),
    mode: form.mode,
    kind: form.kind,
    duration_minutes: form.duration_minutes,
    shuffle: form.shuffle,
    blank_mode: form.blank_mode,
    due_at: dueAtValue(),
  }
  if (form.mode === 'fixed') {
    if (form.question_ids.length === 0) {
      errorText.value = '固定组卷至少要选择一道题'
      return
    }
    payload.question_ids = form.question_ids
  } else {
    if (form.bank_ids.length === 0) {
      errorText.value = '随机抽题至少要选择一个题库'
      return
    }
    if (form.count <= 0) {
      errorText.value = '抽题数量必须大于 0'
      return
    }
    payload.bank_ids = form.bank_ids
    payload.count = form.count
    payload.knowledge_tag = form.knowledge_tag.trim() || null
    payload.difficulty = form.difficulty || null
  }

  submitting.value = true
  try {
    const paper = await papersApi.create(classId.value, payload)
    toast.success('试卷已创建')
    await router.push(`/teacher/papers/${paper.id}`)
  } catch (error) {
    errorText.value = toUserMessage(error)
  } finally {
    submitting.value = false
  }
}

watch(
  () => form.mode,
  (mode) => {
    if (mode === 'fixed') {
      form.question_ids = []
      void loadQuestions(true)
    }
  },
)

watch(
  () => form.bank_id,
  () => {
    form.question_ids = []
    questionKeyword.value = ''
    questionPage.value = 1
    void loadQuestions(true)
  },
)

onMounted(async () => {
  await loadBanks()
})
</script>

<template>
  <header class="page-head">
    <div class="page-head__main">
      <p class="page-head__crumb">
        <RouterLink :to="`/teacher/classes/${classId}`">班级</RouterLink> ·
        <RouterLink :to="`/teacher/classes/${classId}/papers`">试卷</RouterLink> · 组卷
      </p>
      <h1>新建试卷</h1>
      <p class="page-head__lede">固定题目或按条件随机抽题；保存后仍可发布或继续编辑。</p>
    </div>
  </header>

  <p v-if="errorText" class="notice notice--danger">{{ errorText }}</p>

  <div class="columns">
    <section class="card stack">
      <header class="card__head"><h2>试卷设置</h2></header>

      <BaseField label="试卷标题" required>
        <input v-model="form.title" class="input" type="text" placeholder="例如 函数与导数 · 课后练习" />
      </BaseField>

      <div class="form-row">
        <BaseField label="试卷用途">
          <BaseSelect v-model="form.kind" :options="kindOptions" aria-label="试卷用途" />
        </BaseField>
        <BaseField label="组卷方式">
          <BaseSelect v-model="form.mode" :options="modeOptions" aria-label="组卷方式" />
        </BaseField>
      </div>

      <div class="form-row">
        <BaseField label="作答时长（分钟）" hint="0 表示不限时">
          <input v-model.number="form.duration_minutes" class="input" type="number" min="0" max="300" />
        </BaseField>
        <BaseField label="截止时间（选填）" hint="仅作为试卷截止时间，与单次倒计时不同">
          <input v-model="form.due_at" class="input" type="datetime-local" />
        </BaseField>
      </div>

      <div class="form-row">
        <BaseField label="填空题判定">
          <BaseSelect v-model="form.blank_mode" :options="blankModeOptions" aria-label="填空题判定" />
        </BaseField>
        <BaseField label="题目乱序">
          <BaseSelect v-model="form.shuffle" :options="shuffleOptions" aria-label="题目乱序" />
        </BaseField>
      </div>

      <template v-if="form.mode === 'random'">
        <div class="field">
          <span class="field__label">抽题题库</span>
          <p v-if="loadingBanks" class="small tertiary">正在读取题库…</p>
          <p v-else-if="banks.length === 0" class="notice">还没有题库，请先去题库页创建。</p>
          <div v-else class="stack" style="gap: 6px">
            <label v-for="bank in banks" :key="bank.id" class="check">
              <input
                type="checkbox"
                :checked="form.bank_ids.includes(bank.id)"
                @change="toggleBank(bank.id)"
              />
              <span>{{ bank.name }}（{{ bank.question_count }} 题）</span>
            </label>
          </div>
        </div>
        <div class="form-row">
          <BaseField label="抽题数量">
            <input v-model.number="form.count" class="input" type="number" min="1" max="500" />
          </BaseField>
          <BaseField label="难度（选填）">
            <BaseSelect v-model="form.difficulty" :options="difficultyOptions" aria-label="难度" />
          </BaseField>
        </div>
        <BaseField label="知识点（选填）" hint="留空则不限知识点">
          <input v-model="form.knowledge_tag" class="input" type="text" placeholder="例如 导数" />
        </BaseField>
      </template>

      <div class="row">
        <BaseButton variant="primary" :loading="submitting" @click="submit">创建试卷</BaseButton>
        <RouterLink class="btn" :to="`/teacher/classes/${classId}/papers`">取消</RouterLink>
      </div>
    </section>

    <section v-if="form.mode === 'fixed'" class="card stack">
      <header class="card__head">
        <h2>选择题目</h2>
        <span class="card__meta">已选 {{ selectedCount }} 题</span>
      </header>
      <BaseField label="题库">
        <BaseSelect v-model="form.bank_id" :options="bankOptions" placeholder="选择题库" aria-label="题库" />
      </BaseField>
      <BaseField label="搜索题目">
        <div class="row" style="gap: 8px">
          <input
            v-model="questionKeyword"
            class="input"
            type="search"
            placeholder="搜索题干或知识点"
            @keyup.enter="searchQuestions"
          />
          <BaseButton type="button" @click="searchQuestions">搜索</BaseButton>
        </div>
      </BaseField>

      <p v-if="loadingQuestions && !loadingMore" class="loading-line">正在读取题目…</p>
      <p v-else-if="!selectedBank" class="notice">请选择题库。</p>
      <p v-else-if="questions.length === 0" class="notice">该题库还没有题目。</p>
      <div v-else class="stack" style="gap: 8px; max-height: 560px; overflow-y: auto">
        <label
          v-for="item in questions"
          :key="item.id"
          class="notice"
          style="display: flex; gap: 8px; align-items: flex-start; cursor: pointer"
        >
          <input
            type="checkbox"
            style="margin-top: 3px"
            :checked="form.question_ids.includes(item.id)"
            @change="toggleQuestion(item.id)"
          />
          <span style="min-width: 0">
            <span class="strong" style="display: block; font-size: 12.5px; line-height: 1.55">
              {{ item.stem }}
            </span>
            <span class="small tertiary">
              {{ QUESTION_TYPE_LABEL[item.type] }} · {{ item.knowledge_tag }} · 答案
              {{ formatAnswer(item.answer, item.type) }}
            </span>
          </span>
        </label>
      </div>
      <div v-if="selectedBank && questions.length > 0" class="row row--wrap" style="justify-content: space-between">
        <span class="small tertiary">已加载 {{ questions.length }} / 共 {{ questionTotal }} 题</span>
        <BaseButton v-if="questions.length < questionTotal" :loading="loadingMore" @click="loadMore">
          加载更多
        </BaseButton>
      </div>
    </section>

    <section v-else class="card stack">
      <header class="card__head"><h2>抽题预览</h2></header>
      <p class="notice">
        随机组卷会在发布前按条件抽取 {{ form.count }} 道题；若符合条件的题目不足，后端会返回
        「题库为空」类提示。
      </p>
      <div class="kv">
        <span>已选题库：<b>{{ form.bank_ids.length }} 个</b></span>
        <span>用途：<b>{{ form.kind === 'practice' ? '练习' : form.kind === 'homework' ? '作业' : '考试' }}</b></span>
        <span>时长：<b>{{ form.duration_minutes }} 分钟</b></span>
      </div>
    </section>
  </div>
</template>
