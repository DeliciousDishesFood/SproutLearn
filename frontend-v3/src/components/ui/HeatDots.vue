<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { ActivityDay } from '@/api/contract'
import CountUpNumber from '@/components/ui/CountUpNumber.vue'

const props = withDefaults(
  defineProps<{
    days: ActivityDay[]
    weeks?: number
    role: 'teacher' | 'student'
  }>(),
  { weeks: 12 },
)

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const weeks = computed(() => Math.max(1, props.weeks))
const slots = computed(() => weeks.value * 7)

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
      { label: `${weeks.value}周作答`, value: sum(cells.value, (day) => day.answers) },
      { label: '活跃天数', value: cells.value.filter((day) => day.answers > 0).length },
      { label: '单日最高', value: maxAnswers.value },
      { label: '今日活跃', value: cells.value.at(-1)?.active_students ?? 0 },
    ]
  }
  return [
    { label: `${weeks.value}周经验`, value: sum(cells.value, (day) => day.xp ?? 0) },
    { label: '活跃天数', value: cells.value.filter((day) => (day.xp ?? 0) > 0 || day.answers > 0).length },
    { label: '单日最高', value: maxXp.value },
    { label: '今日 XP', value: cells.value.at(-1)?.xp ?? 0 },
  ]
})

function parseDate(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(y, m - 1, d)
}

interface MonthSegment {
  label: string
  startCol: number
  endCol: number
}

/**
 * 月份段：按列聚合，只要该列任意一天进入新月份就换段（等价于取该列最后一天所在月份）。
 * 12 周窗口里 9/1 落在列中间时，标签从该列开始，而不是漂到下一列。
 */
const monthSegments = computed<MonthSegment[]>(() => {
  const result: MonthSegment[] = []
  const formatter = new Intl.DateTimeFormat('zh-CN', { month: 'numeric' })
  for (let col = 0; col < weeks.value; col += 1) {
    const days = cells.value.slice(col * 7, col * 7 + 7)
    if (days.length === 0) break
    const last = parseDate(days[days.length - 1].date)
    const label = `${formatter.format(last).replace(/月$/, '')}月`
    const current = result[result.length - 1]
    if (current && current.label === label) current.endCol = col
    else result.push({ label, startCol: col, endCol: col })
  }
  return result
})

const activeIndex = ref(-1)
const activeDay = computed(() => (activeIndex.value >= 0 ? cells.value[activeIndex.value] ?? null : null))
const activeLevel = computed(() => (activeDay.value ? level(metric(activeDay.value)) : 'l0'))
const cellRefs = ref<Array<HTMLButtonElement | null>>([])

function formatDay(dateKey: string): string {
  const date = parseDate(dateKey)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${WEEKDAYS[date.getDay()]}`
}

function daySummary(day: ActivityDay): string {
  if (props.role === 'teacher') {
    if (day.answers <= 0) return '无学习记录'
    return `作答 ${day.answers} 次 · 活跃 ${day.active_students ?? 0} 人`
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
        <span class="heat-stat__value"><CountUpNumber :value="stat.value" /></span>
        <span class="heat-stat__label">{{ stat.label }}</span>
      </div>
    </div>

    <div class="heat-toolbar">
      <p class="heat-readout" aria-live="polite">
        <template v-if="activeDay">
          <i class="heat-readout__dot" :class="activeLevel" aria-hidden="true" />
          <span class="heat-readout__date">{{ formatDay(activeDay.date) }}</span>
          <span class="heat-readout__value">{{ daySummary(activeDay) }}</span>
        </template>
        <span v-else class="heat-readout__hint">悬停、聚焦或按方向键查看每日记录</span>
      </p>

      <div class="heat-legend" aria-hidden="true">
        <span>少</span>
        <i class="l0" /><i class="l1" /><i class="l2" /><i class="l3" /><i class="l4" />
        <span>多</span>
      </div>
    </div>

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

    <div
      class="heat-months"
      :style="{ gridTemplateColumns: `repeat(${weeks}, 13px)` }"
      aria-hidden="true"
    >
      <span
        v-for="segment in monthSegments"
        :key="segment.startCol"
        :style="{ gridColumn: `${segment.startCol + 1} / ${segment.endCol + 2}` }"
      >
        {{ segment.label }}
      </span>
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
  font-variant-numeric: tabular-nums;
}

.heat-stat__label {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--muted);
  white-space: nowrap;
}

.heat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.heat-readout {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 24px;
  margin: 0;
  padding: 3px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-alt);
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
}

.heat-readout__dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--heat-0);
}

.heat-readout__dot.l1 {
  background: var(--heat-1);
}

.heat-readout__dot.l2 {
  background: var(--heat-2);
}

.heat-readout__dot.l3 {
  background: var(--heat-3);
}

.heat-readout__dot.l4 {
  background: var(--heat-4);
}

.heat-readout__date {
  color: var(--text);
  font-weight: 600;
  white-space: nowrap;
}

.heat-readout__value {
  white-space: nowrap;
}

.heat-readout__hint {
  color: var(--tertiary);
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
  transform: scale(1.05);
  outline: none;
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--lime);
}

.heat-cell.is-active {
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--lime-deep);
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
  gap: 7px;
  justify-content: center;
  margin-top: -2px;
  font-size: 9.5px;
  line-height: 1;
  color: var(--tertiary);
}

.heat-months span {
  overflow: visible;
  text-align: center;
  white-space: nowrap;
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

  .heat-toolbar {
    gap: 6px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .heat-cell {
    transition: none;
  }

  .heat-cell:hover,
  .heat-cell:focus-visible {
    transform: none;
  }
}
</style>
