/**
 * v1.5 演示视觉与「问问小芽」浏览器验收（自包含夹具）。
 *
 * 运行：node scripts/ui-v1.5-polish-check.mjs
 * 前置：本机可执行 npm / Edge；playwright-core 借用同机 Demo 工程（可用 PLAYWRIGHT_CORE 覆盖）。
 * 说明：夹具只服务本任务的 UI 状态断言，不代表真实 MySQL 全流程或真实 AI 内容质量。
 */
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { mkdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const { chromium } = require(
  process.env.PLAYWRIGHT_CORE || 'E:/temporary-work/ui-v3-templates/node_modules/playwright-core',
)

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const OUT = join(ROOT, 'shots', 'v1.5-demo-polish')
const FIXTURE_PORT = 8012
const VITE_PORT = 5176
const BASE = `http://127.0.0.1:${VITE_PORT}`
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const THEME_KEY = 'sprout.v3.theme'
const TOKEN_KEY = 'sproutlearn.v3.auth.token'
const USER_KEY = 'sproutlearn.v3.auth.user'
const NOW = new Date().toISOString()

let failures = 0
function check(label, ok, detail = '') {
  if (!ok) failures += 1
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? ` · ${detail}` : ''}`)
}

async function shot(page, name) {
  await page.screenshot({ path: join(OUT, name) })
  console.log(`[shot] ${name}`)
}

/* ── 夹具数据 ──────────────────────────────────────────────── */

const student = {
  id: 11,
  role: 'student',
  name: '林小满',
  student_no: '20260101',
  class_id: 501,
  class_name: '高二（3）班',
  class_code: 'C26A79',
  level: 7,
  xp_total: 3480,
  qq_bound: false,
  status: 1,
}
const teacher = { id: 2, role: 'teacher', name: '陈老师', account: 'teacher@school.edu.cn' }

const paper = {
  id: 601,
  class_id: 501,
  title: '函数与导数 · 课堂练习',
  mode: 'fixed',
  kind: 'practice',
  blank_mode: 'smart',
  status: 'published',
  question_count: 4,
  total_score: 40,
  duration_minutes: 0,
  published_at: '2026-11-10T09:00:00+08:00',
  due_at: '2026-11-20T23:59:00+08:00',
  created_at: '2026-11-09T09:00:00+08:00',
}

const questions = [
  {
    id: 201,
    seq: 1,
    score: 10,
    type: 'single',
    stem: '函数 f(x)=x² 在 x=1 处的导数值是？',
    options: [
      { key: 'A', text: '0' },
      { key: 'B', text: '1' },
      { key: 'C', text: '2' },
      { key: 'D', text: '4' },
    ],
    knowledge_tag: '导数',
    difficulty: 'easy',
  },
  {
    id: 202,
    seq: 2,
    score: 10,
    type: 'single',
    stem: '曲线 y=x³ 在点 (1,1) 处的切线斜率为？',
    options: [
      { key: 'A', text: '1' },
      { key: 'B', text: '2' },
      { key: 'C', text: '3' },
      { key: 'D', text: '4' },
    ],
    knowledge_tag: '导数的几何意义',
    difficulty: 'medium',
  },
  {
    id: 203,
    seq: 3,
    score: 10,
    type: 'blank',
    stem: '已知 f(x)=x²+3x，求 f′(x)。',
    options: null,
    knowledge_tag: '求导法则',
    difficulty: 'medium',
  },
  {
    id: 204,
    seq: 4,
    score: 10,
    type: 'multiple',
    stem: '下列函数在 x>0 上单调递增的有？',
    options: [
      { key: 'A', text: 'y=x²' },
      { key: 'B', text: 'y=1/x' },
      { key: 'C', text: 'y=ln x' },
      { key: 'D', text: 'y=-x' },
    ],
    knowledge_tag: '函数单调性',
    difficulty: 'hard',
  },
]

const attempt = {
  id: 9001,
  paper_id: paper.id,
  class_id: 501,
  student_id: 11,
  started_at: '2026-11-16T08:00:00+08:00',
  deadline_at: null,
  submitted_at: null,
  status: 'doing',
  total_score: 0,
  full_score: 40,
  needs_review: false,
  late: false,
  paper,
  questions,
  answers: { '201': 'B' },
  server_now: NOW,
  remaining_seconds: null,
}

const resultAnswers = [
  {
    id: 1,
    answer_record_id: 101,
    question_id: 201,
    seq: 1,
    type: 'single',
    stem: questions[0].stem,
    options: questions[0].options,
    standard_answer: 'B',
    analysis: '由幂函数求导法则，(x²)′ = 2x，代入 x=1 得 2。',
    knowledge_tag: '导数',
    difficulty: 'easy',
    full_score: 10,
    raw_answer: 'B',
    score: 10,
    is_correct: true,
    engine: 'rule',
    confidence: 1,
    needs_review: false,
    detail: {},
  },
  {
    id: 2,
    answer_record_id: 102,
    question_id: 202,
    seq: 2,
    type: 'single',
    stem: questions[1].stem,
    options: questions[1].options,
    standard_answer: 'C',
    analysis: 'y=x³ 的导数为 3x²，在 x=1 处为 3。',
    knowledge_tag: '导数的几何意义',
    difficulty: 'medium',
    full_score: 10,
    raw_answer: 'B',
    score: 3,
    is_correct: false,
    engine: 'rule',
    confidence: 1,
    needs_review: false,
    detail: {},
  },
  {
    id: 3,
    answer_record_id: 103,
    question_id: 204,
    seq: 3,
    type: 'multiple',
    stem: questions[3].stem,
    options: questions[3].options,
    standard_answer: ['A', 'C'],
    analysis: 'x² 与 ln x 在 x>0 上单调递增。',
    knowledge_tag: '函数单调性',
    difficulty: 'hard',
    full_score: 10,
    raw_answer: ['A'],
    score: 0,
    is_correct: false,
    engine: 'rule',
    confidence: 1,
    needs_review: false,
    detail: {},
  },
  {
    id: 4,
    answer_record_id: 104,
    question_id: 203,
    seq: 4,
    type: 'blank',
    stem: questions[2].stem,
    options: null,
    standard_answer: '2x+3',
    analysis: '逐项求导：x² 的导数为 2x，3x 的导数为 3。',
    knowledge_tag: '求导法则',
    difficulty: 'medium',
    full_score: 10,
    raw_answer: '2x+3 左右',
    score: 6,
    is_correct: false,
    engine: 'semantic',
    confidence: 0.62,
    needs_review: true,
    detail: {},
  },
]

const result = {
  attempt: {
    id: 9001,
    paper_id: paper.id,
    class_id: 501,
    student_id: 11,
    started_at: attempt.started_at,
    deadline_at: null,
    submitted_at: '2026-11-16T08:42:00+08:00',
    status: 'graded',
    total_score: 27,
    full_score: 40,
    late: true,
    needs_review: true,
  },
  paper,
  answers: resultAnswers,
  reviews: [
    {
      id: 1,
      answer_record_id: 104,
      old_score: 6,
      new_score: 7,
      comment: '步骤基本正确，表述可再精确。',
      created_at: '2026-11-16T10:00:00+08:00',
    },
  ],
  grading_ms: 820,
}

const level = {
  level: 7,
  title: '抽枝',
  min_xp: 3000,
  next_level: 8,
  next_min_xp: 4000,
  xp_to_next: 520,
  progress_pct: 48,
}

const activity = Array.from({ length: 12 }, (_, index) => {
  const date = new Date(Date.now() - (11 - index) * 86400000).toISOString().slice(0, 10)
  return { date, answers: (index * 3) % 7, xp: (index * 5) % 20 }
})

const studentWorkbench = {
  student: {
    id: 11,
    name: '林小满',
    class_id: 501,
    xp_total: 3480,
    streak_days: 12,
  },
  level,
  xp_total: 3480,
  streak_days: 12,
  today_xp: 120,
  today: { login_xp: 5, practice_xp: 80, streak_xp: 10, submission_xp: 25, total_xp: 120, cap: 200 },
  pending: [paper],
  pending_papers: [paper],
  recent: [
    {
      attempt_id: 9001,
      paper_id: paper.id,
      paper_title: paper.title,
      kind: 'practice',
      total_score: 27,
      full_score: 40,
      status: 'graded',
      needs_review: true,
      submitted_at: '2026-11-16T08:42:00+08:00',
    },
  ],
  recent_scores: [],
  activity,
}

const growth = {
  xp_total: 3480,
  level,
  ledger: [
    {
      id: 1,
      source: 'practice',
      ref_type: 'attempt',
      ref_id: 9001,
      xp: 12,
      note: '函数与导数 · 课堂练习',
      created_at: '2026-11-16T08:42:00+08:00',
    },
    {
      id: 2,
      source: 'login',
      xp: 5,
      note: '每日登录',
      created_at: '2026-11-16T08:00:00+08:00',
    },
    {
      id: 3,
      source: 'review',
      xp: 8,
      note: '老师复核加分',
      created_at: '2026-11-15T20:00:00+08:00',
    },
  ],
  activity,
  heatmap: activity,
}

const classItem = {
  id: 501,
  class_code: 'C26A79',
  class_name: '高二（3）班',
  course_name: '数学',
  student_count: 3,
  doc_count: 4,
  status: 1,
  invite_code: '8J4N6W',
  created_at: '2026-09-01T09:00:00+08:00',
}

const studentList = [
  {
    id: 11,
    student_no: '20260101',
    name: '林小满',
    level: 7,
    xp_total: 3480,
    status: 1,
    qq_bound: true,
    created_at: '2026-09-02T09:00:00+08:00',
    last_login_at: '2026-11-16T08:00:00+08:00',
  },
  {
    id: 12,
    student_no: '20260102',
    name: '陈知遥',
    level: 6,
    xp_total: 3010,
    status: 1,
    qq_bound: false,
    created_at: '2026-09-02T09:05:00+08:00',
    last_login_at: '2026-11-16T07:40:00+08:00',
  },
  {
    id: 13,
    student_no: '20260103',
    name: '赵一鸣',
    level: 5,
    xp_total: 2600,
    status: 0,
    qq_bound: false,
    created_at: '2026-09-02T09:10:00+08:00',
    last_login_at: '2026-11-10T19:20:00+08:00',
  },
]

const examPaper = {
  ...paper,
  id: 701,
  title: '期中模拟 · 导数专题',
  kind: 'exam',
  status: 'published',
  question_count: 12,
  total_score: 100,
  published_at: '2026-11-12T09:00:00+08:00',
}

const teacherWorkbench = {
  class_id: 501,
  pending_review: 3,
  today_submissions: 18,
  active_students: 26,
  average_score: 78.4,
  average_score_rate: 0.784,
  recent_papers: [paper, examPaper],
  top_students: [],
  top5: [],
  activity,
}

const explainCalls = new Map()

function envelope(data, code = 0, message = 'ok') {
  return JSON.stringify({ code, message, data, request_id: 'fixture', timestamp: NOW })
}

function send(res, data, code = 0, message = 'ok') {
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(envelope(data, code, message))
}

function pageOf(list, query) {
  const current = Number(query.get('page') ?? 1)
  const size = Number(query.get('page_size') ?? 10)
  const start = (current - 1) * size
  return { list: list.slice(start, start + size), total: list.length, page: current, page_size: size }
}

const apiServer = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1')
  const path = url.pathname
  const query = url.searchParams
  let raw = ''
  for await (const chunk of req) raw += chunk
  let payload = {}
  try {
    payload = raw ? JSON.parse(raw) : {}
  } catch {
    payload = {}
  }

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }
  if (path === '/health') {
    send(res, { status: 'ok' })
    return
  }

  if (path === '/api/v1/auth/login' && req.method === 'POST') {
    if (payload.role === 'student') {
      send(res, { token: 'fixture-student-token', user: student })
    } else {
      send(res, { token: 'fixture-teacher-token', user: teacher })
    }
    return
  }
  if (path === '/api/v1/auth/me') {
    const auth = req.headers.authorization ?? ''
    send(res, auth.includes('teacher') ? teacher : student)
    return
  }
  if (path === '/api/v1/auth/logout') {
    send(res, null)
    return
  }

  if (path === '/api/v1/attempts/9001' && req.method === 'GET') {
    send(res, { attempt, paper, questions, answers: attempt.answers, server_now: NOW, remaining_seconds: null })
    return
  }
  if (path === '/api/v1/attempts/9001/result') {
    send(res, result)
    return
  }
  if (path === '/api/v1/attempts/9001/answers' || path.startsWith('/api/v1/attempts/9001/answers/')) {
    send(res, { attempt_id: 9001, question_id: Number(path.split('/').pop()), answer: payload.answer, updated_at: NOW })
    return
  }
  if (path === '/api/v1/attempts/9001/ask' && req.method === 'POST') {
    const message = String(payload.message ?? '')
    const sources = message.includes('来源')
      ? [{ doc_id: 1, doc_name: '人教版数学选修2-2.pdf' }]
      : []
    send(res, {
      answer: '这题考查导数的几何意义。先求导函数，再把切点横坐标代入，得到切线斜率。',
      sources,
    })
    return
  }
  if (path.startsWith('/api/v1/questions/') && path.endsWith('/explain')) {
    const questionId = Number(path.split('/')[4])
    const call = (explainCalls.get(questionId) ?? 0) + 1
    explainCalls.set(questionId, call)
    if (questionId === 203 && call === 1) {
      send(res, null, 50301, '讲评服务暂时不可用，请稍后重试')
      return
    }
    if (questionId === 203) {
      send(res, {
        engine: 'template',
        degraded: true,
        content: '模板讲评：先对每一项分别求导，再把结果相加。',
      })
      return
    }
    send(res, {
      engine: 'llm',
      degraded: false,
      content:
        '**考点**：导数的几何意义。\n\n1. 先求导函数；\n2. 代入切点横坐标；\n3. 得到斜率。\n\n注意不要把函数值当成斜率。',
    })
    return
  }

  if (path === '/api/v1/me/workbench') {
    send(res, studentWorkbench)
    return
  }
  if (path === '/api/v1/me/activity') {
    send(res, { weeks: Number(query.get('weeks') ?? 52), items: activity, activity })
    return
  }
  if (path === '/api/v1/me/growth') {
    send(res, growth)
    return
  }

  if (path === '/api/v1/classes' && req.method === 'GET') {
    send(res, pageOf([classItem], query))
    return
  }
  if (path === '/api/v1/classes/501' && req.method === 'GET') {
    send(res, classItem)
    return
  }
  if (path === '/api/v1/classes/501/invite-code') {
    send(res, {
      invite_code: '8J4N6W',
      status: 1,
      created_at: '2026-09-01T09:00:00+08:00',
      expires_at: null,
    })
    return
  }
  if (path === '/api/v1/classes/501/students') {
    send(res, pageOf(studentList, query))
    return
  }
  if (path === '/api/v1/classes/501/papers') {
    send(res, pageOf([examPaper, paper], query))
    return
  }
  if (path === '/api/v1/classes/501/workbench') {
    send(res, teacherWorkbench)
    return
  }
  if (path === '/api/v1/classes/501/activity') {
    send(res, { weeks: 52, items: activity, activity })
    return
  }
  if (path === '/api/v1/papers/701/attempts') {
    send(
      res,
      pageOf(
        [
          {
            id: 1,
            attempt_id: 9001,
            student_id: 11,
            student_no: '20260101',
            student_name: '林小满',
            status: 'graded',
            total_score: 27,
            full_score: 40,
            needs_review_count: 1,
            started_at: '2026-11-16T08:00:00+08:00',
            submitted_at: '2026-11-16T08:42:00+08:00',
          },
        ],
        query,
      ),
    )
    return
  }

  if (path === '/api/v1/notifications/unread-count') {
    send(res, { count: 2 })
    return
  }
  if (path === '/api/v1/quotes/random') {
    send(res, { text: '把复杂讲简单，把简单讲深刻。', from: '青芽教学手记', source: 'local' })
    return
  }

  send(res, null)
})

/* ── 启动夹具与前端 ─────────────────────────────────────────── */

async function waitFor(url, timeout = 60000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    try {
      const res = await fetch(url)
      if (res.ok) return
    } catch {
      // 继续等待
    }
    await new Promise((resolve) => setTimeout(resolve, 400))
  }
  throw new Error(`等待超时：${url}`)
}

await mkdir(OUT, { recursive: true })
await new Promise((resolve) => apiServer.listen(FIXTURE_PORT, '127.0.0.1', resolve))

const vite = spawn(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'dev', '--', '--port', String(VITE_PORT)], {
  cwd: ROOT,
  env: { ...process.env, VITE_API_TARGET: `http://127.0.0.1:${FIXTURE_PORT}` },
  shell: process.platform === 'win32',
  stdio: 'ignore',
})

