// 角色与文档状态等业务枚举：与后端 §7 字段保持同一组字面量。
export type Role = 'teacher' | 'student'

// 文档状态由后端 knowledge_doc.status 定义，前端只做展示映射。
export const DocStatus = {
  Pending: 0,
  Processing: 1,
  Ready: 2,
  Failed: 3,
} as const

export type DocStatusValue = (typeof DocStatus)[keyof typeof DocStatus]

export type ToastKind = 'success' | 'error' | 'info' | 'warning'

// 学生绑定 QQ 后，个人中心的展示状态。
export type QqBindState = 'unbound' | 'bound' | 'pending'

export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

export interface TableColumn {
  key: string
  title: string
  width?: string
  align?: 'left' | 'center' | 'right'
  className?: string
}
