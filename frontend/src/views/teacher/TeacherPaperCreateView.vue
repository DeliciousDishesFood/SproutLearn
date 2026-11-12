<!-- 组卷页：固定选题或随机条件组卷，提交前实时校验题量与总分。 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ClipboardList,
  Clock3,
  RefreshCw,
  Send,
  Sparkles,
} from 'lucide-vue-next'
import AppButton from '@/components/base/AppButton.vue'
import AppEmpty from '@/components/base/AppEmpty.vue'
import AppInput from '@/components/base/AppInput.vue'
import AppSelect from '@/components/base/AppSelect.vue'
import AppTag from '@/components/base/AppTag.vue'
import QuestionPicker from '@/components/business/QuestionPicker.vue'
import { papersApi } from '@/api/papers'
import { banksApi } from '@/api/questions'
import { isApiError, toUserMessage } from '@/api/client'
import { useClassStore } from '@/stores/class'
import { useUiStore } from '@/stores/ui'
import {
  BLANK_MODE_META,
  DIFFICULTY_META,
  PAPER_MODE_LABEL,
} from '@/utils/constants'
import type {
  BlankMode,
  PaperCreatePayload,
  PaperMode,
  QuestionBank,
  QuestionDifficulty,
  QuestionItem,
} from '@/api/types'
import type { SelectOption } from '@/types'

const route = useRoute()
const router = useRouter()
const classStore = useClassStore()
const ui = useUiStore()

const selectedClassId = ref('')
const classErroring = ref(false)
const loadingClasses = ref(false)

const title = ref('')
const mode = ref<PaperMode>('fixed')
const durationMinutes = ref(30)
const shuffle = ref(false)
const blankMode = ref<BlankMode>('smart')

const randomTag = ref('')
const randomDifficulty = ref('')
const randomCount = ref(10)
const randomBankIds = ref<number[]>([])

const banks = ref<QuestionBank[]>([])
const banksLoading = ref(false)
const banksError = ref('')

const selectedIds = ref<number[]>([])
const selectedItems = ref<QuestionItem[]>([])
const submitting = ref(false)
const submitError = ref('')

const difficultyOptions: SelectOption[] = [
  { label: '不限难度', value: '' },
  ...(Object.keys(DIFFICULTY_META) as QuestionDifficulty[]).map((value) => ({
    label: DIFFICULTY_META[value].label,
    value,
  })),
]

const classOptions = computed(() =>
  classStore.classes.map((item) => ({
    label: `${item.class_name} · ${item.course_name}`,
    value: String(item.id),
  })),
)

const currentClass = computed(
  () => classStore.classes.find((item) => String(item.id) === selectedClassId.value) ?? null,
)
const classId = computed(() => (selectedClassId.value ? Number(selectedClassId.value) : null))

const randomRangeCount = computed(() => {
  const scoped = randomBankIds.value.length
    ? banks.value.filter((bank) => randomBankIds.value.includes(bank.id))
    : banks.value
  return scoped.reduce((sum, bank) => sum + bank.question_count, 0)
})

const selectedBankNames = computed(() =>
  banks.value
    .filter((bank) => randomBankIds.value.includes(bank.id))
    .map((bank) => bank.name),
)
const fixedBankNames = computed(() => {
  const names: string[] = []
  for (const item of selectedItems.value) {
    if (item.bank_name && !names.includes(item.bank_name)) names.push(item.bank_name)
  }
  return names
})
const sourceBankNames = computed(() => {
  if (mode.value === 'fixed') return fixedBankNames.value
  return randomBankIds.value.length > 0 ? selectedBankNames.value : []
})
const sourceBankLabel = computed(() => {
  const names = sourceBankNames.value
  if (names.length === 0) return mode.value === 'fixed' ? '待选题库' : '全部题库'
  return names.length > 1 ? `${names[0]} +${names.length - 1}` : names[0]
})
const sourceBankTitle = computed(() =>
  sourceBankNames.value.length > 0 ? sourceBankNames.value.join('、') : sourceBankLabel.value,
)

