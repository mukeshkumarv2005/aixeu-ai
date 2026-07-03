/** AI Task Assistant — TypeScript types matching backend Pydantic schemas. */

// ── Task draft (shared by generation, chat-to-task, document-to-task) ───────

export interface AITaskDraft {
  title: string
  description: string | null
  priority: string
  estimated_minutes: number | null
  due_date: string | null
  labels: string[]
}

// ── Generate tasks from natural language ─────────────────────────────────────

export interface AITaskGenerationRequest {
  text: string
  context?: string | null
}

export interface AITaskGenerationResponse {
  tasks: AITaskDraft[]
}

// ── Subtask generation ───────────────────────────────────────────────────────

export interface AISubtaskRequest {
  task_id: string
  count?: number | null
}

export interface AISubtaskItem {
  title: string
  description: string | null
  estimated_minutes: number | null
}

export interface AISubtaskResponse {
  subtasks: AISubtaskItem[]
}

// ── Effort estimation ────────────────────────────────────────────────────────

export interface AIEffortEstimateResponse {
  estimated_minutes: number
  confidence: string
  reasoning: string | null
}

// ── Priority / due-date suggestion ───────────────────────────────────────────

export interface AIPrioritySuggestionResponse {
  priority: string
  due_date: string | null
  reasoning: string | null
}

// ── Work summary ─────────────────────────────────────────────────────────────

export interface AISummaryRequest {
  start_date?: string | null
  end_date?: string | null
}

export interface AISummaryResponse {
  summary: string
  total_completed: number
  highlights: string[]
}

// ── Chat-to-task conversion ──────────────────────────────────────────────────

export interface AIConvertChatRequest {
  conversation_id: string
}

export interface AIConvertChatResponse {
  task: AITaskDraft
  key_points: string[]
}

// ── Document-to-task conversion ──────────────────────────────────────────────

export interface AIConvertDocumentRequest {
  document_id: string
}

export interface AIConvertDocumentResponse {
  task: AITaskDraft
  key_points: string[]
}

// ── Next-action generation ───────────────────────────────────────────────────

export interface AINextActionItem {
  title: string
  context: string | null
  source_task_id: string | null
  priority: string
}

export interface AINextActionsResponse {
  actions: AINextActionItem[]
  summary: string | null
}
