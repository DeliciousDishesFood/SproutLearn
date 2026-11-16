// 无依赖对比度检查：直接解析 tokens.css，校验正文/辅助文字与焦点轮廓的 WCAG 对比度。
// 用法：node scripts/contrast-check.mjs
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const css = readFileSync(resolve(here, '../src/design/tokens.css'), 'utf8')

function parseBlock(selector) {
  const start = css.indexOf(selector)
  if (start < 0) throw new Error(`找不到 token 块：${selector}`)
  const open = css.indexOf('{', start)
  const close = css.indexOf('}', open)
  const body = css.slice(open + 1, close)
  const tokens = {}
  for (const line of body.split('\n')) {
    const match = line.match(/(--[\w-]+)\s*:\s*([^;]+);/)
    if (match) tokens[match[1]] = match[2].trim()
  }
  return tokens
}

const light = parseBlock(':root')
const dark = parseBlock("[data-theme='dark']")

function channel(value) {
  const v = value / 255
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
}

function luminance(hex) {
  const clean = hex.replace('#', '')
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

function ratio(fg, bg) {
  const a = luminance(fg)
  const b = luminance(bg)
  const [hi, lo] = a > b ? [a, b] : [b, a]
  return (hi + 0.05) / (lo + 0.05)
}

const checks = [
  ['正文 text / surface', 'text', 'surface', 4.5],
  ['辅助 muted / surface', 'muted', 'surface', 4.5],
  ['辅助 text-3 / surface', 'text-3', 'surface', 4.5],
  ['辅助 muted / surface-alt', 'muted', 'surface-alt', 4.5],
  ['辅助 text-3 / surface-alt', 'text-3', 'surface-alt', 4.5],
  ['表头 text-3 / surface-alt', 'text-3', 'surface-alt', 4.5],
  ['正文 text / bg', 'text', 'bg', 4.5],
  ['危险 danger / surface', 'danger', 'surface', 4.5],
  ['焦点轮廓 lime-text / surface', 'lime-text', 'surface', 4.5],
  ['焦点轮廓 lime-text / surface-alt', 'lime-text', 'surface-alt', 4.5],
  ['大标题 text / surface（≥3）', 'text', 'surface', 3],
  // v1.3 生长轨迹：石墨品牌画布与冷灰舞台
  ['石墨正文 graphite-ink / graphite', 'graphite-ink', 'graphite', 4.5],
  ['石墨次级 graphite-ink-2 / graphite', 'graphite-ink-2', 'graphite', 4.5],
  ['石墨辅助 graphite-ink-3 / graphite', 'graphite-ink-3', 'graphite', 4.5],
  ['石墨次级 graphite-ink-2 / graphite-2', 'graphite-ink-2', 'graphite-2', 4.5],
  ['青柠按钮 lime-ink / lime', 'lime-ink', 'lime', 4.5],
  ['青柠悬停 lime-ink / lime-hi', 'lime-ink', 'lime-hi', 4.5],
  ['选中选项 option-selected-ink / option-selected-bg', 'option-selected-ink', 'option-selected-bg', 4.5],
  ['冷灰舞台正文 text / stage-cool', 'text', 'stage-cool', 4.5],
  ['冷灰舞台次级 stage-ink-2 / stage-cool', 'stage-ink-2', 'stage-cool', 4.5],
  ['冷灰舞台焦点 lime-text / stage-cool', 'lime-text', 'stage-cool', 4.5],
]

let failed = 0
const results = []

for (const [theme, tokens] of [
  ['light', light],
  ['dark', { ...light, ...dark }],
]) {
  for (const [label, fg, bg, min] of checks) {
    const foreground = tokens[`--${fg}`]
    const background = tokens[`--${bg}`]
    if (!foreground || !background) {
      results.push({ theme, label, ratio: null, min, pass: false, note: 'token 缺失' })
      failed += 1
      continue
    }
    const value = Number(ratio(foreground, background).toFixed(2))
    const pass = value >= min
    if (!pass) failed += 1
    results.push({
      theme,
      label,
      fg: foreground,
      bg: background,
      ratio: value,
      min,
      pass,
    })
  }
}

for (const item of results) {
  const mark = item.pass ? 'PASS' : 'FAIL'
  console.log(
    `${mark}  ${item.theme.padEnd(5)}  ${String(item.ratio ?? '-').padStart(6)}  ≥${item.min}  ${item.label}` +
      (item.note ? ` (${item.note})` : ''),
  )
}

console.log(`\n${results.length - failed}/${results.length} 通过`)
console.log(JSON.stringify({ generatedAt: new Date().toISOString(), failed, results }, null, 2))

process.exit(failed > 0 ? 1 : 0)
