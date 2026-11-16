// 通知 / 公告接口（契约 §2.10）。
import { api } from './client'
import type {
  AnnouncementPayload,
  AnnouncementResult,
  NotificationListResult,
  UnreadCountResult,
} from './contract'

export interface NotificationListQuery {
  page?: number
  page_size?: number
  unread_only?: boolean
}

export const notificationsApi = {
  list(query: NotificationListQuery = {}): Promise<NotificationListResult> {
    return api.get<NotificationListResult>('/notifications', {
      params: {
        page: query.page ?? 1,
        page_size: query.page_size ?? 20,
        unread_only: query.unread_only ?? false,
      },
      skipGlobalError: true,
    })
  },

  unreadCount(): Promise<UnreadCountResult> {
    return api.get<UnreadCountResult>('/notifications/unread-count', {
      skipGlobalError: true,
    })
  },

  read(id: number): Promise<null> {
    return api.post<null>(`/notifications/${id}/read`, undefined, { skipGlobalError: true })
  },

  readAll(): Promise<{ count: number }> {
    return api.post<{ count: number }>('/notifications/read-all', undefined, {
      skipGlobalError: true,
    })
  },

  announce(classId: number, payload: AnnouncementPayload): Promise<AnnouncementResult> {
    return api.post<AnnouncementResult>(`/classes/${classId}/announcements`, payload, {
      skipGlobalError: true,
    })
  },
}
