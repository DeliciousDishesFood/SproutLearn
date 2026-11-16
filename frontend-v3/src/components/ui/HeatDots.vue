<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { ActivityDay } from '@/api/contract'

const props = withDefaults(
  defineProps<{
    days: ActivityDay[]
    weeks?: number
    role: 'teacher' | 'student'
  }>(),
  { weeks: 12 },
)

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const slots = computed(() => Math.max(1, props.weeks) * 7)

/** 取最近 N 周，按日期升序补齐；缺失日期按 0 展示；日期用本地午夜构造。 */
const cells = computed<ActivityDay[]>(() => {
  const map = new Map<string, ActivityDay>()
  props.days.forEach((day) => map.set(day.date, day))
  const total = slots.value
  const now = new Date()
  const result: ActivityDay[] = []
  for (let index = total - 1; index >= 0; index -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - index)
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    result.push(map.get(key) ?? { date: key, answers: 0 })
  }
  return result
})

/** 教师按 answers 着色；学生按 xp>0 ? xp : answers 着色；active_students 只进读数。 */
function metric(day: ActivityDay): number {
  if (props.role === 'student') {
    const xp = day.xp ?? 0
    return xp > 0 ? xp : day.answers
  }
  return day.answers
}

const max = computed(() => Math.max(0, ...cells.value.map(metric)))

function level(value: number): 'l0' | 'l1' | 'l2' | 'l3' | 'l4' {
  if (value <= 0 || max.value <= 0) return 'l0'
  const ratio = value / max.value
  if (ratio <= 0.25) return 'l1'
  if (ratio <= 0.5) return 'l2'
  if (ratio <= 0.75) return 'l3'
  return 'l4'
}

function sum(list: ActivityDay[], pick: (day: ActivityDay) => number): number {
  return list.reduce((acc, day) => acc + pick(day), 0)
}

const maxAnswers = computed(() => Math.max(0, ...cells.value.map((day) => day.answers)))
const maxXp = computed(() => Math.max(0, ...cells.value.map((day) => day.xp ?? 0)))

/** 图上方 4 项统计，教师/学生口径不同；0 显示 0，不显示“—”。 */
const stats = computed<Array<{ label: string; value: number }>>(() => {
  if (props.role === 'teacher') {
    return [
      { label: `${props.weeks}周作答`, value: sum(cells.value, (day) => day.answers) },
      { label: '活跃天数', value: cells.value.filter((day) => day.answers > 0).length },
      { label: '单日最高', value: maxAnswers.value },
      { label: '今日活跃', value: cells.value.at(-1)?.active_students ?? 0 },
    ]
  }
  return [
    { label: `${props.weeks}周经验`, value: sum(cells.value, (day) => day.xp ?? 0) },
    { label: '活跃天数', value: cells.value.filter((day) => (day.xp ?? 0) > 0 || day.answers > 0).length },
    { label: '单日最高', value: maxXp.value },
    { label: '今日 XP', value: cells.value.at(-1)?.xp ?? 0 },
  ]
})

