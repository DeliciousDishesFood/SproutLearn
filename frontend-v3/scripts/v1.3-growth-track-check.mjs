/**
 * v1.3「生长轨迹」浏览器验收：真实登录 → 真实作答 → 截图 + 断言。
 *
 * 前置：后端 127.0.0.1:8000、前端 127.0.0.1:5174 已启动，演示卷已发布（PAPER_ID 默认 129）。
 * 运行：node scripts/v1.3-growth-track-check.mjs
 * 依赖：借用同机 Demo 工程的 playwright-core（不写入本工程依赖）；可用 PLAYWRIGHT_CORE 覆盖路径。
 */
import { createRequire } from 'node:module'
import { mkdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const { chromium } = require(
  process.env.PLAYWRIGHT_CORE ||
    'E:/temporary-work/ui-v3-templates/node_modules/playwright-core',
)

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const OUT = join(ROOT, 'shots', 'v1.3-growth-track')
const BASE = 'http://127.0.0.1:5174'
const API = 'http://127.0.0.1:8000/api/v1'
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PAPER_ID = Number(process.env.PAPER_ID || 131)
const STUDENT = { class_code: 'C26A79', student_no: '20260101', password: 'Demo@123' }

let failures = 0
function check(label, ok, detail = '') {
  if (!ok) failures += 1
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? ` · ${detail}` : ''}`)
}

async function shot(page, name) {
  await page.screenshot({ path: join(OUT, name) })
  console.log(`[shot] ${name}`)
}

async function apiLogin() {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'student', ...STUDENT }),
    })
    const body = await res.json()
    if (res.ok) return body.data
    // 演示环境有登录频率限制：42901 时等待窗口过后重试，不伪造结果。
    if (body.code === 42901 && attempt < 2) {
      console.log('[info] 登录触发频率限制，等待 130s 后重试')
      await new Promise((resolve) => setTimeout(resolve, 130000))
      continue
    }
    throw new Error(`login failed: ${body.code} ${body.message}`)
  }
  throw new Error('login failed: rate limited')
}

async function startAttempt(token) {
  const res = await fetch(`${API}/papers/${PAPER_ID}/attempts`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  const body = await res.json()
  if (!res.ok) throw new Error(`start failed: ${body.code} ${body.message}`)
  return body.data.id
}

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch({ executablePath: EDGE, headless: true })

/* ── 1. 登录页（浅色 / 错误 / 深色 / 手机） ───────────────── */
{
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
  })
  const page = await context.newPage()
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1700)
  await shot(page, 'login-light-1440.png')

  const canvasBg = await page.evaluate(() => {
    const el = document.querySelector('.gt-canvas')
    return el ? getComputedStyle(el).backgroundColor : 'none'
  })
  check('登录画布为石墨深色', canvasBg === 'rgb(14, 18, 16)', canvasBg)

  // 错误态：真实调用接口，用错误口令
  await page.getByPlaceholder('教师账号').fill('nobody@school.edu.cn')
  await page.getByPlaceholder('登录密码').fill('Wrong12345')
  await page.getByRole('button', { name: '进入青芽' }).click()
  await page.waitForSelector('[role="alert"]', { timeout: 8000 })
  await page.waitForTimeout(300)
  await shot(page, 'login-error-1440.png')
  const alertText = await page.locator('[role="alert"]').innerText()
  check('登录错误提示可见', alertText.length > 0, alertText.trim())

  // 键盘焦点：Tab 到身份分段
  await page.keyboard.press('Tab')
  const outline = await page.evaluate(() => {
    const el = document.activeElement
    return el ? `${el.tagName.toLowerCase()} ${getComputedStyle(el).outlineWidth}` : 'none'
  })
  console.log(`[info] 登录页首个 Tab 焦点 · ${outline}`)

  // 深色主题
  await page.evaluate(() => localStorage.setItem('sprout.v3.theme', 'dark'))
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(1600)
  const darkTheme = await page.evaluate(() => document.documentElement.dataset.theme)
  check('深色主题已应用', darkTheme === 'dark', darkTheme)
  await shot(page, 'login-dark-1440.png')
  await page.evaluate(() => localStorage.removeItem('sprout.v3.theme'))
  await context.close()
}

{
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    locale: 'zh-CN',
  })
  const page = await context.newPage()
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1600)
  await shot(page, 'login-mobile-390.png')
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  check('登录 390 无横向溢出', overflow <= 0, `${overflow}px`)
  const submitInside = await page
    .getByRole('button', { name: '进入青芽' })
    .evaluate((el) => el.getBoundingClientRect().bottom <= window.innerHeight)
  check('登录 390 首屏可见主操作', submitInside)
  await context.close()
}

/* ── 2. 真实登录 + 进入真实作答 ───────────────────────────── */
const session = await apiLogin()
const attemptId = await startAttempt(session.token)
console.log(`[info] attempt=${attemptId} paper=${PAPER_ID}`)

const authState = {
  cookies: [],
  origins: [
    {
      origin: BASE,
      localStorage: [
        { name: 'sproutlearn.v3.auth.token', value: session.token },
        { name: 'sproutlearn.v3.auth.user', value: JSON.stringify(session.user) },
      ],
    },
  ],
}

{
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    storageState: authState,
  })
  const page = await context.newPage()
  await page.goto(`${BASE}/student/attempts/${attemptId}`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.option', { timeout: 15000 })
  await page.waitForTimeout(500)
  await shot(page, 'attempt-light-1440.png')

  const optionStyle = await page.evaluate(() => {
    const el = document.querySelector('.option')
    if (!el) return null
    const s = getComputedStyle(el)
    return { radius: s.borderRadius, border: s.borderTopWidth, bg: s.backgroundColor }
  })
  check('选项取消卡片外框', optionStyle?.radius === '0px' && optionStyle?.border === '1px', JSON.stringify(optionStyle))

  // 单选：确保产生一次真实变更（重复运行时答案可能已保存过）
  const radios = page.locator('.att-qbody--desktop .option__native')
  const firstChecked = await radios.nth(0).isChecked()
  await page.locator('.att-qbody--desktop .option').nth(firstChecked ? 1 : 0).click()
  await page.waitForTimeout(1200)
  await shot(page, 'attempt-selected.png')
  const selectedBg = await page.evaluate(() => {
    const el = document.querySelector('.option.is-selected')
    return el ? getComputedStyle(el).backgroundColor : 'none'
  })
  check('选中行使用石墨底', selectedBg === 'rgb(21, 27, 23)', selectedBg)
  check('保存状态回到已保存', await page.getByText('已保存').first().isVisible())

  // 多选：按当前真实作答状态补齐到「选 2 项」，重复运行也不会互相干扰
  await page.locator('.answer-sheet__grid .cell').nth(1).click()
  const boxes = page.locator('.att-qbody--desktop .option__native')
  for (let i = 0; i < 4; i += 1) {
    const want = i < 2
    const checked = await boxes.nth(i).isChecked()
    if (checked !== want) await page.locator('.att-qbody--desktop .option').nth(i).click()
  }
  await page.waitForTimeout(1000)
  const multiText = await page.locator('.att-qbody--desktop .q-count').innerText()
  check('多选显示已选数量', /已选\s*2\s*项/.test(multiText), multiText.replace(/\s+/g, ' '))
  await shot(page, 'attempt-multiselect.png')

  // 判断
  await page.locator('.answer-sheet__grid .cell').nth(2).click()
  await page.locator('.option').first().click()
  await page.waitForTimeout(1000)
  await shot(page, 'attempt-judge.png')

  // 填空
  await page.locator('.answer-sheet__grid .cell').nth(3).click()
  await page.locator('.att-qbody--desktop textarea').fill('Access Control')
  await page.waitForTimeout(1000)
  await shot(page, 'attempt-blank.png')

  // 保存失败：拦截真实 PUT 请求，验证失败态与重试
  await page.route('**/answers/**', (route) => route.abort())
  await page.locator('.answer-sheet__grid .cell').nth(4).click()
  const q5Options = page.locator('.att-qbody--desktop .option__native')
  let target = 0
  for (let i = 0; i < 4; i += 1) {
    if (!(await q5Options.nth(i).isChecked())) {
      target = i
      break
    }
  }
  await page.locator('.att-qbody--desktop .option').nth(target).click()
  await page.waitForTimeout(1600)
  const failed = await page.getByText('保存失败').first().isVisible()
  check('保存失败态出现', failed)
  await shot(page, 'attempt-save-failed.png')
  await page.unroute('**/answers/**')
  await page.getByRole('button', { name: '重试' }).click()
  await page.waitForTimeout(1500)
  check('重试后恢复已保存', await page.getByText('已保存').first().isVisible())

  // 提交确认（不真正提交，保留本次作答）
  await page.getByRole('button', { name: '提交试卷' }).first().click()
  await page.waitForTimeout(400)
  const dialogText = await page.getByRole('dialog').innerText()
  check('提交确认含未答数量', /未作答/.test(dialogText), dialogText.replace(/\s+/g, ' ').slice(0, 60))
  await shot(page, 'attempt-submit-confirm.png')
  await page.getByRole('button', { name: '取消' }).click()
  await page.waitForTimeout(300)

  // 深色
  await page.evaluate(() => localStorage.setItem('sprout.v3.theme', 'dark'))
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForSelector('.option', { timeout: 15000 })
  await page.waitForTimeout(600)
  await shot(page, 'attempt-dark-1440.png')
  await page.evaluate(() => localStorage.removeItem('sprout.v3.theme'))

  // 共享按钮 / 焦点抽验：非本轮页面（学生试卷列表）
  await page.goto(`${BASE}/student/papers`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await shot(page, 'shared-button-regression.png')

  await context.close()
}

/* ── 3. 手机答题页 + 答题卡抽屉焦点陷阱 ───────────────────── */
{
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    locale: 'zh-CN',
    storageState: authState,
  })
  const page = await context.newPage()
  await page.goto(`${BASE}/student/attempts/${attemptId}`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.att-slide', { timeout: 15000 })
  await page.waitForTimeout(600)
  await shot(page, 'attempt-mobile-390.png')

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  check('答题页 390 无横向溢出', overflow <= 0, `${overflow}px`)

  const trigger = page.getByRole('button', { name: /答题卡/ })
  await trigger.click()
  await page.waitForTimeout(500)
  await shot(page, 'attempt-mobile-sheet.png')

  const cellHeight = await page
    .locator('.att-drawer__panel .cell')
    .first()
    .evaluate((el) => el.getBoundingClientRect().height)
  check('题号触控目标 ≥ 44px', cellHeight >= 44, `${cellHeight}px`)

  for (let i = 0; i < 14; i += 1) await page.keyboard.press('Tab')
  const trapped = await page.evaluate(() => {
    const panel = document.querySelector('.att-drawer__panel')
    return Boolean(panel && panel.contains(document.activeElement))
  })
  check('抽屉 Tab 焦点被限制在面板内', trapped)

  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
  const closed = await page.locator('.att-drawer__panel').count()
  check('Escape 关闭答题卡', closed === 0)
  const restored = await page.evaluate(() =>
    Boolean(document.activeElement?.textContent?.includes('答题卡')),
  )
  check('关闭后焦点回到答题卡按钮', restored)

  await context.close()
}

await browser.close()
console.log(failures === 0 ? '[done] all browser checks passed' : `[done] ${failures} check(s) failed`)
process.exit(failures === 0 ? 0 : 1)
