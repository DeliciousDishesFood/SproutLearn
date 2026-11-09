// 路由实例：history 模式（生产 nginx try_files 回落 index.html）。
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from '@/router/routes'
import { setupGuards } from '@/router/guards'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

setupGuards(router)

export default router
