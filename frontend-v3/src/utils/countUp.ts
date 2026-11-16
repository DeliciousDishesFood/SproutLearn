/**
 * 数字滚动 count-up（参考 aitlas `utils/countUp.ts`）。
 *
 * - rAF + ease-out cubic，默认 700ms 从 0 滚到目标值；
 * - 只写 textContent（容器带 tabular-nums，宽度不抖，不动布局）；
 * - prefers-reduced-motion 直显终值；
 * - 返回取消函数：组件卸载/数据刷新时调用，防泄漏与竞态。
 */
export interface CountUpOptions {
  /** 动画时长（ms），默认 700 */
  duration?: number
  /** 小数位，默认 0（百分比/平均分可传 1 或 2） */
  decimals?: number
}

const NUMBER_LOCALE = 'zh-CN'

function format(n: number, decimals: number): string {
  const digits = Math.min(Math.max(Math.trunc(decimals) || 0, 0), 2)
  const value = digits > 0 ? Number(n.toFixed(digits)) : Math.round(n)
  return value.toLocaleString(NUMBER_LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

export function countUp(el: HTMLElement, target: number, opts: CountUpOptions = {}): () => void {
  const duration = opts.duration ?? 700
  const decimals = opts.decimals ?? 0

  // 非法值/零时长/减少动效：直显终值
  if (!Number.isFinite(target) || duration <= 0 || prefersReducedMotion()) {
    el.textContent = format(Number.isFinite(target) ? target : 0, decimals)
    return () => {}
  }

  let rafId = 0
  let cancelled = false
  const start = performance.now()

  el.textContent = format(0, decimals)

  const tick = (now: number) => {
    if (cancelled) return
    // rAF 时间戳可能早于 start（同一帧内调用），负进度会让首帧显示 -1，夹到 [0,1]
    const p = Math.min(Math.max((now - start) / duration, 0), 1)
    // ease-out cubic：先快后慢，收尾稳
    const eased = 1 - Math.pow(1 - p, 3)
    el.textContent = format(target * eased, decimals)
    if (p < 1) rafId = requestAnimationFrame(tick)
  }

  rafId = requestAnimationFrame(tick)

  return () => {
    cancelled = true
    cancelAnimationFrame(rafId)
  }
}
