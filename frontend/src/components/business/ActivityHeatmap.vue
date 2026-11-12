<!-- 活跃热力图：7 行 × N 列（默认 12 周 = 84 格），5 档分位色，悬停显示当日详情。 -->
<script setup lang="ts">
import { computed } from 'vue'

export interface HeatmapDay {
  date: string
  count: number
  xp?: number
}

const props = withDefaults(
  defineProps<{
    days: HeatmapDay[]
    weeks?: number
    countLabel?: string
    extraLabel?: string
    emptyHint?: string
  }>(),
  {
    weeks: 12,
    countLabel: '答题',
    extraLabel: '经验',
    emptyHint: '还没有活跃记录，完成一次练习后这里就会亮起来。',
  },
)

const WEEKDAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']
const WEEKDAY_FULL = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const LEVELS = [1, 2, 3, 4, 5] as const

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  next.setDate(next.getDate() + days)
  return next
}

function quantile(sorted: number[], ratio: number): number {
  if (sorted.length === 0) return 0
  const position = (sorted.length - 1) * ratio
  const lower = Math.floor(position)
  const upper = Math.ceil(position)
  if (lower === upper) return sorted[lower]
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower)
}

const today = new Date()
const todayKey = dateKey(today)

const dayMap = computed(() => {
  const map = new Map<string, HeatmapDay>()
  for (const day of props.days) {
    if (!day || typeof day.date !== 'string') continue
    map.set(day.date.slice(0, 10), day)
  }
  return map
})

const thresholds = computed(() => {
  const counts = props.days
    .filter((day) => day && day.count > 0 && day.date.slice(0, 10) <= todayKey)
    .map((day) => day.count)
    .sort((left, right) => left - right)
  if (counts.length === 0) return [] as number[]
  return [0.2, 0.4, 0.6, 0.8].map((ratio) => quantile(counts, ratio))
})

function levelOf(count: number): number {
  if (!count || count <= 0) return 0
  const cuts = thresholds.value
  let level = 1
  for (const cut of cuts) {
    if (count >= cut) level += 1
  }
  return Math.min(5, level)
}

interface HeatCell {
  key: string
  date: string
  count: number
  xp: number | null
  level: number
  future: boolean
  weekday: string
}

const cells = computed<HeatCell[]>(() => {
  const weekCount = Math.max(1, Math.floor(props.weeks))
  const weekdayOffset = (today.getDay() + 6) % 7
  const lastMonday = addDays(today, -weekdayOffset)
  const firstMonday = addDays(lastMonday, -7 * (weekCount - 1))
  const list: HeatCell[] = []

  for (let index = 0; index < weekCount * 7; index += 1) {
    const date = addDays(firstMonday, index)
    const key = dateKey(date)
    const future = key > todayKey
    const record = future ? undefined : dayMap.value.get(key)
    const count = record?.count ?? 0
    list.push({
      key,
      date: key,
      count,
      xp: typeof record?.xp === 'number' ? record.xp : null,
      level: future ? -1 : levelOf(count),
      future,
      weekday: WEEKDAY_FULL[(date.getDay() + 6) % 7],
    })
  }
  return list
})

const totalCount = computed(() =>
  cells.value.reduce((sum, cell) => sum + (cell.future ? 0 : cell.count), 0),
)

const rangeLabel = computed(() => {
  const first = cells.value[0]
  const last = cells.value[cells.value.length - 1]
  if (!first || !last) return ''
  return `${first.date.slice(5).replace('-', '/')} - ${last.date.slice(5).replace('-', '/')}`
})

function cellTitle(cell: HeatCell): string {
  const parts = [`${cell.date} ${cell.weekday}`, `${cell.count} ${props.countLabel}`]
  if (cell.xp !== null) parts.push(`${cell.xp} ${props.extraLabel}`)
  return parts.join(' · ')
}
</script>

