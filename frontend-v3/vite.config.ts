import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 新前端独立端口 5174；/api 与 /health 反代本机后端。
// 生产默认 8000；本轮联调用 VITE_API_TARGET=http://127.0.0.1:8010 覆盖。
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/health': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'es2020',
  },
  preview: {
    host: '127.0.0.1',
    port: 4174,
  },
})