function toggleRandomBank(bankId: number): void {
  const index = randomBankIds.value.indexOf(bankId)
  if (index >= 0) randomBankIds.value = randomBankIds.value.filter((id) => id !== bankId)
  else randomBankIds.value = [...randomBankIds.value, bankId]
}

const questionCount = computed(() => {
  if (mode.value === 'fixed') return selectedIds.value.length
  const count = Number(randomCount.value)
  return Number.isFinite(count) && count > 0 ? Math.floor(count) : 0
})
const totalScore = computed(() => questionCount.value)
const durationLabel = computed(() =>
  Number(durationMinutes.value) > 0 ? `${Number(durationMinutes.value)} 分钟` : '不限时',
)
const blankMeta = computed(() => BLANK_MODE_META[blankMode.value])
const blankModeOptions = (Object.keys(BLANK_MODE_META) as BlankMode[]).map((key) => ({
  key,
  ...BLANK_MODE_META[key],
}))

const validationHint = computed(() => {
  if (!selectedClassId.value) return '请选择班级'
  if (title.value.trim() === '') return '请填写试卷标题'
  if (title.value.trim().length > 200) return '试卷标题不能超过 200 字'
  if (mode.value === 'fixed' && selectedIds.value.length === 0) {
    return '固定组卷至少选择 1 道题'
  }
  if (mode.value === 'random') {
    const count = Number(randomCount.value)
    if (!Number.isInteger(count) || count < 1 || count > 500) {
      return '随机题量需为 1-500 的整数'
    }
  }
  const duration = Number(durationMinutes.value)
  if (!Number.isFinite(duration) || duration < 0) {
    return '作答时长需为不小于 0 的整数'
  }
  return ''
})
const canSubmit = computed(() => validationHint.value === '' && !submitting.value)

async function loadBanks(): Promise<void> {
  if (!classId.value) {
    banks.value = []
    return
  }
  banksLoading.value = true
  banksError.value = ''
  try {
    banks.value = await banksApi.list(classId.value)
  } catch (err) {
    banks.value = []
    banksError.value = isApiError(err) && err.code === 40302 ? '无权访问该班级资源' : toUserMessage(err)
  } finally {
    banksLoading.value = false
  }
}

async function bootstrap(): Promise<void> {
  loadingClasses.value = true
  classErroring.value = false
  try {
    await classStore.fetchAllClasses()
  } catch {
    classErroring.value = true
    return
  } finally {
    loadingClasses.value = false
  }
  if (classStore.classes.length === 0) return
  const queryId = Number(route.query.class_id)
  const matched = classStore.classes.find((item) => item.id === queryId)
  selectedClassId.value = String(matched ? matched.id : classStore.classes[0].id)
  if (!matched) syncClassQuery()
  await loadBanks()
}

function syncClassQuery(): void {
  void router.replace({
    query: {
      ...route.query,
      class_id: selectedClassId.value,
    },
  })
}

function handleClassChange(value: string): void {
  if (value === selectedClassId.value) return
  selectedClassId.value = value
  selectedIds.value = []
  selectedItems.value = []
  randomTag.value = ''
  randomBankIds.value = []
  banks.value = []
  banksError.value = ''
  submitError.value = ''
  syncClassQuery()
  void loadBanks()
}

function backToPapers(): void {
  void router.push({ path: '/teacher/papers', query: { class_id: selectedClassId.value } })
}

function switchMode(next: PaperMode): void {
  if (mode.value === next) return
  mode.value = next
  submitError.value = ''
}

function mapSubmitError(err: unknown): string {
  if (isApiError(err) && err.code === 40302) return '无权访问该班级资源'
  if (isApiError(err) && err.code === 40908) {
    return '题库没有可用题目，或数量不足；请先导入题目或调整随机条件。'
  }
  return toUserMessage(err)
}