<template>
  <div class="heatmap">
    <div class="heatmap__body">
      <div class="heatmap__weekdays" aria-hidden="true">
        <span v-for="(label, index) in WEEKDAY_LABELS" :key="index" class="heatmap__weekday">
          {{ index % 2 === 0 ? label : '' }}
        </span>
      </div>

      <div class="heatmap__scroll">
        <div
          class="heatmap__grid"
          :style="{ gridTemplateColumns: `repeat(${Math.max(1, Math.floor(weeks))}, 1fr)` }"
          role="img"
          :aria-label="`近 ${weeks} 周活跃热力图，共 ${totalCount} 次${countLabel}`"
        >
          <div
            v-for="cell in cells"
            :key="cell.key"
            class="heatmap__cell"
            :class="[
              cell.future ? 'heatmap__cell--future' : `heatmap__cell--l${cell.level}`,
              { 'heatmap__cell--active': !cell.future },
            ]"
            :title="cell.future ? undefined : cellTitle(cell)"
          >
            <span v-if="!cell.future" class="heatmap__tip" role="presentation">
              <strong>{{ cell.date.slice(5).replace('-', '/') }} {{ cell.weekday }}</strong>
              <span>{{ cell.count }} {{ countLabel }}</span>
              <span v-if="cell.xp !== null">{{ cell.xp }} {{ extraLabel }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <footer class="heatmap__foot">
      <span class="heatmap__range">{{ rangeLabel }}</span>
      <span class="heatmap__legend">
        <span class="heatmap__legend-label">少</span>
        <span
          v-for="level in LEVELS"
          :key="level"
          class="heatmap__swatch"
          :class="`heatmap__swatch--l${level}`"
          aria-hidden="true"
        />
        <span class="heatmap__legend-label">多</span>
      </span>
    </footer>

    <p v-if="totalCount === 0" class="heatmap__empty">{{ emptyHint }}</p>
  </div>
</template>

<style scoped>
.heatmap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}

.heatmap__body {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: var(--sp-2);
  width: 100%;
  min-width: 0;
}

.heatmap__weekdays {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
  flex-shrink: 0;
}

.heatmap__weekday {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 14px;
  color: var(--color-text-muted);
  font-size: 10px;
  line-height: 1;
}

.heatmap__scroll {
  min-width: 0;
  flex: 1;
  max-width: 420px;
}

.heatmap__grid {
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
}

.heatmap__cell {
  position: relative;
  aspect-ratio: 1;
  min-height: 12px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: var(--color-surface-alt);
}

.heatmap__cell--active {
  border-color: color-mix(in srgb, var(--color-primary) 12%, transparent);
  cursor: default;
}

.heatmap__cell--future {
  background: transparent;
  border-color: transparent;
}

.heatmap__cell--l0 {
  background: var(--color-surface-alt);
}

.heatmap__cell--l1 {
  background: color-mix(in srgb, var(--color-primary) 18%, var(--color-surface));
}

.heatmap__cell--l2 {
  background: color-mix(in srgb, var(--color-primary) 36%, var(--color-surface));
}

.heatmap__cell--l3 {
  background: color-mix(in srgb, var(--color-primary) 56%, var(--color-surface));
}

.heatmap__cell--l4 {
  background: color-mix(in srgb, var(--color-primary) 78%, var(--color-surface));
}

.heatmap__cell--l5 {
  background: var(--color-primary);
}

.heatmap__cell--active:hover {
  outline: 1px solid var(--color-primary);
  outline-offset: 1px;
}

.heatmap__tip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  z-index: 10;
  display: none;
  flex-direction: column;
  gap: 1px;
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  background: var(--color-surface);
  box-shadow: var(--shadow-2);
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.5;
  white-space: nowrap;
  transform: translateX(-50%);
  pointer-events: none;
}

.heatmap__tip strong {
  color: var(--color-text);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.heatmap__cell--active:hover .heatmap__tip {
  display: flex;
}

.heatmap__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  flex-wrap: wrap;
  width: 100%;
  max-width: 442px;
  margin: 0 auto;
}

.heatmap__range {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}

.heatmap__legend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.heatmap__legend-label {
  color: var(--color-text-muted);
  font-size: 10px;
}

.heatmap__swatch {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 12%, transparent);
}

.heatmap__swatch--l1 {
  background: color-mix(in srgb, var(--color-primary) 18%, var(--color-surface));
}

.heatmap__swatch--l2 {
  background: color-mix(in srgb, var(--color-primary) 36%, var(--color-surface));
}

.heatmap__swatch--l3 {
  background: color-mix(in srgb, var(--color-primary) 56%, var(--color-surface));
}

.heatmap__swatch--l4 {
  background: color-mix(in srgb, var(--color-primary) 78%, var(--color-surface));
}

.heatmap__swatch--l5 {
  background: var(--color-primary);
}

.heatmap__empty {
  color: var(--color-text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}
</style>
