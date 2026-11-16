// 工作台 / 成长 / 金句接口（契约 §2.8）。
import { api } from './client'
import type {
  ActivitySummary,
  GrowthSummary,
  QuoteResult,
  StudentWorkbench,
  TeacherWorkbench,
  XpConfigResponse,
} from './contract'

export const workbenchApi = {
  student(): Promise<StudentWorkbench> {
    return api.get<StudentWorkbench>('/me/workbench', { skipGlobalError: true })
  },

  teacher(classId: number): Promise<TeacherWorkbench> {
    return api.get<TeacherWorkbench>(`/classes/${classId}/workbench`, { skipGlobalError: true })
  },

  studentActivity(weeks = 12): Promise<ActivitySummary> {
    return api.get<ActivitySummary>('/me/activity', {
      params: { weeks },
      skipGlobalError: true,
    })
  },

  classActivity(classId: number, weeks = 12): Promise<ActivitySummary> {
    return api.get<ActivitySummary>(`/classes/${classId}/activity`, {
      params: { weeks },
      skipGlobalError: true,
    })
  },

  growth(): Promise<GrowthSummary> {
    return api.get<GrowthSummary>('/me/growth', { skipGlobalError: true })
  },

  xpConfig(classId: number): Promise<XpConfigResponse> {
    return api.get<XpConfigResponse>(`/classes/${classId}/xp-config`, { skipGlobalError: true })
  },

  updateXpConfig(
    classId: number,
    items: Array<{ code: string; enabled: boolean }>,
  ): Promise<XpConfigResponse> {
    return api.patch<XpConfigResponse>(`/classes/${classId}/xp-config`, { items }, {
      skipGlobalError: true,
    })
  },

  quote(): Promise<QuoteResult> {
    return api.get<QuoteResult>('/quotes/random', { skipGlobalError: true })
  },
}