async function submit(): Promise<void> {
  if (!selectedClassId.value || submitting.value) return
  if (validationHint.value) {
    submitError.value = validationHint.value
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    const payload: PaperCreatePayload = {
      title: title.value.trim(),
      mode: mode.value,
      duration_minutes: Math.max(0, Math.floor(Number(durationMinutes.value) || 0)),
      shuffle: shuffle.value,
      blank_mode: blankMode.value,
    }
    if (mode.value === 'fixed') {
      payload.question_ids = [...selectedIds.value]
    } else {
      payload.knowledge_tag = randomTag.value.trim() || null
      payload.difficulty = randomDifficulty.value
        ? (randomDifficulty.value as QuestionDifficulty)
        : null
      payload.count = Math.floor(Number(randomCount.value))
      if (randomBankIds.value.length > 0) payload.bank_ids = [...randomBankIds.value]
    }
    const paper = await papersApi.create(Number(selectedClassId.value), payload)
    ui.success('试卷已创建，可在详情页发布')
    await router.replace({
      name: 'teacher-paper-detail',
      params: { id: String(paper.id) },
      query: { class_id: selectedClassId.value },
    })
  } catch (err) {
    submitError.value = mapSubmitError(err)
  } finally {
    submitting.value = false
  }
}

onMounted(bootstrap)
</script>

