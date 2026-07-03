/** Settings — TypeScript types matching backend Pydantic schemas. */

// ── Constants ────────────────────────────────────────────────────────────────

export const AI_PROVIDERS = [
  'openai',
  'anthropic',
  'gemini',
  'openrouter',
  'groq',
  'azure_openai',
  'ollama',
] as const
export type AiProvider = (typeof AI_PROVIDERS)[number]

export const ACCENT_COLORS = [
  'indigo',
  'emerald',
  'amber',
  'rose',
  'violet',
  'sky',
] as const
export type AccentColor = (typeof ACCENT_COLORS)[number]

export const THEME_OPTIONS = ['light', 'dark', 'system'] as const
export type ThemeOption = (typeof THEME_OPTIONS)[number]

export const DENSITY_OPTIONS = ['comfortable', 'compact'] as const
export type DensityOption = (typeof DENSITY_OPTIONS)[number]

// ── User Settings ────────────────────────────────────────────────────────────

export interface UserSettingsResponse {
  theme: string
  timezone: string
  language: string
  default_model: string
  default_agent_id: string | null
  notify_email_task_reminders: boolean
  notify_email_agent_completion: boolean
  notify_email_document_processing: boolean
  notify_email_knowledge_indexing: boolean
  notify_browser_task_reminders: boolean
  notify_browser_agent_completion: boolean
  accent_color: string
  sidebar_default_open: boolean
  density: string
  animations_enabled: boolean
  font_scale: number
  extra_settings: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
}

export interface UserSettingsUpdate {
  theme?: string
  timezone?: string
  language?: string
  default_model?: string
  default_agent_id?: string | null
  notify_email_task_reminders?: boolean
  notify_email_agent_completion?: boolean
  notify_email_document_processing?: boolean
  notify_email_knowledge_indexing?: boolean
  notify_browser_task_reminders?: boolean
  notify_browser_agent_completion?: boolean
  accent_color?: string
  sidebar_default_open?: boolean
  density?: string
  animations_enabled?: boolean
  font_scale?: number
  extra_settings?: Record<string, unknown> | null
}

// ── API Provider ─────────────────────────────────────────────────────────────

export interface ApiProviderResponse {
  id: string
  provider: string
  display_name: string | null
  api_key_encrypted: string
  config: Record<string, unknown> | null
  is_active: boolean
  order: number
  created_at: string
  updated_at: string | null
}

export interface ApiProviderCreate {
  provider: string
  display_name?: string | null
  api_key: string
  config?: Record<string, unknown> | null
}

export interface ApiProviderUpdate {
  display_name?: string | null
  api_key?: string
  config?: Record<string, unknown> | null
  is_active?: boolean
}

export interface ApiProviderListResponse {
  items: ApiProviderResponse[]
}

// ── Sessions ─────────────────────────────────────────────────────────────────

export interface UserSessionResponse {
  id: string
  device_name: string | null
  ip_address: string | null
  user_agent: string | null
  is_current: boolean
  expires_at: string
  revoked_at: string | null
  created_at: string
}

export interface UserSessionListResponse {
  items: UserSessionResponse[]
}

// ── Password ─────────────────────────────────────────────────────────────────

export interface PasswordChangeRequest {
  current_password: string
  new_password: string
}

// ── Import / Export ──────────────────────────────────────────────────────────

export interface SettingsExportResponse {
  settings: UserSettingsResponse
  providers: ApiProviderResponse[]
  session_count: number
}

export interface SettingsImport {
  settings: UserSettingsUpdate
  providers: ApiProviderCreate[]
}