function parseDate(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** 按每列首日生成月份标签；不硬编码月份。 */
const monthLabels = computed(() => {
  const labels: Array<{ column: number; label: string }> = []
  let previous = ''
  cells.value.forEach((day, index) => {
    if (index % 7 !== 0) return
    const month = parseDate(day.date).getMonth() + 1
    const label = `${month}月`
    if (label !== previous) {
      labels.push({ column: index / 7, label })
      previous = label
    }
  })
  return labels
})

const activeIndex = ref(-1)
const readout = ref('悬停、聚焦或按方向键查看每日记录')
const cellRefs = ref<Array<HTMLButtonElement | null>>([])

function formatDay(dateKey: string): string {
  const date = parseDate(dateKey)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${WEEKDAYS[date.getDay()]}`
}

function daySummary(day: ActivityDay): string {
  if (props.role === 'teacher') {
    if (day.answers <= 0) return '无学习记录'
    return `作答 ${day.answers} 次 · 活跃学生 ${day.active_students ?? 0} 人`
  }
  const xp = day.xp ?? 0
  if (xp <= 0 && day.answers <= 0) return '无学习记录'
  return `+${xp} XP · 作答 ${day.answers} 次`
}

function readText(day: ActivityDay): string {
  return `${formatDay(day.date)} · ${daySummary(day)}`
}

function setCellRef(el: unknown, index: number): void {
  cellRefs.value[index] = el as HTMLButtonElement | null
}

function select(index: number, focus = false): void {
  if (index < 0 || index >= cells.value.length) return
  activeIndex.value = index
  readout.value = readText(cells.value[index])
  if (focus) {
    void nextTick(() => cellRefs.value[index]?.focus())
  }
}

/** 键盘：左右 ±7（按周），上下 ±1（按天）；roving tabindex，仅当前格可 Tab。 */
function onKeydown(event: KeyboardEvent): void {
  const total = cells.value.length
  if (total === 0) return
  const current = activeIndex.value >= 0 ? activeIndex.value : total - 1
  let next = current
  if (event.key === 'ArrowLeft') next = current - 7
  else if (event.key === 'ArrowRight') next = current + 7
  else if (event.key === 'ArrowUp') next = current - 1
  else if (event.key === 'ArrowDown') next = current + 1
  else return
  event.preventDefault()
  next = Math.max(0, Math.min(total - 1, next))
  select(next, true)
}
</script>

<template>
  <div class="heat">
    <div class="heat-stats" role="list">
      <div v-for="stat in stats" :key="stat.label" class="heat-stat" role="listitem">
        <span class="heat-stat__value">{{ stat.value }}</span>
        <span class="heat-stat__label">{{ stat.label }}</span>
      </div>
    </div>

    <p class="heat-readout" aria-live="polite">{{ readout }}</p>

    <div
      class="heat-grid"
      role="grid"
      :aria-label="`最近 ${weeks} 周学习热力`"
      tabindex="0"
      @keydown="onKeydown"
    >
      <button
        v-for="(day, index) in cells"
        :key="day.date"
        type="button"
        class="heat-cell"
        :class="[level(metric(day)), { 'is-active': activeIndex === index }]"
        :aria-label="readText(day)"
        :tabindex="activeIndex === index ? 0 : -1"
        :ref="(el) => setCellRef(el, index)"
        @mouseenter="select(index)"
        @focus="select(index)"
        @click="select(index)"
      />
    </div>

    <div class="heat-months" aria-hidden="true">
      <span
        v-for="item in monthLabels"
        :key="`${item.column}-${item.label}`"
        :style="{ gridColumn: `${item.column + 1} / span 2` }"
      >
        {{ item.label }}
      </span>
    </div>

    <div class="heat-foot">
      <div class="heat-legend" aria-hidden="true">
        <span>少</span>
        <i class="l0" /><i class="l1" /><i class="l2" /><i class="l3" /><i class="l4" />
        <span>多</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.heat {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.heat-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  padding: 2px 0 10px;
  border-bottom: 1px solid var(--line-soft);
}

.heat-stat__value {
  display: block;
  font-size: 20px;
  line-height: 1.15;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.heat-stat__label {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--muted);
  white-space: nowrap;
}

.heat-readout {
  min-height: 16px;
  margin: 0;
  font-size: 11px;
  color: var(--muted);
}

.heat-grid {
  display: grid;
  grid-template-columns: repeat(12, 13px);
  grid-template-rows: repeat(7, 13px);
  grid-auto-flow: column;
  gap: 7px;
  justify-content: center;
  align-content: start;
  padding: 2px 0;
}

.heat-cell {
  width: 13px;
  height: 13px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--heat-0);
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.heat-cell:hover,
.heat-cell:focus-visible {
  transform: scale(1.18);
  outline: none;
  box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--lime);
}

.heat-cell.is-active {
  box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--lime-deep);
}

.heat-cell.l1 {
  background: var(--heat-1);
}

.heat-cell.l2 {
  background: var(--heat-2);
}

.heat-cell.l3 {
  background: var(--heat-3);
}

.heat-cell.l4 {
  background: var(--heat-4);
}

.heat-months {
  display: grid;
  grid-template-columns: repeat(12, 13px);
  gap: 7px;
  justify-content: center;
  margin-top: -2px;
  font-size: 9.5px;
  line-height: 1;
  color: var(--tertiary);
}

.heat-months span {
  white-space: nowrap;
}

.heat-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 2px;
}

.heat-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--tertiary);
}

.heat-legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.heat-legend i.l0 {
  background: var(--heat-0);
}

.heat-legend i.l1 {
  background: var(--heat-1);
}

.heat-legend i.l2 {
  background: var(--heat-2);
}

.heat-legend i.l3 {
  background: var(--heat-3);
}

.heat-legend i.l4 {
  background: var(--heat-4);
}

@media (max-width: 640px) {
  .heat-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .heat-stat__value {
    font-size: 18px;
  }
}
</style>
