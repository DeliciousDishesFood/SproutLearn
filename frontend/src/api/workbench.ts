// 工作台与成长接口（M3.2）：学生/教师工作台、活跃热力图、成长汇总。
import { api } from '@/api/client'
import type {
  ActivitySummary,
  GrowthSummary,
  StudentWorkbench,
  TeacherWorkbench,
} from '@/api/types'

export const workbenchApi = {
  /** M3.2-01 学生工作台。 */
  student(): Promise<StudentWorkbench> {
    return api.get<StudentWorkbench>('/me/workbench', { skipGlobalError: true })
  },

  /** M3.2-02 教师工作台（跨班 40302）。 */
  teacher(classId: number): Promise<TeacherWorkbench> {
    return api.get<TeacherWorkbench>(`/classes/${classId}/workbench`, { skipGlobalError: true })
  },

  /** M3.2-03 学生近 N 周活跃。 */
  studentActivity(weeks = 12): Promise<ActivitySummary> {
    return api.get<ActivitySummary>('/me/activity', {
      params: { weeks },
      skipGlobalError: true,
    })
  },

  /** M3.2-04 班级近 N 周活跃。 */
  classActivity(classId: number, weeks = 12): Promise<ActivitySummary> {
    return api.get<ActivitySummary>(`/classes/${classId}/activity`, {
      params: { weeks },
      skipGlobalError: true,
    })
  },

  /** M3.2-05 学生成长：等级进度、经验流水与热力图。 */
  growth(): Promise<GrowthSummary> {
    return api.get<GrowthSummary>('/me/growth', { skipGlobalError: true })
  },
}
