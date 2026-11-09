// 统一请求 hook：维护 loading / error / data，并提供过期请求保护。
import { ref, shallowRef } from 'vue'
import { toUserMessage } from '@/api/client'

export interface UseRequestOptions<TData> {
  initialData?: TData | null
  onSuccess?: (data: TData) => void
  onError?: (message: string, error: unknown) => void
}

export function useRequest<TArgs extends unknown[], TData>(
  requestFn: (...args: TArgs) => Promise<TData>,
  options: UseRequestOptions<TData> = {},
) {
  const data = shallowRef<TData | null>(options.initialData ?? null)
  const loading = ref(false)
  const error = ref('')
  const rawError = shallowRef<unknown>(null)
  let sequence = 0

  async function run(...args: TArgs): Promise<TData | null> {
    const current = ++sequence
    loading.value = true
    error.value = ''
    rawError.value = null
    try {
      const result = await requestFn(...args)
      if (current !== sequence) return null
      data.value = result
      options.onSuccess?.(result)
      return result
    } catch (err) {
      if (current !== sequence) return null
      rawError.value = err
      error.value = toUserMessage(err)
      options.onError?.(error.value, err)
      return null
    } finally {
      if (current === sequence) loading.value = false
    }
  }

  function reset(): void {
    sequence += 1
    data.value = options.initialData ?? null
    loading.value = false
    error.value = ''
    rawError.value = null
  }

  return { data, loading, error, rawError, run, reset }
}
