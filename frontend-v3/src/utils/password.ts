// 统一密码规则（契约 §9.2）：8–32 位，且同时包含字母和数字。
export const PASSWORD_RULE_TEXT = '8–32 位，且同时包含字母和数字'
export const PASSWORD_RULE_ERROR = '密码需为 8–32 位，且同时包含字母和数字'

/** 返回统一错误文案；通过返回 null。前端只做提示，最终以后端校验为准。 */
export function validatePassword(value: string): string | null {
  if (value.length < 8 || value.length > 32) return PASSWORD_RULE_ERROR
  if (!/[A-Za-z]/.test(value) || !/[0-9]/.test(value)) return PASSWORD_RULE_ERROR
  return null
}