let browser
try {
  await waitFor(`${BASE}/login`)
  browser = await chromium.launch({ executablePath: EDGE, headless: true })

  const storage = (user, token, theme) => ({
    cookies: [],
    origins: [
      {
        origin: BASE,
        localStorage: [
          { name: TOKEN_KEY, value: token },
          { name: USER_KEY, value: JSON.stringify(user) },
          ...(theme ? [{ name: THEME_KEY, value: theme }] : []),
        ],
      },
    ],
  })

  const studentContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    storageState: storage(student, 'fixture-student-token'),
  })
  const page = await studentContext.newPage()
  await page.goto(`${BASE}/student/attempts/9001`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.att-qbody--desktop .q-stem', { timeout: 20000 })

  async function selectStem() {
    await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll('.q-stem')).find(
        (node) => node instanceof HTMLElement && node.offsetParent !== null,
      )
      if (!el) return
      const range = document.createRange()
      range.selectNodeContents(el)
      const selection = window.getSelection()
      selection?.removeAllRanges()
      selection?.addRange(range)
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
    })
    await page.waitForSelector('[data-ask-trigger]', { timeout: 5000 })
    await page.locator('[data-ask-trigger]').click()
    await page.waitForSelector('.ask-panel')
    await page.waitForTimeout(300)
  }

  /* ── 1. 问问小芽：桌面 ───────────────────────────────────── */
  await selectStem()
  await shot(page, 'ask-empty-1440.png')

  const panelBox = await page.locator('.ask-panel').boundingBox()
  check('小芽桌面宽度 380–400px', panelBox && panelBox.width >= 380 && panelBox.width <= 400, `${panelBox?.width}px`)
  const panelStyle = await page.locator('.ask-panel').evaluate((el) => {
    const style = getComputedStyle(el)
    return { radius: style.borderTopLeftRadius, bg: style.backgroundColor }
  })
  check('小芽面板 22–24px 圆角', panelStyle.radius === '22px', panelStyle.radius)
  const closeBox = await page.getByRole('button', { name: '关闭问问小芽' }).boundingBox()
  check('关闭按钮命中区 ≥44px', closeBox && closeBox.width >= 44 && closeBox.height >= 44, `${closeBox?.width}×${closeBox?.height}`)

  await page.locator('.ask-quick__chip').first().click()
  const filled = await page.locator('.ask-compose__input').inputValue()
  check('快捷提问只填入不发送', filled.length > 0 && (await page.locator('.ask-msg').count()) === 0, filled)

  await page.getByRole('button', { name: '发送' }).click()
  await page.waitForSelector('.ask-msg--bot')
  await page.waitForTimeout(250)
  const userBubble = await page.locator('.ask-msg--user').first().evaluate((el) => getComputedStyle(el).backgroundColor)
  check('用户气泡使用石墨底', userBubble === 'rgb(21, 27, 23)', userBubble)
  check('无 sources 时不显示来源', (await page.locator('.ask-src').count()) === 0)
  await shot(page, 'ask-conversation-1440.png')

  await page.locator('.ask-compose__input').fill('请给出这个结论的讲来源')
  await page.getByRole('button', { name: '发送' }).click()
  await page.waitForSelector('.ask-src')
  check('sources 真实返回时展示文档标签', (await page.locator('.ask-src__tag').first().innerText()).includes('pdf'))
  await shot(page, 'ask-sources-1440.png')

  const userBeforeError = await page.locator('.ask-msg--user').count()
  await page.route('**/api/v1/attempts/9001/ask', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: envelope(null, 50301, '小芽暂时不可用，请稍后重试'),
    }),
  )
  await page.locator('.ask-compose__input').fill('这条消息会失败')
  await page.getByRole('button', { name: '发送' }).click()
  await page.waitForSelector('.ask-error')
  check('503 内联错误可见', await page.locator('.ask-error').isVisible())
  await shot(page, 'ask-error-retry-1440.png')
  await page.unroute('**/api/v1/attempts/9001/ask')
  const botBeforeRetry = await page.locator('.ask-msg--bot').count()
  await page.getByRole('button', { name: '重试' }).click()
  await page.waitForFunction(
    (count) => document.querySelectorAll('.ask-msg--bot').length > count,
    botBeforeRetry,
    { timeout: 8000 },
  )
  const userAfterRetry = await page.locator('.ask-msg--user').count()
  check('重试不重复插入用户消息', userAfterRetry === userBeforeError + 1, `${userBeforeError}→${userAfterRetry}`)

  await page.keyboard.press('Escape')
  await page.waitForSelector('.ask-panel', { state: 'detached' })
  const restored = await page.evaluate(() => document.activeElement?.classList.contains('att-stage'))
  check('关闭后焦点回到答题阅读区', restored)
  await page.keyboard.press('Escape')

  /* ── 2. 问问小芽：深色 ───────────────────────────────────── */
  await page.evaluate((key) => localStorage.setItem(key, 'dark'), THEME_KEY)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.att-qbody--desktop .q-stem', { timeout: 20000 })
  await selectStem()
  await page.locator('.ask-quick__chip').first().click()
  await page.getByRole('button', { name: '发送' }).click()
  await page.waitForSelector('.ask-msg--bot')
  await page.waitForTimeout(250)
  await shot(page, 'ask-dark-1440.png')
  await page.keyboard.press('Escape')
  await page.evaluate((key) => localStorage.removeItem(key), THEME_KEY)

  /* ── 3. 结果页 ───────────────────────────────────────────── */
  await page.goto(`${BASE}/student/attempts/9001/result`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.result-hero', { timeout: 20000 })
  await shot(page, 'result-1440.png')

  const heroBg = await page.locator('.result-hero').evaluate((el) => getComputedStyle(el).backgroundColor)
  check('成绩 Hero 为石墨深底', heroBg === 'rgb(14, 18, 16)', heroBg)
  const scoreColor = await page.locator('.result-hero__score').evaluate((el) => getComputedStyle(el).color)
  check('大分数使用青柠', scoreColor === 'rgb(154, 230, 0)', scoreColor)

  await page.getByRole('button', { name: /错题/ }).click()
  await page.waitForTimeout(200)
  const wrongItems = await page.locator('.answer-item').count()
  check('错题筛选只显示错题', wrongItems === 2, `${wrongItems} 题`)
  await shot(page, 'result-filter-wrong-1440.png')

  await page.getByRole('button', { name: /全部/ }).click()
  const wrongFirst = page.locator('.answer-item').filter({ hasText: '错误' }).first()
  await wrongFirst.getByRole('button', { name: '看讲评' }).click()
  await page.waitForSelector('.explain-section__body')
  await page.waitForFunction(() => !document.querySelector('.modal .loading-line'), null, {
    timeout: 10000,
  })
  const modalText = await page.getByRole('dialog').innerText()
  check('讲评弹层区分官方解析与 AI 讲评', modalText.includes('官方解析') && modalText.includes('AI 讲评'))
  check('AI 讲评正文已真实渲染', modalText.includes('先求导函数'))
  check('AI 返回的 ** 已被清理', !modalText.includes('**'))
  check('AI 讲评附边界说明', modalText.includes('仅供学习参考'))
  await shot(page, 'result-explain-1440.png')
  await page.locator('.modal__foot').getByRole('button', { name: '关闭' }).click()
  await page.waitForTimeout(200)

  const pendingItem = page.locator('.answer-item').filter({ hasText: '待老师复核' }).first()
  await pendingItem.getByRole('button', { name: '看讲评' }).click()
  await page.waitForSelector('.notice--danger')
  check('讲评 503 显示错误出口', await page.getByRole('button', { name: '重新生成' }).isVisible())
  await page.getByRole('button', { name: '重新生成' }).click()
  await page.getByText('模板讲评').waitFor({ timeout: 10000 })
  const degradedText = await page.getByRole('dialog').innerText()
  check('降级状态按真实字段显示', degradedText.includes('模板讲评') || degradedText.includes('降级内容'))
  await page.locator('.modal__foot').getByRole('button', { name: '关闭' }).click()
  await page.waitForTimeout(200)

  await page.evaluate((key) => localStorage.setItem(key, 'dark'), THEME_KEY)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.result-hero', { timeout: 20000 })
  await shot(page, 'result-dark-1440.png')
  await page.evaluate((key) => localStorage.removeItem(key), THEME_KEY)

  /* ── 4. 学生首页 1440 ────────────────────────────────────── */
  await page.goto(`${BASE}/student`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.stat--focus', { timeout: 20000 })
  const focusBg = await page.locator('.stat--focus').evaluate((el) => getComputedStyle(el).backgroundColor)
  check('当前等级卡为石墨焦点', focusBg === 'rgb(14, 18, 16)', focusBg)
  const plainBg = await page.locator('.stat').nth(1).evaluate((el) => getComputedStyle(el).backgroundColor)
  check('其余统计卡保持浅色', plainBg === 'rgb(255, 255, 255)', plainBg)
  await shot(page, 'home-1440.png')

  await studentContext.close()

  /* ── 5. 手机：小芽、结果、首页 ───────────────────────────── */
  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    locale: 'zh-CN',
    storageState: storage(student, 'fixture-student-token'),
  })
  const mobile = await mobileContext.newPage()

  async function selectStemMobile() {
    await mobile.evaluate(() => {
      const el = Array.from(document.querySelectorAll('.q-stem')).find(
        (node) => node instanceof HTMLElement && node.offsetParent !== null,
      )
      if (!el) return
      const range = document.createRange()
      range.selectNodeContents(el)
      const selection = window.getSelection()
      selection?.removeAllRanges()
      selection?.addRange(range)
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
    })
    await mobile.waitForSelector('[data-ask-trigger]', { timeout: 5000 })
    await mobile.locator('[data-ask-trigger]').click()
    await mobile.waitForSelector('.ask-panel')
    await mobile.waitForTimeout(300)
  }

  await mobile.goto(`${BASE}/student/attempts/9001`, { waitUntil: 'domcontentloaded' })
  await mobile.waitForSelector('.att-qbody--swipe .q-stem', { timeout: 20000 })
  await selectStemMobile()
  const mobilePanel = await mobile.locator('.ask-panel').evaluate((el) => {
    const style = getComputedStyle(el)
    const box = el.getBoundingClientRect()
    return {
      radius: style.borderTopLeftRadius,
      bottom: box.bottom,
      height: box.height,
      viewport: window.innerHeight,
    }
  })
  check('390 小芽为底部抽屉', mobilePanel.radius === '24px' && Math.abs(mobilePanel.bottom - mobilePanel.viewport) < 2, JSON.stringify(mobilePanel))
  const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  check('小芽打开后页面无横向溢出', mobileOverflow <= 0, `${mobileOverflow}px`)
  await shot(mobile, 'ask-mobile-390.png')

  await mobile.setViewportSize({ width: 390, height: 520 })
  await mobile.waitForTimeout(400)
  const inputVisible = await mobile.locator('.ask-compose__input').evaluate((el) => {
    const box = el.getBoundingClientRect()
    return { bottom: box.bottom, viewport: window.innerHeight }
  })
  check('键盘占用高度时输入区仍可见', inputVisible.bottom <= inputVisible.viewport, JSON.stringify(inputVisible))
  await shot(mobile, 'ask-mobile-keyboard-390.png')
  await mobile.keyboard.press('Escape')
  await mobile.setViewportSize({ width: 390, height: 844 })

  await mobile.goto(`${BASE}/student/attempts/9001/result`, { waitUntil: 'domcontentloaded' })
  await mobile.waitForSelector('.result-hero', { timeout: 20000 })
  await mobile.waitForTimeout(200)
  const resultOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  check('结果页 390 无横向溢出', resultOverflow <= 0, `${resultOverflow}px`)
  await shot(mobile, 'result-mobile-390.png')

  await mobile.goto(`${BASE}/student`, { waitUntil: 'domcontentloaded' })
  await mobile.waitForSelector('.stat--focus', { timeout: 20000 })
  const statColumns = await mobile.locator('.stats').evaluate((el) => {
    return getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length
  })
  check('手机统计区保持 2×2', statColumns === 2, `${statColumns} 列`)
  const homeOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  check('学生首页 390 无横向溢出', homeOverflow <= 0, `${homeOverflow}px`)
  await shot(mobile, 'home-390.png')
  await mobileContext.close()

  /* ── 6. 教师：工作台、学生表、设置 ───────────────────────── */
  const teacherContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
    storageState: storage(teacher, 'fixture-teacher-token'),
  })
  const teacherPage = await teacherContext.newPage()
  await teacherPage.goto(`${BASE}/teacher`, { waitUntil: 'domcontentloaded' })
  await teacherPage.waitForSelector('.dash-task', { timeout: 20000 })
  check('工作台待复核任务条显示真实数量', (await teacherPage.locator('.dash-task').innerText()).includes('3'))
  await shot(teacherPage, 'dashboard-1440.png')

  await teacherPage.goto(`${BASE}/teacher/settings`, { waitUntil: 'domcontentloaded' })
  await teacherPage.waitForSelector('.settings-page', { timeout: 20000 })
  const settingsLayout = await teacherPage.locator('.settings-page').evaluate((el) => {
    const style = getComputedStyle(el)
    const box = el.getBoundingClientRect()
    const main = el.closest('.main')?.getBoundingClientRect()
    return {
      maxWidth: style.maxWidth,
      left: box.left - (main?.left ?? 0),
      right: (main?.right ?? window.innerWidth) - box.right,
    }
  })
  check('账号设置限宽居中', settingsLayout.maxWidth === '920px' && Math.abs(settingsLayout.left - settingsLayout.right) < 2, JSON.stringify(settingsLayout))
  await shot(teacherPage, 'settings-1440.png')
  await teacherContext.close()

  const tableContext = await browser.newContext({
    viewport: { width: 375, height: 812 },
    deviceScaleFactor: 2,
    locale: 'zh-CN',
    storageState: storage(teacher, 'fixture-teacher-token'),
  })
  const tablePage = await tableContext.newPage()
  await tablePage.goto(`${BASE}/teacher/classes/501`, { waitUntil: 'domcontentloaded' })
  await tablePage.waitForSelector('.class-tabs, [role="tab"]', { timeout: 20000 })
  const studentsTab = tablePage.getByRole('tab', { name: /学生/ }).first()
  if (await studentsTab.count()) await studentsTab.click()
  await tablePage.waitForSelector('.student-table', { timeout: 20000 })
  await tablePage.waitForTimeout(300)

  const tableMetrics = await tablePage.evaluate(() => {
    const table = document.querySelector('.student-table')
    const nameCell = document.querySelector('.student-table__name')
    const wrap = document.querySelector('.table-wrap--students')
    return {
      minWidth: table ? getComputedStyle(table).minWidth : '',
      nameWrap: nameCell ? getComputedStyle(nameCell).whiteSpace : '',
      wrapScroll: wrap ? wrap.scrollWidth : 0,
      wrapClient: wrap ? wrap.clientWidth : 0,
      pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
    }
  })
  check('学生表 min-width ≥720px', parseInt(tableMetrics.minWidth, 10) >= 720, tableMetrics.minWidth)
  check('姓名列不换行不竖排', tableMetrics.nameWrap === 'nowrap', tableMetrics.nameWrap)
  check('学生表在容器内局部横滚', tableMetrics.wrapScroll > tableMetrics.wrapClient, `${tableMetrics.wrapScroll}/${tableMetrics.wrapClient}`)
  check('375 学生页无整体横溢', tableMetrics.pageOverflow <= 0, `${tableMetrics.pageOverflow}px`)
  await shot(tablePage, 'students-table-375.png')
  await tableContext.close()
} finally {
  if (browser) await browser.close()
  await new Promise((resolve) => apiServer.close(resolve))
  if (process.platform === 'win32') {
    spawn('taskkill', ['/pid', String(vite.pid), '/T', '/F'], { stdio: 'ignore' })
  } else {
    vite.kill('SIGTERM')
  }
}

console.log(failures === 0 ? '[done] all v1.5 browser checks passed' : `[done] ${failures} check(s) failed`)
process.exit(failures === 0 ? 0 : 1)
