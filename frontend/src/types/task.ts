/** Task Management — TypeScript types matching backend Pydantic schemas. */

// ── Status & priority constants ──────────────────────────────────────────

export const TASK_STATUSES = ['todo', 'in_progress', 'review', 'done', 'archived'] as const
export type TaskStatus = (typeof TASK_STATUSES)[number]

export const TASK_PRIORITIES = ['low', 'medium', 'high', 'critical'] as const
export type TaskPriority = (typeof TASK_PRIORITIES)[number]

// ── Labels ───────────────────────────────────────────────────────────────

export interface TaskLabel {
  id: string
  name: string
  color: string | null
}

// ── Comments ─────────────────────────────────────────────────────────────

export interface TaskComment {
  id: string
  task_id: string
  author_id: string
  content: string
  created_at: string
  updated_at: string | null
}

// ── Attachments ──────────────────────────────────────────────────────────

export interface TaskAttachment {
  id: string
  task_id: string
  file_id: string
  uploaded_by: string
  created_at: string
}

// ── Task ─────────────────────────────────────────────────────────────────

export interface TaskResponse {
  id: string
  owner_id: string
  title: string
  description: string | null
  status: string
  priority: string
  due_date: string | null
  reminder_at: string | null
  estimated_minutes: number | null
  completed_at: string | null
  uploaded_document_id: string | null
  chat_conversation_id: string | null
  kb_document_id: string | null
  created_at: string
  updated_at: string | null
  labels: TaskLabel[]
  comments: TaskComment[]
  attachments: TaskAttachment[]
}

export interface TaskListResponse {
  items: TaskResponse[]
  total: number
  offset: number
  limit: number
}

// ── Create / Update ──────────────────────────────────────────────────────

export interface TaskCreate {
  title: string
  description?: string | null
  status?: string
  priority?: string
  due_date?: string | null
  reminder_at?: string | null
  estimated_minutes?: number | null
  uploaded_document_id?: string | null
  chat_conversation_id?: string | null
  kb_document_id?: string | null
}

export interface TaskUpdate {
  title?: string
  description?: string | null
  status?: string
  priority?: string
  due_date?: string | null
  reminder_at?: string | null
  estimated_minutes?: number | null
}

// ── Board / Calendar / Stats ─────────────────────────────────────────────

export interface TaskBoardResponse {
  todo: TaskResponse[]
  in_progress: TaskResponse[]
  review: TaskResponse[]
  done: TaskResponse[]
  archived: TaskResponse[]
}

export interface TaskCalendarResponse {
  items: TaskResponse[]
  total: number
  start_date: string | null
  end_date: string | null
}

export interface TaskStats {
  total: number
  todo: number
  in_progress: number
  review: number
  done: number
  archived: number
  overdue: number
  critical: number
  high: number
  medium: number
  low: number
  incomplete_by_priority: Record<string, number>
}

// ── Label create ─────────────────────────────────────────────────────────

export interface TaskLabelCreate {
  name: string
  color?: string | null
}

// ── Comment create ───────────────────────────────────────────────────────

export interface TaskCommentCreate {
  content: string
}
