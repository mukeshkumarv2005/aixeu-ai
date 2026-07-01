/** Dashboard — TypeScript types matching the backend schemas. */

export interface DashboardStats {
  total_conversations: number
  total_messages: number
  total_files: number
  total_storage_bytes: number
  total_input_tokens: number
  total_output_tokens: number
  total_documents_processed: number
}

export interface RecentChatItem {
  id: string
  title: string | null
  model: string
  message_count: number
  updated_at: string
  created_at: string
}

export interface RecentActivityItem {
  id: string
  type: 'chat' | 'upload' | 'message'
  description: string
  created_at: string
}

export interface DailyTokenUsage {
  date: string
  input_tokens: number
  output_tokens: number
}

export interface FileInfo {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  storage_path: string
  checksum?: string | null
  processing_status?: string
  is_temporary: boolean
  created_at: string
  updated_at: string | null
}

export interface DashboardResponse {
  stats: DashboardStats
  recent_chats: RecentChatItem[]
  recent_files: FileInfo[]
  recent_activity: RecentActivityItem[]
}

export interface UsageResponse {
  total_input_tokens: number
  total_output_tokens: number
  total_messages: number
  total_conversations: number
  daily_usage: DailyTokenUsage[]
  storage_total_bytes: number
  storage_total_files: number
}
