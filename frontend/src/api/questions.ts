// 题库接口（M2-C/M2.5）：导入预览/提交、筛选列表、编辑、软删除、讲评（含流式）。
import { api, ApiError } from '@/api/client'
import type {
  Paged,
  QuestionExplainResult,
  QuestionImportCommit,
  QuestionImportCommitPayload,
  QuestionImportPreview,
  QuestionItem,
  QuestionListQuery,
  QuestionUpdatePayload,
} from '@/api/types'
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants'

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
  onDone?: (payload: {
    engine?: string
    degraded?: boolean
    elapsed_ms?: number
  }) => void
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
      const body = (await response.json()) as { code?: number; message?: string }
      if (body && typeof body.message === 'string' && body.message) message = body.message
    } catch {
      // 非 JSON 响应保持默认文案
    }
    throw new ApiError({ code: -1, message, httpStatus: response.status })
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

export const questionsApi = {
  previewImport(classId: number, file: File): Promise<QuestionImportPreview> {
    const formData = new FormData()
    formData.append('file', file, file.name)
    return api.post<QuestionImportPreview>(
      `/classes/${classId}/questions/import/preview`,
      formData,
      { timeout: 0, skipGlobalError: true },
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
        type: query.type,
        // 后端实际读取 tag；同时带 knowledge_tag，保持与派工包参数名一致。
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

  /** M2.5 流式讲评：SSE（meta → delta… → done），失败时由调用方保留已收内容。 */
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
