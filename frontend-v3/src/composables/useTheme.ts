import { ref } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'sprout.v3.theme'

/** 主题状态（模块级单例）：侧栏、移动端顶栏与登录页共用同一份。 */
const theme = ref<Theme>('light')
let initialized = false
let media: MediaQueryList | null = null

function systemTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function applyTheme(next: Theme): void {
  theme.value = next
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', next)
  }
}

function onSystemChange(): void {
  // 用户未手动选择时才跟随系统
  try {
    if (!localStorage.getItem(STORAGE_KEY)) applyTheme(systemTheme())
  } catch {
    applyTheme(systemTheme())
  }
}

function ensureInit(): void {
  if (initialized || typeof window === 'undefined') return
  initialized = true
  const current = document.documentElement.getAttribute('data-theme')
  applyTheme(current === 'dark' || current === 'light' ? current : systemTheme())
  media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', onSystemChange)
}

export function useTheme() {
  ensureInit()

  function toggle(): void {
    const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // localStorage 不可用时仅当前会话生效
    }
    applyTheme(next)
  }

  return { theme, toggle }
}
