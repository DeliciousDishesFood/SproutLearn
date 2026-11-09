// 应用入口：装配 Pinia、Router、全局样式与会话失效监听。
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { SESSION_EXPIRED_EVENT } from '@/utils/constants'
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/utilities.css'

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
app.use(router)

const auth = useAuthStore(pinia)
if (auth.token && !auth.user) {
  auth.clearSession()
}

// 40101 / 40102 由 api/client 统一广播；这里只做一次清理与跳转。
window.addEventListener(SESSION_EXPIRED_EVENT, (event: Event) => {
  const detail = (event as CustomEvent<{ message?: string }>).detail
  const currentAuth = useAuthStore(pinia)
  const wasAuthenticated = currentAuth.isAuthenticated
  currentAuth.clearSession()

  const ui = useUiStore(pinia)
  if (wasAuthenticated) {
    ui.warning(detail?.message || '登录已过期，请重新登录')
  }

  if (router.currentRoute.value.path !== '/login') {
    router.replace({
      path: '/login',
      query: { expired: '1', redirect: router.currentRoute.value.fullPath },
    })
  }
})

app.mount('#app')
