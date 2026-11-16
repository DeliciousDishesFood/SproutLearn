// 题库与题目接口（契约 §2.4 / §2.5）：导入两步、筛选、编辑、讲评（含 SSE）。
import { api, ApiError } from './client'
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants'
import type {
  Paged,
  QuestionBank,
  QuestionBankCreatePayload,
  QuestionBankUpdatePayload,
  QuestionExplainResult,
  QuestionImportCommit,
  QuestionImportCommitPayload,
  QuestionImportPreview,
  QuestionItem,
  QuestionListQuery,
  QuestionUpdatePayload,
} from './contract'

interface ExplainStreamPayload {
  engine?: string
  model?: string | null
  content?: string
  degraded?: boolean
  elapsed_ms?: number
}

export interface ExplainStreamHandlers {
  onMeta?: (payload: { engine?: string; model?: string | null }) => void
  onDelta: (content: string) => void
  onDone?: (payload: { engine?: string; degraded?: boolean; elapsed_ms?: number }) => void
}

export interface ExplainStreamHandle {
  promise: Promise<void>
  abort: () => void
}

function parseSseBlock(block: string): { event: string; payload: ExplainStreamPayload } | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }
  if (dataLines.length === 0) return null
  try {
    return { event, payload: JSON.parse(dataLines.join('\n')) as ExplainStreamPayload }
  } catch {
    return null
  }
}

async function readExplainStream(
  questionId: number,
  studentAnswer: unknown,
  handlers: ExplainStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem(STORAGE_KEYS.token)
  const response = await fetch(`${API_BASE_URL}/questions/${questionId}/explain/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(studentAnswer === undefined ? {} : { student_answer: studentAnswer }),
    signal,
  })

  const contentType = response.headers.get('content-type') ?? ''
  if (!response.ok || !contentType.includes('text/event-stream') || !response.body) {
    let message = '讲评流暂时不可用'
    try {
      const body = (await response.json()) as { message?: string }
      if (body && typeof body.message === 'string' && body.message) message = body.message
    } catch {
      // 非 JSON 响应保持默认文案
    }
    throw new ApiError({ code: -1, message, http_status: response.status })
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const dispatch = (block: string): void => {
    const parsed = parseSseBlock(block)
    if (!parsed) return
    const { event, payload } = parsed
    if (event === 'meta') {
      handlers.onMeta?.(payload)
    } else if (event === 'done') {
      handlers.onDone?.(payload)
    } else if (event === 'delta') {
      handlers.onDelta(payload.content ?? '')
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() ?? ''
    for (const block of blocks) dispatch(block)
  }
  buffer += decoder.decode()
  if (buffer.trim()) dispatch(buffer)
}

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

export const questionsApi = {
  previewImport(classId: number, file: File, bankId?: number | null): Promise<QuestionImportPreview> {
    const formData = new FormData()
    formData.append('file', file, file.name)
    if (bankId !== undefined && bankId !== null) formData.append('bank_id', String(bankId))
    return api.post<QuestionImportPreview>(
      `/classes/${classId}/questions/import/preview`,
      formData,
      { timeout: 0, skipGlobalError: true },
    )
  },

  /** v1.1：AI 智能识别预览；文件抽取 + LLM 结构化，最多 2 分钟。 */
  aiPreview(
    classId: number,
    file: File,
    bankId?: number | null,
    maxQuestions = 50,
  ): Promise<QuestionImportPreview> {
    const formData = new FormData()
    formData.append('file', file, file.name)
    if (bankId !== undefined && bankId !== null) formData.append('bank_id', String(bankId))
    formData.append('max_questions', String(maxQuestions))
    return api.post<QuestionImportPreview>(
      `/classes/${classId}/questions/import/ai-preview`,
      formData,
      { timeout: 120000, skipGlobalError: true },
    )
  },

  commitImport(
    classId: number,
    payload: QuestionImportCommitPayload,
  ): Promise<QuestionImportCommit> {
    return api.post<QuestionImportCommit>(`/classes/${classId}/questions/import/commit`, payload, {
      timeout: 0,
      skipGlobalError: true,
    })
  },

  list(classId: number, query: QuestionListQuery = {}): Promise<Paged<QuestionItem>> {
    const tag = query.knowledge_tag?.trim() || undefined
    return api.get<Paged<QuestionItem>>(`/classes/${classId}/questions`, {
      params: {
        bank_id: query.bank_id,
        type: query.type,
        // 后端读取 tag；契约派工参数名为 knowledge_tag，两者同值。
        tag,
        knowledge_tag: tag,
        difficulty: query.difficulty,
        status: query.status,
        keyword: query.keyword?.trim() || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 10,
      },
    })
  },

  update(questionId: number, payload: QuestionUpdatePayload): Promise<QuestionItem> {
    return api.patch<QuestionItem>(`/questions/${questionId}`, payload, { skipGlobalError: true })
  },

  remove(questionId: number): Promise<null> {
    return api.delete<null>(`/questions/${questionId}`, { skipGlobalError: true })
  },

  explain(questionId: number, studentAnswer?: unknown): Promise<QuestionExplainResult> {
    return api.post<QuestionExplainResult>(
      `/questions/${questionId}/explain`,
      studentAnswer === undefined ? {} : { student_answer: studentAnswer },
      { timeout: 60000, skipGlobalError: true },
    )
  },

  explainStream(
    questionId: number,
    handlers: ExplainStreamHandlers,
    studentAnswer?: unknown,
  ): ExplainStreamHandle {
    const controller = new AbortController()
    return {
      promise: readExplainStream(questionId, studentAnswer, handlers, controller.signal),
      abort: () => controller.abort(),
    }
  },
}