<template>
  <div class="page paper-create">
    <header class="page-head">
      <div class="page-head__text">
        <p class="eyebrow">NEW PAPER</p>
        <h1 class="page-title">新建试卷</h1>
        <p class="page-subtitle">
          固定选题可按题库勾选；随机组卷按知识点与难度抽题。创建后先保存为草稿，发布前可再调整。
        </p>
      </div>
      <AppButton variant="ghost" @click="backToPapers">
        <ArrowLeft :size="15" :stroke-width="1.9" />
        返回试卷
      </AppButton>
    </header>

    <section v-if="classErroring" class="panel">
      <AppEmpty error title="班级列表暂时无法加载" description="请检查后端服务后重试">
        <template #action>
          <AppButton variant="secondary" :loading="loadingClasses" @click="bootstrap">
            <RefreshCw :size="15" :stroke-width="1.8" />
            重新加载
          </AppButton>
        </template>
      </AppEmpty>
    </section>

    <section v-else-if="!loadingClasses && classStore.classes.length === 0" class="panel">
      <AppEmpty title="还没有可组卷的班级" description="试卷按班级隔离，创建班级后再回来组卷。">
        <template #action>
          <router-link to="/teacher/classes">
            <AppButton variant="primary">去我的班级</AppButton>
          </router-link>
        </template>
      </AppEmpty>
    </section>
    <div v-else class="create-layout">
      <main class="content-stack">
        <section class="panel panel-body settings">
          <div class="form-grid">
            <AppSelect
              :model-value="selectedClassId"
              label="所属班级"
              :options="classOptions"
              class="form-grid__full"
              @update:model-value="handleClassChange"
            />
            <AppInput
              v-model="title"
              label="试卷标题"
              placeholder="如：传输层第一次随堂测"
              :maxlength="200"
              class="form-grid__full"
            />
            <label class="field">
              <span class="field__label">作答时长</span>
              <div class="number-field">
                <input
                  v-model.number="durationMinutes"
                  class="number-field__input tabular"
                  type="number"
                  min="0"
                  max="600"
                  step="5"
                  :disabled="submitting"
                />
                <span class="number-field__unit">分钟</span>
              </div>
              <span class="form-hint">填 0 表示不限时；至 0 时以服务端截止时间自动提交。</span>
            </label>
            <div class="field">
              <span class="field__label">创建后状态</span>
              <div class="readonly-value">
                <AppTag tone="neutral" dot>草稿</AppTag>
                <span class="muted text-xs">发布后学生才可见</span>
              </div>
            </div>
          </div>

          <div class="switch-row">
            <label class="switch">
              <input v-model="shuffle" type="checkbox" class="visually-hidden" />
              <span class="switch__track" aria-hidden="true">
                <span class="switch__thumb" />
              </span>
              <span class="switch__text">
                <strong>题目乱序</strong>
                <small>每位学生的题号顺序不同，选项顺序不变。</small>
              </span>
            </label>
          </div>
        </section>

        <section class="panel panel-body mode-panel">
          <div class="mode-head">
            <h2 class="section-title">组卷方式</h2>
            <span class="muted text-xs">每题 1 分 · 总分 = 题量</span>
          </div>

          <div class="mode-grid" role="radiogroup" aria-label="组卷方式">
            <button
              class="mode-card"
              :class="{ 'mode-card--active': mode === 'fixed' }"
              type="button"
              role="radio"
              :aria-checked="mode === 'fixed'"
              @click="switchMode('fixed')"
            >
              <span class="mode-card__icon"><ClipboardList :size="20" :stroke-width="1.7" /></span>
              <span>
                <strong>固定选题</strong>
                <small>从题库逐题勾选，试卷内容完全确定。</small>
              </span>
              <span class="mode-card__check"><Check v-if="mode === 'fixed'" :size="14" :stroke-width="2.4" /></span>
            </button>
            <button
              class="mode-card"
              :class="{ 'mode-card--active': mode === 'random' }"
              type="button"
              role="radio"
              :aria-checked="mode === 'random'"
              @click="switchMode('random')"
            >
              <span class="mode-card__icon"><Sparkles :size="20" :stroke-width="1.7" /></span>
              <span>
                <strong>随机组卷</strong>
                <small>按知识点与难度抽题，创建时确定题目。</small>
              </span>
              <span class="mode-card__check"><Check v-if="mode === 'random'" :size="14" :stroke-width="2.4" /></span>
            </button>
          </div>

          <QuestionPicker
            v-if="mode === 'fixed'"
            v-model="selectedIds"
            :class-id="classId"
            :banks="banks"
            @update:items="selectedItems = $event"
          />

          <div v-else class="random-form">
            <section class="bank-scope" aria-label="随机组卷抽题范围">
              <div class="bank-scope__head">
                <span class="bank-scope__title">抽题范围</span>
                <span class="muted text-xs">可多选题库；不选则从全班题库抽取</span>
              </div>
              <p v-if="banksLoading" class="muted text-xs">正在加载题库…</p>
              <p v-else-if="banksError" class="form-error" role="alert">
                <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
                <span>{{ banksError }}</span>
              </p>
              <p v-else-if="banks.length === 0" class="muted text-xs">
                本班还没有题库，请先在题库页导入题目。
              </p>
              <div v-else class="bank-scope__chips">
                <button
                  v-for="bank in banks"
                  :key="bank.id"
                  class="bank-chip"
                  :class="{ 'bank-chip--active': randomBankIds.includes(bank.id) }"
                  type="button"
                  :aria-pressed="randomBankIds.includes(bank.id)"
                  @click="toggleRandomBank(bank.id)"
                >
                  <Check
                    v-if="randomBankIds.includes(bank.id)"
                    :size="12"
                    :stroke-width="2.6"
                    aria-hidden="true"
                  />
                  <span class="truncate" :title="bank.name">{{ bank.name }}</span>
                  <span class="bank-chip__count tabular">{{ bank.question_count }}</span>
                </button>
              </div>
              <p class="bank-scope__summary">
                抽题范围：<strong class="tabular">{{ randomRangeCount }}</strong> 题
                <button
                  v-if="randomBankIds.length > 0"
                  class="bank-scope__clear"
                  type="button"
                  @click="randomBankIds = []"
                >
                  清空范围
                </button>
              </p>
            </section>

            <div class="form-grid">
              <AppInput
                v-model="randomTag"
                label="知识点标签（可选）"
                placeholder="如：传输层；留空则全库随机"
              />
              <AppSelect
                v-model="randomDifficulty"
                label="难度（可选）"
                :options="difficultyOptions"
              />
              <label class="field">
                <span class="field__label">抽取题量</span>
                <div class="number-field">
                  <input
                    v-model.number="randomCount"
                    class="number-field__input tabular"
                    type="number"
                    min="1"
                    max="500"
                    step="1"
                  />
                  <span class="number-field__unit">道</span>
                </div>
                <span class="form-hint">1-500 道；本班题库不足时会提示 40908。</span>
              </label>
            </div>

            <div class="quick-counts">
              <span class="muted text-xs">快捷题量</span>
              <button
                v-for="count in [5, 10, 20]"
                :key="count"
                class="quick-count"
                :class="{ 'quick-count--active': Number(randomCount) === count }"
                type="button"
                @click="randomCount = count"
              >
                {{ count }} 题
              </button>
            </div>

            <p class="random-note">
              <AlertCircle :size="14" :stroke-width="1.9" aria-hidden="true" />
              <span v-if="randomBankIds.length > 0">
                只会在已选题库范围内抽题；范围内没有匹配题目时提示数量不足，不会越界到其他题库。
              </span>
              <span v-else>
                标签或难度没有匹配题目时，后端会自动回退到本班全库随机；仍无题则提示题库为空。
              </span>
            </p>
          </div>
        </section>

        <section class="panel panel-body judging">
          <div class="judging__head">
            <h2 class="section-title">判分严格度</h2>
            <span class="muted text-xs">发布前可修改；仅影响填空题</span>
          </div>
          <div class="blank-grid" role="radiogroup" aria-label="判分严格度">
            <button
              v-for="option in blankModeOptions"
              :key="option.key"
              class="blank-card"
              :class="{ 'blank-card--active': blankMode === option.key }"
              type="button"
              role="radio"
              :aria-checked="blankMode === option.key"
              @click="blankMode = option.key"
            >
              <span class="blank-card__head">
                <strong>{{ option.label }}</strong>
                <span v-if="option.key === 'smart'" class="blank-card__badge">默认</span>
              </span>
              <small>{{ option.description }}</small>
              <span class="blank-card__radio" aria-hidden="true">
                <span v-if="blankMode === option.key" class="blank-card__dot" />
              </span>
            </button>
          </div>
        </section>

        <p v-if="submitError" class="form-error" role="alert">
          <AlertCircle :size="16" :stroke-width="1.9" aria-hidden="true" />
          <span>{{ submitError }}</span>
        </p>
      </main>

      <aside class="summary" aria-label="试卷摘要">
        <div class="panel panel-body summary__inner">
          <p class="eyebrow">SUMMARY</p>
          <h2 class="summary__title">{{ title.trim() || '未命名试卷' }}</h2>
          <p class="summary__class">{{ currentClass?.class_name || '未选择班级' }}</p>

          <dl class="summary__stats">
            <div>
              <dt>组卷方式</dt>
              <dd>{{ PAPER_MODE_LABEL[mode] }}</dd>
            </div>
            <div>
              <dt>来源题库</dt>
              <dd class="summary__banks" :title="sourceBankTitle">{{ sourceBankLabel }}</dd>
            </div>
            <div>
              <dt>题量</dt>
              <dd class="tabular">{{ questionCount }} 题</dd>
            </div>
            <div>
              <dt>总分</dt>
              <dd class="tabular summary__score">{{ totalScore }} 分</dd>
            </div>
            <div>
              <dt>时长</dt>
              <dd>
                <Clock3 :size="13" :stroke-width="1.8" aria-hidden="true" />
                {{ durationLabel }}
              </dd>
            </div>
            <div>
              <dt>判分</dt>
              <dd>{{ blankMeta.label }}</dd>
            </div>
            <div>
              <dt>题目顺序</dt>
              <dd>{{ shuffle ? '乱序' : '固定' }}</dd>
            </div>
          </dl>

          <p v-if="validationHint && !submitError" class="summary__hint">
            {{ validationHint }}
          </p>

          <AppButton
            variant="primary"
            block
            :loading="submitting"
            :disabled="!canSubmit"
            @click="submit"
          >
            <Send :size="15" :stroke-width="1.9" />
            创建试卷
          </AppButton>
          <p class="summary__note">创建后仍为草稿，详情页确认后再发布给学生。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.create-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--sp-5);
  align-items: start;
}

