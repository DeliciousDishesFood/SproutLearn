// 题库接口（契约 §2.4）：班级下题库列表、新建、改名/描述、删除。
import { api } from './client'
import type {
  QuestionBank,
  QuestionBankCreatePayload,
  QuestionBankUpdatePayload,
} from './contract'

export const banksApi = {
  list(classId: number): Promise<QuestionBank[]> {
    return api.get<QuestionBank[]>(`/classes/${classId}/banks`)
  },

  create(classId: number, payload: QuestionBankCreatePayload): Promise<QuestionBank> {
    return api.post<QuestionBank>(`/classes/${classId}/banks`, payload, { skipGlobalError: true })
  },

  update(bankId: number, payload: QuestionBankUpdatePayload): Promise<QuestionBank> {
    return api.patch<QuestionBank>(`/banks/${bankId}`, payload, { skipGlobalError: true })
  },

  remove(bankId: number): Promise<null> {
    return api.delete<null>(`/banks/${bankId}`, { skipGlobalError: true })
  },
}
