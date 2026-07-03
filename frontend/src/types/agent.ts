/** AI Agents — TypeScript types matching backend Pydantic schemas. */

// ── Constants ────────────────────────────────────────────────────────────────

export const AGENT_STATUSES = [
  'queued',
  'running',
  'paused',
  'completed',
  'failed',
  'cancelled',
  'timed_out',
] as const
export type AgentStatus = (typeof AGENT_STATUSES)[number]

export const MEMORY_TYPES = ['short_term', 'long_term', 'conversation'] as const
export const MEMORY_ROLES = ['user', 'assistant', 'system'] as const

export const TOOL_TYPES = [
  'knowledge_search',
  'document_reader',
  'task_manager',
  'global_search',
  'chat_history',
  'calculator',
  'current_time',
] as const
export type ToolType = (typeof TOOL_TYPES)[number]

export const TEMPLATE_CATEGORIES = [
  'general',
  'research',
  'coding',
  'writing',
  'assistant',
  'custom',
] as const
export type TemplateCategory = (typeof TEMPLATE_CATEGORIES)[number]

// ── Agent ────────────────────────────────────────────────────────────────────

export interface AgentResponse {
  id: string
  owner_id: string
  workspace_id: string | null
  name: string
  description: string | null
  system_prompt: string | null
  model: string
  temperature: number
  max_tokens: number | null
  enabled: boolean
  created_at: string
  updated_at: string | null
}

export interface AgentListResponse {
  items: AgentResponse[]
  total: number
  offset: number
  limit: number
}

export interface AgentCreate {
  name: string
  description?: string | null
  system_prompt?: string | null
  model?: string
  temperature?: number
  max_tokens?: number | null
  enabled?: boolean
}

export interface AgentUpdate {
  name?: string
  description?: string | null
  system_prompt?: string | null
  model?: string
  temperature?: number
  max_tokens?: number | null
  enabled?: boolean
}

// ── Agent Run ────────────────────────────────────────────────────────────────

export interface AgentRunResponse {
  id: string
  agent_id: string
  owner_id: string
  status: string
  started_at: string | null
  finished_at: string | null
  input_text: string | null
  result: string | null
  token_usage: Record<string, unknown> | null
  cost: number | null
  steps: Record<string, unknown> | null
  logs: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  updated_at: string | null
}

export interface AgentRunListResponse {
  items: AgentRunResponse[]
  total: number
  offset: number
  limit: number
}

// ── Agent Run Execution ──────────────────────────────────────────────────────

export interface AgentRunExecuteRequest {
  input_text: string
  stream?: boolean
}

export interface AgentRunExecuteResponse {
  run_id: string
  result: string | null
  token_usage: Record<string, unknown> | null
}

// ── Agent Tool ───────────────────────────────────────────────────────────────

export interface AgentToolResponse {
  id: string
  agent_id: string
  tool_type: string
  name: string
  description: string | null
  config: Record<string, unknown> | null
  enabled: boolean
  created_at: string
  updated_at: string | null
}

export interface AgentToolCreate {
  tool_type: string
  name: string
  description?: string | null
  config?: Record<string, unknown> | null
  enabled?: boolean
}

export interface AgentToolUpdate {
  name?: string
  description?: string | null
  config?: Record<string, unknown> | null
  enabled?: boolean
}

// ── Agent Template ───────────────────────────────────────────────────────────

export interface AgentTemplateResponse {
  id: string
  owner_id: string | null
  name: string
  description: string | null
  category: string | null
  system_prompt: string | null
  model: string
  temperature: number
  default_tools: Record<string, unknown> | null
  is_builtin: boolean
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface AgentTemplateListResponse {
  items: AgentTemplateResponse[]
  total: number
  offset: number
  limit: number
}

export interface AgentTemplateCreate {
  name: string
  description?: string | null
  category?: string
  system_prompt?: string | null
  model?: string
  temperature?: number
  default_tools?: Record<string, unknown>[] | null
}

export interface AgentTemplateUpdate {
  name?: string
  description?: string | null
  category?: string
  system_prompt?: string | null
  model?: string
  temperature?: number
  default_tools?: Record<string, unknown>[] | null
  is_active?: boolean
}

// ── Agent Memory ─────────────────────────────────────────────────────────────

export interface AgentMemoryResponse {
  id: string
  agent_id: string
  run_id: string | null
  memory_type: string
  role: string | null
  content: string
  summary: string | null
  memory_metadata: Record<string, unknown> | null
  importance: number | null
  expires_at: string | null
  created_at: string
  updated_at: string | null
}

export interface AgentMemoryListResponse {
  items: AgentMemoryResponse[]
  total: number
  offset: number
  limit: number
}
