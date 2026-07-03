/** Global Search — TypeScript types matching backend Pydantic schemas. */

// ── Search result ─────────────────────────────────────────────────────────

export interface SearchResult {
  entity_type: 'conversation' | 'message' | 'file' | 'kb_document' | 'task'
  entity_id: string
  title: string
  snippet: string
  score: number
  url: string
  entity_metadata: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
  offset: number
  limit: number
}

// ── Search filters ────────────────────────────────────────────────────────

export interface SearchFilters {
  entity_types?: string[]
  status?: string
  priority?: string
  kb_id?: string
  date_from?: string
  date_to?: string
}

// ── Saved searches ────────────────────────────────────────────────────────

export interface SavedSearchResponse {
  id: string
  query: string
  filters: Record<string, unknown> | null
  created_at: string
}

export interface SavedSearchCreate {
  query: string
  filters?: Record<string, unknown> | null
}

export interface SavedSearchUpdate {
  query?: string
  filters?: Record<string, unknown> | null
}

// ── Recent searches ───────────────────────────────────────────────────────

export interface RecentSearchResponse {
  id: string
  query: string
  searched_at: string
}

// ── Entity type config for UI ─────────────────────────────────────────────

export const ENTITY_TYPES = [
  { value: 'conversation', label: 'Conversations', icon: 'MessageSquare' },
  { value: 'message', label: 'Messages', icon: 'MessagesSquare' },
  { value: 'file', label: 'Files', icon: 'FileText' },
  { value: 'kb_document', label: 'Knowledge Base', icon: 'BookOpen' },
  { value: 'task', label: 'Tasks', icon: 'CheckSquare' },
] as const

export type EntityType = (typeof ENTITY_TYPES)[number]['value']
