/** Tasks — TanStack Query hooks for all Task CRUD and board/calendar/stats endpoints. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  TaskResponse,
  TaskListResponse,
  TaskBoardResponse,
  TaskCalendarResponse,
  TaskStats,
  TaskCreate,
  TaskUpdate,
} from '@/types/task'

// ── Query key factory ────────────────────────────────────────────────────

export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  board: () => [...taskKeys.all, 'board'] as const,
  calendar: () => [...taskKeys.all, 'calendar'] as const,
  stats: () => [...taskKeys.all, 'stats'] as const,
  overdue: () => [...taskKeys.all, 'overdue'] as const,
}

// ── List tasks ───────────────────────────────────────────────────────────

interface TaskListFilters extends Record<string, unknown> {
  status?: string
  priority?: string
  search?: string
  offset?: number
  limit?: number
}

export function useTasks(filters: TaskListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.search) params.set('search', filters.search)
  if (filters.offset) params.set('offset', String(filters.offset))
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()

  return useQuery<TaskListResponse>({
    queryKey: taskKeys.list(filters),
    queryFn: () =>
      apiClient.get<TaskListResponse>(`/tasks${qs ? `?${qs}` : ''}`),
    staleTime: 30_000,
  })
}

// ── Search tasks ─────────────────────────────────────────────────────────

export function useTaskSearch(q: string, offset = 0, limit = 50) {
  return useQuery<TaskListResponse>({
    queryKey: [...taskKeys.all, 'search', q, offset, limit],
    queryFn: () =>
      apiClient.get<TaskListResponse>(
        `/tasks/search?q=${encodeURIComponent(q)}&offset=${offset}&limit=${limit}`,
      ),
    enabled: q.length > 0,
    staleTime: 15_000,
  })
}

// ── Single task ──────────────────────────────────────────────────────────

export function useTask(taskId: string | undefined) {
  return useQuery<TaskResponse>({
    queryKey: taskKeys.detail(taskId ?? ''),
    queryFn: () => apiClient.get<TaskResponse>(`/tasks/${taskId}`),
    enabled: !!taskId,
    staleTime: 15_000,
  })
}

// ── Board ────────────────────────────────────────────────────────────────

export function useTaskBoard() {
  return useQuery<TaskBoardResponse>({
    queryKey: taskKeys.board(),
    queryFn: () => apiClient.get<TaskBoardResponse>('/tasks/board'),
    staleTime: 10_000,
  })
}

// ── Calendar ─────────────────────────────────────────────────────────────

export function useTaskCalendar(startDate?: string, endDate?: string) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const qs = params.toString()

  return useQuery<TaskCalendarResponse>({
    queryKey: [...taskKeys.calendar(), { startDate, endDate }],
    queryFn: () =>
      apiClient.get<TaskCalendarResponse>(`/tasks/calendar${qs ? `?${qs}` : ''}`),
    staleTime: 30_000,
  })
}

// ── Stats ────────────────────────────────────────────────────────────────

export function useTaskStats() {
  return useQuery<TaskStats>({
    queryKey: taskKeys.stats(),
    queryFn: () => apiClient.get<TaskStats>('/tasks/stats'),
    staleTime: 30_000,
  })
}

// ── Overdue ──────────────────────────────────────────────────────────────

export function useOverdueTasks(limit = 50) {
  return useQuery<TaskListResponse>({
    queryKey: [...taskKeys.overdue(), limit],
    queryFn: () =>
      apiClient.get<TaskListResponse>(`/tasks/overdue?limit=${limit}`),
    staleTime: 30_000,
  })
}

// ── Tasks by resource ────────────────────────────────────────────────────

interface TaskResourceFilters {
  kb_document_id?: string
  chat_conversation_id?: string
  uploaded_document_id?: string
  limit?: number
}

export function useTasksByResource(filters: TaskResourceFilters) {
  const params = new URLSearchParams()
  if (filters.kb_document_id) params.set('kb_document_id', filters.kb_document_id)
  if (filters.chat_conversation_id) params.set('chat_conversation_id', filters.chat_conversation_id)
  if (filters.uploaded_document_id) params.set('uploaded_document_id', filters.uploaded_document_id)
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()

  return useQuery<TaskListResponse>({
    queryKey: [...taskKeys.all, 'by-resource', filters],
    queryFn: () =>
      apiClient.get<TaskListResponse>(`/tasks/by-resource?${qs}`),
    enabled: !!(filters.kb_document_id || filters.chat_conversation_id || filters.uploaded_document_id),
    staleTime: 30_000,
  })
}

// ── Create task ──────────────────────────────────────────────────────────

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation<TaskResponse, Error, TaskCreate>({
    mutationFn: (body) => apiClient.post<TaskResponse>('/tasks', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
      queryClient.invalidateQueries({ queryKey: taskKeys.board() })
      queryClient.invalidateQueries({ queryKey: taskKeys.stats() })
    },
  })
}

// ── Update task ──────────────────────────────────────────────────────────

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation<TaskResponse, Error, { taskId: string; body: TaskUpdate }>({
    mutationFn: ({ taskId, body }) =>
      apiClient.patch<TaskResponse>(`/tasks/${taskId}`, body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
      queryClient.invalidateQueries({ queryKey: taskKeys.board() })
      queryClient.invalidateQueries({ queryKey: taskKeys.calendar() })
      queryClient.invalidateQueries({ queryKey: taskKeys.stats() })
    },
  })
}

// ── Delete task ──────────────────────────────────────────────────────────

export function useDeleteTask() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (taskId) => apiClient.delete(`/tasks/${taskId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all })
    },
  })
}

// ── Status transitions ───────────────────────────────────────────────────

export function useCompleteTask() {
  const queryClient = useQueryClient()
  return useMutation<TaskResponse, Error, string>({
    mutationFn: (taskId) =>
      apiClient.post<TaskResponse>(`/tasks/${taskId}/complete`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
      queryClient.invalidateQueries({ queryKey: taskKeys.board() })
      queryClient.invalidateQueries({ queryKey: taskKeys.stats() })
    },
  })
}

export function useArchiveTask() {
  const queryClient = useQueryClient()
  return useMutation<TaskResponse, Error, string>({
    mutationFn: (taskId) =>
      apiClient.post<TaskResponse>(`/tasks/${taskId}/archive`),
    onSuccess: (_data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all })
    },
  })
}

export function useRestoreTask() {
  const queryClient = useQueryClient()
  return useMutation<TaskResponse, Error, string>({
    mutationFn: (taskId) =>
      apiClient.post<TaskResponse>(`/tasks/${taskId}/restore`),
    onSuccess: (_data) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all })
    },
  })
}

// ── Labels ───────────────────────────────────────────────────────────────

export function useAddLabel() {
  const queryClient = useQueryClient()
  return useMutation<
    { id: string; name: string; color: string | null },
    Error,
    { taskId: string; name: string; color?: string | null }
  >({
    mutationFn: ({ taskId, name, color }) =>
      apiClient.post<{ id: string; name: string; color: string | null }>(
        `/tasks/${taskId}/labels`,
        { name, color },
      ),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

export function useRemoveLabel() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { taskId: string; labelId: string }>({
    mutationFn: ({ taskId, labelId }) =>
      apiClient.delete(`/tasks/${taskId}/labels/${labelId}`),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

// ── Comments ─────────────────────────────────────────────────────────────

export function useAddComment() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { taskId: string; content: string }>({
    mutationFn: ({ taskId, content }) =>
      apiClient.post(`/tasks/${taskId}/comments`, { content }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

export function useUpdateComment() {
  const queryClient = useQueryClient()
  return useMutation<
    void,
    Error,
    { taskId: string; commentId: string; content: string }
  >({
    mutationFn: ({ taskId, commentId, content }) =>
      apiClient.patch(`/tasks/${taskId}/comments/${commentId}`, { content }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

export function useDeleteComment() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { taskId: string; commentId: string }>({
    mutationFn: ({ taskId, commentId }) =>
      apiClient.delete(`/tasks/${taskId}/comments/${commentId}`),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

// ── Attachments ──────────────────────────────────────────────────────────

export function useAddAttachment() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { taskId: string; fileId: string }>({
    mutationFn: ({ taskId, fileId }) =>
      apiClient.post(`/tasks/${taskId}/attachments`, { file_id: fileId }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}

export function useRemoveAttachment() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { taskId: string; attachmentId: string }>({
    mutationFn: ({ taskId, attachmentId }) =>
      apiClient.delete(`/tasks/${taskId}/attachments/${attachmentId}`),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(vars.taskId) })
    },
  })
}
