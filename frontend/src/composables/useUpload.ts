// 上传 hook：客户端先做白名单/大小预检，失败项与后端 fail_list 合并展示。
import { computed, ref, shallowRef } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import { toUserMessage } from '@/api/client'
import type { UploadFailItem, UploadResult } from '@/api/types'
import {
  ERROR_CODE,
  MAX_FILES_PER_REQUEST,
  MAX_TOTAL_UPLOAD_MB,
  UPLOAD_ALLOWED_EXT,
  UPLOAD_MAX_MB,
} from '@/utils/constants'

function getExtension(name: string): string {
  const dotIndex = name.lastIndexOf('.')
  return dotIndex >= 0 ? name.slice(dotIndex + 1).toLowerCase() : ''
}

export function useUpload() {
  const uploading = ref(false)
  const progress = ref(0)
  const result = shallowRef<UploadResult | null>(null)
  const error = ref('')
  const selectedCount = ref(0)

  const successCount = computed(() => result.value?.success_list.length ?? 0)
  const failCount = computed(() => result.value?.fail_list.length ?? 0)

  function makeFail(fileName: string, code: number, message: string): UploadFailItem {
    return { file_name: fileName, error_code: code, error_message: message }
  }

  function validateFiles(files: File[]): { accepted: File[]; failures: UploadFailItem[] } {
    const accepted: File[] = []
    const failures: UploadFailItem[] = []
    for (const file of files) {
      const ext = getExtension(file.name)
      if (!UPLOAD_ALLOWED_EXT.includes(ext)) {
        failures.push(
          makeFail(
            file.name,
            ERROR_CODE.UNSUPPORTED_FORMAT,
            '文件类型不支持，请上传 PDF、Word、PPT、Markdown 或 TXT',
          ),
        )
        continue
      }
      if (file.size > UPLOAD_MAX_MB * 1024 * 1024) {
        failures.push(
          makeFail(file.name, ERROR_CODE.FILE_TOO_LARGE, `文件超过 ${UPLOAD_MAX_MB}MB 上限，请压缩后重试`),
        )
        continue
      }
      accepted.push(file)
    }
    return { accepted, failures }
  }

  async function upload(
    classId: number,
    files: File[],
    options: { courseName?: string } = {},
  ): Promise<UploadResult | null> {
    if (uploading.value || files.length === 0) return null
    error.value = ''
    result.value = null
    progress.value = 0
    selectedCount.value = files.length

    if (files.length > MAX_FILES_PER_REQUEST) {
      error.value = `单次最多上传 ${MAX_FILES_PER_REQUEST} 个文件，请分批上传`
      return null
    }
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
    if (totalBytes > MAX_TOTAL_UPLOAD_MB * 1024 * 1024) {
      error.value = `本次上传总大小超过 ${MAX_TOTAL_UPLOAD_MB}MB 上限，请分批上传`
      return null
    }

    const { accepted, failures } = validateFiles(files)
    if (accepted.length === 0) {
      result.value = { total: files.length, success_list: [], fail_list: failures }
      return result.value
    }

    uploading.value = true
    try {
      const response = await knowledgeApi.upload(
        { class_id: classId, course_name: options.courseName, files: accepted },
        (percent) => {
          progress.value = percent
        },
      )
      result.value = {
        ...response,
        total: response.total + failures.length,
        fail_list: [...failures, ...response.fail_list],
      }
      progress.value = 100
      return result.value
    } catch (err) {
      error.value = toUserMessage(err)
      return null
    } finally {
      uploading.value = false
    }
  }

  function reset(): void {
    uploading.value = false
    progress.value = 0
    result.value = null
    error.value = ''
    selectedCount.value = 0
  }

  return {
    uploading,
    progress,
    result,
    error,
    selectedCount,
    successCount,
    failCount,
    upload,
    reset,
  }
}