.settings,
.mode-panel,
.judging {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4);
}

.form-grid__full {
  grid-column: 1 / -1;
}

.form-hint {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.field__label {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--color-text);
}

.number-field {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.number-field__input {
  width: 100px;
  min-height: 40px;
  padding: 9px var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
}

.number-field__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.number-field__unit {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.readonly-value {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-height: 40px;
  padding: 0 var(--sp-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.switch-row {
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.switch {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  cursor: pointer;
}

.switch__track {
  position: relative;
  width: 42px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--color-border-strong);
  transition: background-color 160ms ease-out;
}

.switch__thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: var(--color-surface);
  box-shadow: var(--shadow-1);
  transition: transform 160ms ease-out;
}

.switch input:checked + .switch__track {
  background: var(--color-primary);
}

.switch input:checked + .switch__track .switch__thumb {
  transform: translateX(18px);
}

.switch__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch__text strong {
  font-size: var(--fs-sm);
}

.switch__text small {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.mode-head,
.judging__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.mode-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.mode-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  padding: var(--sp-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  text-align: left;
  transition: border-color 160ms ease-out, background-color 160ms ease-out;
}

.mode-card:hover {
  border-color: var(--color-primary);
}

.mode-card--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.mode-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
  color: var(--color-primary);
}

.mode-card--active .mode-card__icon {
  background: var(--color-surface);
}

.mode-card strong {
  display: block;
  font-size: var(--fs-base);
}

.mode-card small {
  display: block;
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.mode-card__check {
  display: inline-flex;
  position: absolute;
  top: var(--sp-3);
  right: var(--sp-3);
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  color: var(--color-text-inverse);
  background: var(--color-primary);
}

.random-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--color-border);
}

.bank-scope {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-alt);
}

.bank-scope__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.bank-scope__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}

