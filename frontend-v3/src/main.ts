import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { SESSION_EXPIRED_EVENT } from './api/client'
import { PASSWORD_CHANGE_REQUIRED_EVENT } from './utils/constants'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'
import { useTheme } from './composables/useTheme'
import './design/tokens.css'
import './design/base.css'

useTheme()

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

const auth = useAuthStore(pinia)
const ui = useUiStore(pinia)

window.addEventListener(SESSION_EXPIRED_EVENT, (event) => {
  const detail = (event as CustomEvent<{ message?: string }>).detail
  auth.clear()
  // 会话失效同时清掉持久化班级 ID，避免切换后端后拿旧 ID 继续请求。
  ui.setCurrentClassId(null)
  ui.toast(detail?.message ?? '登录已过期，请重新登录', 'error')
  const current = router.currentRoute.value
  if (current.meta.role !== 'public') {
    void router.replace({ path: '/login', query: { redirect: current.fullPath } })
  }
})

// 40303：保留会话，只把用户送到强制改密页。
window.addEventListener(PASSWORD_CHANGE_REQUIRED_EVENT, () => {
  const current = router.currentRoute.value
  if (current.name === 'account-change-password') return
  void router.replace({ path: '/account/change-password', query: { forced: '1' } })
})

app.mount('#app')

/* 离屏骨架屏暂停：骨架屏只在视口内播放轻 opacity，减少无意义动画开销。 */
const skeletonObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      entry.target.classList.toggle('is-offscreen', !entry.isIntersecting)
    })
  },
  { rootMargin: '80px' },
)

const observeSkeletons = (root: ParentNode): void => {
  root.querySelectorAll('.skeleton').forEach((el) => skeletonObserver.observe(el))
}

observeSkeletons(document)
new MutationObserver((records) => {
  records.forEach((record) => {
    record.addedNodes.forEach((node) => {
      if (node instanceof HTMLElement) {
        if (node.classList.contains('skeleton')) skeletonObserver.observe(node)
        observeSkeletons(node)
      }
    })
  })
}).observe(document.body, { childList: true, subtree: true })
