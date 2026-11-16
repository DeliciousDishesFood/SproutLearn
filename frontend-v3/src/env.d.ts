/// <reference types="vite/client" />

// vite.config.ts 运行在 Node 侧；本工程不引入 @types/node，此处最小化声明 process.env。
declare const process: { env: Record<string, string | undefined> }

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}