.bank-scope__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.bank-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 240px;
  padding: 5px var(--sp-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.bank-chip:hover {
  border-color: var(--color-primary);
}

.bank-chip--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.bank-chip__count {
  color: var(--color-text-muted);
  font-weight: 500;
}

.bank-chip--active .bank-chip__count {
  color: var(--color-primary);
}

.bank-scope__summary {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.bank-scope__summary strong {
  color: var(--color-primary);
}

.bank-scope__clear {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--fs-xs);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.quick-counts {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.quick-count {
  min-height: 30px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.quick-count:hover,
.quick-count--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.random-note {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.random-note svg {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--color-warning);
}

.blank-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.blank-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  text-align: left;
}

.blank-card:hover {
  border-color: var(--color-primary);
}

.blank-card--active {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary-soft) 52%, var(--color-surface));
}

.blank-card__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.blank-card__head strong {
  font-size: var(--fs-sm);
}

.blank-card__badge {
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-accent);
  color: var(--color-text-inverse);
  font-size: 10px;
  font-weight: 600;
}

.blank-card small {
  max-width: 88%;
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.blank-card__radio {
  position: absolute;
  top: var(--sp-4);
  right: var(--sp-4);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1px solid var(--color-border-strong);
  border-radius: 999px;
  background: var(--color-surface);
}

.blank-card--active .blank-card__radio {
  border-color: var(--color-primary);
}

.blank-card__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--color-primary);
}

.summary {
  position: sticky;
  top: calc(var(--topbar-h) + var(--sp-4));
}

.summary__inner {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.summary__title {
  font-size: var(--fs-xl);
  line-height: 1.4;
  overflow-wrap: anywhere;
  text-align: center;
}

.summary__class {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
  text-align: center;
}

.summary__stats {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  grid-auto-rows: 36px;
  align-items: center;
  padding: var(--sp-2) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.summary__stats div {
  display: contents;
}

.summary__stats dt {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  text-align: left;
}

.summary__stats dd {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
  font-size: var(--fs-sm);
  font-weight: 600;
  text-align: right;
}

.summary__score {
  color: var(--color-primary);
  font-size: var(--fs-xl) !important;
}

.summary__banks {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary__hint {
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-xs);
  background: var(--color-surface-alt);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
}

.summary__note {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

@media (max-width: 1023px) {
  .create-layout {
    grid-template-columns: 1fr;
  }

  .summary {
    position: static;
  }
}

@media (max-width: 720px) {
  .form-grid,
  .mode-grid,
  .blank-grid {
    grid-template-columns: 1fr;
  }
}
</style>
