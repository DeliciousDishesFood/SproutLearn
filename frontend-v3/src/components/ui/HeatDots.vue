<script setup lang="ts">
// 学习热力：52 周单块 SVG、周日对齐、未来格不计数；月份按列首左对齐。
import { computed, nextTick, ref } from 'vue'
import type { ActivityDay } from '@/api/contract'
import CountUpNumber from '@/components/ui/CountUpNumber.vue'

const props = withDefaults(
  defineProps<{
    days: ActivityDay[]
    weeks?: number
    role: 'teacher' | 'student'
  }>(),
  { weeks: 52 },
)

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const PITCH = 24
const DOT = 7
const TOP = 18

const weeks = computed(() => Math.max(1, props.weeks))
const svgWidth = computed(() => weeks.value * PITCH)
const svgHeight = TOP + 7 * PITCH

interface Cell {
  date: string
  col: number
  row: number
  future: boolean
  metric: number
  day: ActivityDay | null
}

function keyOf(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function parseDate(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const today = (() => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
})()

/** 结束于本周周六，向前推 N 周，保证第一列是周日。 */
const startDate = computed(() => {
  const end = new Date(today.getFullYear(), today.getMonth(), today.getDate() + (6 - today.getDay()))
  return new Date(end.getFullYear(), end.getMonth(), end.getDate() - (weeks.value * 7 - 1))
})

const byDate = computed(() => {
  const map = new Map<string, ActivityDay>()
  props.days.forEach((day) => map.set(day.date, day))
  return map
})

function metricOf(day: ActivityDay): number {
  if (props.role === 'student') {
    const xp = day.xp ?? 0
    return xp > 0 ? xp : day.answers
  }
  return day.answers
}

const cells = computed<Cell[]>(() => {
  const result: Cell[] = []
  for (let col = 0; col < weeks.value; col += 1) {
    for (let row = 0; row < 7; row += 1) {
      const date = new Date(
        startDate.value.getFullYear(),
        startDate.value.getMonth(),
        startDate.value.getDate() + col * 7 + row,
      )
      const key = keyOf(date)
      const day = byDate.value.get(key) ?? null
      const future = date.getTime() > today.getTime()
      result.push({
        date: key,
        col,
        row,
        future,
        metric: future || !day ? 0 : metricOf(day),
        day,
      })
    }
  }
  return result
})

const max = computed(() => Math.max(0, ...cells.value.map((cell) => cell.metric)))

function level(value: number): 'l0' | 'l1' | 'l2' | 'l3' | 'l4' {
  if (value <= 0 || max.value <= 0) return 'l0'
  const ratio = value / max.value
  if (ratio <= 0.25) return 'l1'
  if (ratio <= 0.5) return 'l2'
  if (ratio <= 0.75) return 'l3'
  return 'l4'
}

const maxAnswers = computed(() => Math.max(0, ...cells.value.map((cell) => cell.day?.answers ?? 0)))
const maxXp = computed(() => Math.max(0, ...cells.value.map((cell) => cell.day?.xp ?? 0)))
const todayCell = computed(() => cells.value.find((cell) => cell.date === keyOf(today)) ?? null)

/** 图上方 4 项统计（未来格不计入）。 */
const stats = computed<Array<{ label: string; value: number }>>(() => {
  const past = cells.value.filter((cell) => !cell.future)
  if (props.role === 'teacher') {
    return [
      { label: `${weeks.value}周作答`, value: past.reduce((acc, cell) => acc + (cell.day?.answers ?? 0), 0) },
      { label: '活跃天数', value: past.filter((cell) => (cell.day?.answers ?? 0) > 0).length },
      { label: '单日最高', value: maxAnswers.value },
      { label: '今日活跃', value: todayCell.value?.day?.active_students ?? 0 },
    ]
  }
  return [
    { label: `${weeks.value}周经验`, value: past.reduce((acc, cell) => acc + (cell.day?.xp ?? 0), 0) },
    {
      label: '活跃天数',
      value: past.filter((cell) => (cell.day?.xp ?? 0) > 0 || (cell.day?.answers ?? 0) > 0).length,
    },
    { label: '单日最高', value: maxXp.value },
    { label: '今日 XP', value: todayCell.value?.day?.xp ?? 0 },
  ]
})

/** 月份标签：只在该列周日进入新月份时出现，位置左对齐到列首。 */
const monthLabels = computed<Array<{ x: number; label: string }>>(() => {
  const result: Array<{ x: number; label: string }> = []
  let previous = ''
  for (let col = 0; col < weeks.value; col += 1) {
    const date = new Date(
      startDate.value.getFullYear(),
      startDate.value.getMonth(),
      startDate.value.getDate() + col * 7,
    )
    const label = `${date.getMonth() + 1}月`
    if (label !== previous) {
      result.push({ x: col * PITCH, label })
      previous = label
    }
  }
  return result
})

const activeIndex = ref(-1)
const activeCell = computed(() => (activeIndex.value >= 0 ? cells.value[activeIndex.value] ?? null : null))
const activeLevel = computed(() => (activeCell.value ? level(activeCell.value.metric) : 'l0'))
const cellRefs = ref<Array<SVGRectElement | null>>([])

function formatDay(dateKey: string): string {
  const date = parseDate(dateKey)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${WEEKDAYS[date.getDay()]}`
}

function daySummary(cell: Cell): string {
  if (!cell.day) return '无学习记录'
  if (props.role === 'teacher') {
    if (cell.day.answers <= 0) return '无学习记录'
    return `作答 ${cell.day.answers} 次 · 活跃 ${cell.day.active_students ?? 0} 人`
  }
  const xp = cell.day.xp ?? 0
  if (xp <= 0 && cell.day.answers <= 0) return '无学习记录'
  return `+${xp} XP · 作答 ${cell.day.answers} 次`
}

function readText(cell: Cell): string {
  if (cell.future) return `${formatDay(cell.date)} · 未来日期`
  return `${formatDay(cell.date)} · ${daySummary(cell)}`
}

function setCellRef(el: unknown, index: number): void {
  cellRefs.value[index] = el as SVGRectElement | null
}

function select(index: number, focus = false): void {
  if (index < 0 || index >= cells.value.length) return
  if (cells.value[index]?.future) return
  activeIndex.value = index
  if (focus) {
    void nextTick(() => cellRefs.value[index]?.focus())
  }
}

/** 键盘：左右按周、上下按天；未来格跳过。 */
function onKeydown(event: KeyboardEvent): void {
  const total = cells.value.length
  if (total === 0) return
  const current = activeIndex.value >= 0 ? activeIndex.value : cells.value.findIndex((cell) => !cell.future)
  if (current < 0) return
  let next = current
  if (event.key === 'ArrowLeft') next = current - 7
  else if (event.key === 'ArrowRight') next = current + 7
  else if (event.key === 'ArrowUp') next = current - 1
  else if (event.key === 'ArrowDown') next = current + 1
  else return
  event.preventDefault()
  next = Math.max(0, Math.min(total - 1, next))
  if (cells.value[next]?.future) return
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
        <template v-if="activeCell">
          <i class="heat-readout__dot" :class="activeLevel" aria-hidden="true" />
          <span class="heat-readout__date">{{ formatDay(activeCell.date) }}</span>
          <span class="heat-readout__value">{{ daySummary(activeCell) }}</span>
        </template>
        <span v-else class="heat-readout__hint">悬停、聚焦或按方向键查看每日记录</span>
      </p>

      <div class="heat-legend" aria-hidden="true">
        <span>少</span>
        <i class="l0" /><i class="l1" /><i class="l2" /><i class="l3" /><i class="l4" />
        <span>多</span>
      </div>
    </div>

    <p v-if="max === 0" class="heat-empty">近 {{ weeks }} 周暂无学习记录</p>

    <div class="heat-scroll">
      <svg
        class="heat-svg"
        :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
        role="group"
        :aria-label="`最近 ${weeks} 周学习热力`"
        @keydown="onKeydown"
      >
        <text
          v-for="month in monthLabels"
          :key="month.label + month.x"
          class="heat-month"
          :x="month.x"
          y="12"
        >
          {{ month.label }}
        </text>

        <g v-for="(cell, index) in cells" :key="cell.date">
          <rect
            v-if="!cell.future"
            :ref="(el) => setCellRef(el, index)"
            class="heat-hit"
            :x="cell.col * PITCH"
            :y="TOP + cell.row * PITCH"
            :width="PITCH"
            :height="PITCH"
            :tabindex="activeIndex === index ? 0 : -1"
            role="button"
            :aria-label="readText(cell)"
            @mouseenter="select(index)"
            @focus="select(index)"
            @click="select(index)"
          />
          <circle
            class="heat-dot"
            :class="[level(cell.metric), { 'is-future': cell.future, 'is-active': activeIndex === index }]"
            :cx="cell.col * PITCH + PITCH / 2"
            :cy="TOP + cell.row * PITCH + PITCH / 2"
            :r="DOT"
            aria-hidden="true"
          />
        </g>
      </svg>
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
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}

.heat-stat__label {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
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
  font-size: 12px;
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
  color: var(--text-3);
}

.heat-empty {
  margin: 0;
  color: var(--text-3);
  font-size: 12px;
}

.heat-scroll {
  overflow-x: auto;
  padding-bottom: 2px;
}

.heat-svg {
  display: block;
  width: 100%;
  height: auto;
}

.heat-month {
  fill: var(--text-3);
  font-size: 11px;
  font-family: var(--font);
}

.heat-hit {
  fill: transparent;
  cursor: pointer;
  outline: none;
}

.heat-hit:focus-visible {
  outline: var(--focus-ring);
  outline-offset: -2px;
}

.heat-dot {
  fill: var(--heat-0);
  pointer-events: none;
  transition: transform 0.12s ease;
}

.heat-dot.l1 {
  fill: var(--heat-1);
}

.heat-dot.l2 {
  fill: var(--heat-2);
}

.heat-dot.l3 {
  fill: var(--heat-3);
}

.heat-dot.l4 {
  fill: var(--heat-4);
}

.heat-dot.is-future {
  fill: var(--heat-0);
  opacity: 0.45;
}

.heat-dot.is-active {
  stroke: var(--lime-text);
  stroke-width: 2;
}

.heat-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-3);
  font-size: 11.5px;
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

@media (max-width: 900px) {
  /* 窄屏保持 24px 命中区，图内横向滚动，不撑破页面。 */
  .heat-svg {
    width: auto;
    min-width: 1248px;
    height: auto;
  }
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
  .heat-dot {
    transition: none;
  }
}
</style>
