import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { SESSION_EXPIRED_EVENT } from './api/client'
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
  ui.toast(detail?.message ?? '登录已过期，请重新登录', 'error')
  const current = router.currentRoute.value
  if (current.meta.role !== 'public') {
    void router.replace({ path: '/login', query: { redirect: current.fullPath } })
  }
})

app.mount('#app')
