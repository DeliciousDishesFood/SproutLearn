<script setup lang="ts">
import { Check } from 'lucide-vue-next'

defineProps<{
  /** 当前点亮的节点（0 起）；由真实状态推进，不做循环动画 */
  active: number
}>()

const NODES = [
  { id: '01', title: '完成作答', caption: '切换题目也不丢答案' },
  { id: '02', title: '获得有依据的讲评', caption: '官方解析与 AI 补充分开标注' },
  { id: '03', title: '记录成长反馈', caption: '作答结果回流学习记录' },
]

/* 成长条只表达「有记录」，不宣称任何真实数据 */
const BARS = [38, 52, 44, 66, 58, 78]
</script>

<template>
  <div class="gt">
    <ol class="gt__nodes">
      <li
        v-for="(node, index) in NODES"
        :key="node.id"
        class="node"
        :class="{
          'is-current': index === active,
          'is-done': index < active,
          'is-pending': index > active,
        }"
      >
        <div class="node__rail" aria-hidden="true">
          <span class="node__dot" />
          <span
            class="node__seg"
            :class="{ 'is-filled': index < active, 'is-tail': index === NODES.length - 1 }"
          />
        </div>

        <div class="node__body">
          <p class="node__num mono">{{ node.id }}</p>
          <h3 class="node__title">{{ node.title }}</h3>
          <p class="node__cap">{{ node.caption }}</p>

          <div class="node__frag">
            <template v-if="index === 0">
              <div class="frag__top">
                <span class="frag__tag mono">单选题</span>
                <span class="frag__meta">自动保存</span>
              </div>
              <p class="frag__stem">靠墙围矩形，求面积最大值</p>
              <p class="frag__row is-on"><span class="frag__key mono">A</span>x = 10，S = 200</p>
              <p class="frag__row"><span class="frag__key mono">B</span>x = 10，S = 100</p>
              <p class="frag__note"><Check :size="11" :stroke-width="3" aria-hidden="true" />已保存</p>
            </template>

            <template v-else-if="index === 1">
              <p class="frag__tag is-official">官方解析</p>
              <p class="frag__stem">先由墙长确定 x 的取值范围，再在区间内求最值。</p>
              <p class="frag__tag is-ai">AI 补充</p>
              <p class="frag__quote">端点不在定义域内，答案需要重新讨论。</p>
            </template>

            <template v-else>
              <p class="frag__meta">学习记录</p>
              <p class="frag__stem">二次函数 · 本次练习</p>
              <div class="frag__bars" aria-hidden="true">
                <i v-for="(bar, i) in BARS" :key="i" :style="{ height: `${bar}%` }" />
              </div>
              <p class="frag__note">已回流成长页</p>
            </template>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.gt {
  --gt-dim: var(--graphite-ink-3);
  --gt-line: rgba(255, 255, 255, 0.14);
  width: 100%;
}

.gt__nodes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.node {
  min-width: 0;
  padding-right: 22px;
}

.node:last-child {
  padding-right: 0;
}

.node__rail {
  display: flex;
  align-items: center;
  height: 12px;
}

.node__dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  background: transparent;
  transition:
    background var(--dur-slow, 520ms) var(--ease-premium),
    border-color var(--dur-slow, 520ms) var(--ease-premium),
    box-shadow var(--dur-slow, 520ms) var(--ease-premium),
    transform var(--dur-slow, 520ms) var(--ease-premium);
}

.node__seg {
  flex: 1;
  height: 1px;
  margin-left: 10px;
  background: var(--gt-line);
}

.node__seg::after {
  content: '';
  display: block;
  height: 1px;
  background: var(--lime);
  transform: scaleX(0);
  transform-origin: left center;
  transition: transform 520ms var(--ease-premium);
}

.node__seg.is-filled::after {
  transform: scaleX(1);
}

/* 最后一段是虚线尾巴：轨迹在第三个节点之后继续 */
.node__seg.is-tail {
  background: repeating-linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.2) 0 4px,
    transparent 4px 9px
  );
}

.node__seg.is-tail::after {
  display: none;
}

.node.is-done .node__dot {
  border-color: var(--lime);
  background: var(--lime);
}

.node.is-current .node__dot {
  border-color: var(--lime);
  background: var(--lime);
  box-shadow:
    0 0 0 4px rgba(154, 230, 0, 0.18),
    0 0 14px rgba(154, 230, 0, 0.45);
  transform: scale(1.25);
}

.node__body {
  margin-top: 14px;
  min-width: 0;
}

.node__num {
  margin: 0;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: var(--gt-dim);
}

.node__title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.01em;
  color: rgba(255, 255, 255, 0.46);
}

.node__cap {
  margin-top: 4px;
  font-size: 11.5px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.32);
}

.node.is-current .node__num,
.node.is-done .node__num {
  color: var(--lime);
}

.node.is-current .node__title,
.node.is-done .node__title {
  color: var(--graphite-ink);
}

.node.is-current .node__cap,
.node.is-done .node__cap {
  color: var(--graphite-ink-3);
}

.node__frag {
  margin-top: 14px;
  padding: 12px 12px 11px;
  min-height: 128px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 10px;
  background: var(--graphite-2);
  opacity: 0.62;
  transition:
    opacity 260ms var(--ease-premium),
    border-color 260ms var(--ease-premium);
}

.node.is-current .node__frag,
.node.is-done .node__frag {
  opacity: 1;
  border-color: rgba(255, 255, 255, 0.14);
}

.node.is-current .node__frag {
  border-color: rgba(154, 230, 0, 0.34);
}

.frag__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.frag__tag {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 4px;
  font-size: 9.5px;
  letter-spacing: 0.06em;
  color: rgba(255, 255, 255, 0.68);
}

.frag__tag.is-official {
  border-color: rgba(154, 230, 0, 0.4);
  color: var(--lime);
}

.frag__tag.is-ai {
  border-color: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.6);
  border-style: dashed;
}

.frag__meta {
  font-size: 10px;
  color: var(--graphite-ink-3);
  white-space: nowrap;
}

.frag__stem {
  margin-top: 9px;
  font-size: 11.5px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.72);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.frag__row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 7px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.58);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.frag__row.is-on {
  padding: 4px 6px;
  margin-left: -6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.frag__key {
  color: rgba(255, 255, 255, 0.4);
  font-size: 10px;
}

.frag__row.is-on .frag__key {
  color: var(--lime);
}

.frag__quote {
  margin-top: 7px;
  padding-left: 8px;
  border-left: 1px solid rgba(255, 255, 255, 0.22);
  font-size: 10.5px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.58);
}

.frag__note {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 10px;
  font-size: 10px;
  color: var(--lime);
}

.frag__bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 34px;
  margin-top: 10px;
}

.frag__bars i {
  flex: 1;
  border-radius: 1px;
  background: rgba(255, 255, 255, 0.16);
}

.frag__bars i:last-child {
  background: var(--lime);
}

/* 窄屏：只保留编号与节点名，避免挤压登录表单 */
@media (max-width: 900px) {
  .node {
    padding-right: 14px;
  }

  .node__body {
    margin-top: 10px;
  }

  .node__cap,
  .node__frag {
    display: none;
  }

  .node__title {
    font-size: 11.5px;
    line-height: 1.4;
  }

  .node__num {
    font-size: 9.5px;
  }
}
</style>
