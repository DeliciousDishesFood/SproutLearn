<script setup lang="ts">
import { computed } from 'vue'

type SaveStateValue = 'idle' | 'saving' | 'saved' | 'error'

const props = defineProps<{
  /** 题目总数 */
  total: number
  /** 当前题下标（0 起） */
  currentIndex: number
  /** 每题是否已作答 */
  answered: boolean[]
  /** 只用于给当前题显示保存中／保存失败，不改动保存状态机 */
  saveState: SaveStateValue
}>()

defineEmits<{ (event: 'jump', index: number): void }>()

const answeredCount = computed(() => props.answered.filter(Boolean).length)

function pad(value: number): string {
  return String(value).padStart(2, '0')
}
</script>

<template>
  <div class="answer-sheet">
    <header class="answer-sheet__head">
      <h2 class="answer-sheet__title">作答轨迹</h2>
      <p class="answer-sheet__count mono">{{ pad(answeredCount) }} / {{ pad(total) }}</p>
    </header>

    <!-- 细轨迹：一题一格，当前题是唯一亮点 -->
    <div class="answer-sheet__track" aria-hidden="true">
      <span
        v-for="(done, index) in answered"
        :key="`t-${index}`"
        class="tick"
        :class="{ 'is-done': done, 'is-current': index === currentIndex }"
      />
    </div>

    <div class="answer-sheet__grid" role="group" aria-label="跳转到题目">
      <button
        v-for="(done, index) in answered"
        :key="`c-${index}`"
        class="cell mono"
        :class="{
          'is-done': done,
          'is-current': index === currentIndex,
          'is-saving': index === currentIndex && saveState === 'saving',
          'is-failed': index === currentIndex && saveState === 'error',
        }"
        type="button"
        :aria-current="index === currentIndex ? 'step' : undefined"
        :aria-label="`第 ${index + 1} 题，${done ? '已作答' : '未作答'}`"
        @click="$emit('jump', index)"
      >
        {{ pad(index + 1) }}
      </button>
    </div>

    <ul class="answer-sheet__legend">
      <li><i class="legend-mark is-done" aria-hidden="true" />已答</li>
      <li><i class="legend-mark is-current" aria-hidden="true" />当前</li>
      <li><i class="legend-mark" aria-hidden="true" />未答</li>
      <li v-if="saveState === 'error'"><i class="legend-mark is-failed" aria-hidden="true" />保存失败</li>
    </ul>
  </div>
</template>

<style scoped>
.answer-sheet {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.answer-sheet__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.answer-sheet__title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.answer-sheet__count {
  font-size: 11.5px;
  color: var(--text-3);
}

.answer-sheet__track {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 8px;
}

.tick {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: var(--line);
  transition:
    background 260ms var(--ease-premium),
    height 260ms var(--ease-premium);
}

.tick.is-done {
  background: var(--text);
}

.tick.is-current {
  height: 8px;
  background: var(--lime);
}

.answer-sheet__grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}

.cell {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 140ms ease,
    border-color 140ms ease,
    color 140ms ease;
}

.cell:hover {
  border-color: var(--line-strong);
  color: var(--text);
}

.cell.is-done {
  border-color: var(--text);
  background: var(--text);
  color: var(--surface);
}

.cell.is-current {
  border-color: var(--lime);
  background: var(--lime);
  color: var(--lime-ink);
  box-shadow:
    0 0 0 2px var(--surface),
    0 0 0 3px var(--text);
}

.cell.is-failed {
  border-color: var(--danger);
  background: var(--danger-soft);
  color: var(--danger);
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--danger);
}

.cell.is-saving {
  border-color: var(--lime);
}

.answer-sheet__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text-3);
  font-size: 11.5px;
}

.answer-sheet__legend li {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend-mark {
  width: 9px;
  height: 9px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--surface);
}

.legend-mark.is-done {
  border-color: var(--text);
  background: var(--text);
}

.legend-mark.is-current {
  border-color: var(--lime);
  background: var(--lime);
}

.legend-mark.is-failed {
  border-color: var(--danger);
  background: var(--danger-soft);
}

@media (max-width: 900px) {
  .cell {
    height: 44px;
    font-size: 13px;
  }
}
</style>
