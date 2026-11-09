// 班级与邀请码接口（API-05 ~ API-11）。
import { api } from '@/api/client'
import type {
  ClassCreatePayload,
  ClassCreateResult,
  ClassDetail,
  ClassListItem,
  ClassListQuery,
  InviteCodeInfo,
  JoinClassResult,
  Paged,
  ResetInviteCodeResult,
  StudentJoinPayload,
  StudentListItem,
  StudentListQuery,
} from '@/api/types'

export const classesApi = {
  create(payload: ClassCreatePayload): Promise<ClassCreateResult> {
    return api.post<ClassCreateResult>('/classes', payload, { skipGlobalError: true })
  },

  list(query: ClassListQuery = {}): Promise<Paged<ClassListItem>> {
    return api.get<Paged<ClassListItem>>('/classes', {
      params: { page: query.page ?? 1, page_size: query.page_size ?? 10, status: query.status },
    })
  },

  detail(classId: number): Promise<ClassDetail> {
    return api.get<ClassDetail>(`/classes/${classId}`)
  },

  inviteCode(classId: number): Promise<InviteCodeInfo> {
    return api.get<InviteCodeInfo>(`/classes/${classId}/invite-code`)
  },

  resetInviteCode(classId: number): Promise<ResetInviteCodeResult> {
    return api.post<ResetInviteCodeResult>(`/classes/${classId}/invite-code/reset`, undefined, {
      skipGlobalError: true,
    })
  },

  students(classId: number, query: StudentListQuery = {}): Promise<Paged<StudentListItem>> {
    return api.get<Paged<StudentListItem>>(`/classes/${classId}/students`, {
      params: {
        keyword: query.keyword || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 10,
      },
    })
  },

  join(payload: StudentJoinPayload): Promise<JoinClassResult> {
    return api.post<JoinClassResult>('/classes/join', payload, {
      skipGlobalError: true,
      skipSessionRedirect: true,
    })
  },
}
