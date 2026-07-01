/** Knowledge Base — TypeScript types matching the backend schemas. */

export interface KnowledgeBaseResponse {
  id: string
  user_id: string
  name: string
  description: string | null
  embedding_model: string
  dimension: number
  document_count: number
  total_chunks: number
  created_at: string
  updated_at: string | null
}

export interface KnowledgeBaseListResponse {
  items: KnowledgeBaseResponse[]
  total: number
}

export interface KnowledgeBaseDocumentResponse {
  id: string
  knowledge_base_id: string
  file_id: string | null
  title: string
  content: string
  metadata_json: string | null
  status: string
  error_message: string | null
  chunk_count: number
  created_at: string
  updated_at: string | null
}

export interface KnowledgeBaseDocumentListResponse {
  items: KnowledgeBaseDocumentResponse[]
  total: number
}

export interface SemanticSearchResult {
  document_id: string
  document_title: string
  content: string
  chunk_index: number
  similarity: number
  metadata_json: string | null
}

export interface SemanticSearchResponse {
  query: string
  results: SemanticSearchResult[]
  total: number
  embedding_model: string
  search_time_ms: number
}

export interface DocumentProcessStatus {
  document_id: string
  status: string
  error_message: string | null
  chunk_count: number
}
