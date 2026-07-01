/** Document intelligence — TypeScript types matching the backend schemas. */

export interface DocumentMetadata {
  id: string
  file_id: string
  extracted_text?: string | null
  title?: string | null
  author?: string | null
  language?: string | null
  language_confidence?: number | null
  page_count?: number | null
  word_count?: number | null
  character_count?: number | null
  document_type?: string | null
  created_date?: string | null
  modified_date?: string | null
  processing_time_ms?: number | null
  ocr_used: boolean
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface DocumentChunk {
  id: string
  file_id: string
  chunk_index: number
  content: string
  token_count?: number | null
  char_count: number
  chunk_type: string
  metadata_json?: string | null
  created_at?: string | null
}

export interface DocumentChunkList {
  chunks: DocumentChunk[]
  total: number
  chunk_type: string
  total_tokens: number
}

export interface DocumentAnalysis {
  id: string
  file_id: string
  summary?: string | null
  keywords: string[]
  topics: string[]
  entities: Record<string, unknown>[]
  category?: string | null
  language_confidence?: number | null
  model_used?: string | null
  analysis_completed_at?: string | null
  created_at?: string | null
}

export interface DocumentStatus {
  file_id: string
  filename: string
  processing_status: string
  processing_error?: string | null
  has_metadata: boolean
  has_analysis: boolean
  has_chunks: boolean
  chunk_count: number
}

export interface DocumentProcessRequest {
  chunk_size?: number
  chunk_overlap?: number
  chunk_strategy?: 'fixed' | 'paragraph' | 'sentence' | 'recursive'
  min_chunk_length?: number
  max_chunk_length?: number
  force_reprocess?: boolean
}
