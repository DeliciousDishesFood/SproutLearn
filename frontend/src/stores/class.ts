// 班级 store：缓存教师班级列表与当前班级详情，页面共享 loading/error 状态。
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { classesApi } from '@/api/classes'
import type {
  ClassCreatePayload,
  ClassCreateResult,
  ClassDetail,
  ClassListItem,
  StudentListItem,
} from '@/api/types'
import { toUserMessage } from '@/api/client'
import { DASHBOARD_PAGE_SIZE, PAGE_SIZE } from '@/utils/constants'

export const useClassStore = defineStore('class', () => {
  const classes = ref<ClassListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(PAGE_SIZE)
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref('')

  const currentClass = ref<ClassDetail | null>(null)
  const currentLoading = ref(false)
  const currentError = ref('')

  const students = ref<StudentListItem[]>([])
  const studentsTotal = ref(0)
  const studentsPage = ref(1)
  const studentsPageSize = ref(PAGE_SIZE)
  const studentsKeyword = ref('')
  const studentsLoading = ref(false)
  const studentsError = ref('')

  async function fetchClasses(options: { page?: number; pageSize?: number; silent?: boolean } = {}) {
    const nextPage = options.page ?? page.value
    const nextPageSize = options.pageSize ?? pageSize.value
    if (!options.silent) loading.value = true
    error.value = ''
    try {
      const result = await classesApi.list({ page: nextPage, page_size: nextPageSize })
      classes.value = result.list
      total.value = result.total
      page.value = result.page
      pageSize.value = result.page_size
      loaded.value = true
    } catch (err) {
      error.value = toUserMessage(err)
      throw err
    } finally {
      if (!options.silent) loading.value = false
    }
  }

  /** 工作台统计需要一次性取满（50 为接口上限）。 */
  async function fetchAllClasses(): Promise<ClassListItem[]> {
    loading.value = true
    error.value = ''
    try {
      const result = await classesApi.list({ page: 1, page_size: DASHBOARD_PAGE_SIZE })
      classes.value = result.list
      total.value = result.total
      page.value = result.page
      pageSize.value = result.page_size
      loaded.value = true
      return result.list
    } catch (err) {
      error.value = toUserMessage(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createClass(payload: ClassCreatePayload): Promise<ClassCreateResult> {
    const created = await classesApi.create(payload)
    await fetchAllClasses().catch(() => undefined)
    return created
  }

  async function fetchDetail(classId: number, silent = false) {
    if (!silent) currentLoading.value = true
    currentError.value = ''
    try {
      currentClass.value = await classesApi.detail(classId)
    } catch (err) {
      currentClass.value = null
      currentError.value = toUserMessage(err)
      throw err
    } finally {
      if (!silent) currentLoading.value = false
    }
  }

  async function fetchStudents(
    classId: number,
    options: { page?: number; pageSize?: number; keyword?: string; silent?: boolean } = {},
  ) {
    const nextPage = options.page ?? 1
    const nextPageSize = options.pageSize ?? PAGE_SIZE
    const nextKeyword = options.keyword ?? ''
    if (!options.silent) studentsLoading.value = true
    studentsError.value = ''
    try {
      const result = await classesApi.students(classId, {
        page: nextPage,
        page_size: nextPageSize,
        keyword: nextKeyword,
      })
      students.value = result.list
      studentsTotal.value = result.total
      studentsPage.value = result.page
      studentsPageSize.value = result.page_size
      studentsKeyword.value = nextKeyword
    } catch (err) {
      studentsError.value = toUserMessage(err)
      throw err
    } finally {
      if (!options.silent) studentsLoading.value = false
    }
  }

  function resetCurrent(): void {
    currentClass.value = null
    currentError.value = ''
    students.value = []
    studentsTotal.value = 0
    studentsError.value = ''
  }

  return {
    classes,
    total,
    page,
    pageSize,
    loading,
    loaded,
    error,
    currentClass,
    currentLoading,
    currentError,
    students,
    studentsTotal,
    studentsPage,
    studentsPageSize,
    studentsKeyword,
    studentsLoading,
    studentsError,
    fetchClasses,
    fetchAllClasses,
    createClass,
    fetchDetail,
    fetchStudents,
    resetCurrent,
  }
})
