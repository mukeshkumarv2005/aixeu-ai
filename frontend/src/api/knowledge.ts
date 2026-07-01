/** Knowledge Base — TanStack Query hooks for all KB API endpoints. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  KnowledgeBaseResponse,
  KnowledgeBaseListResponse,
  KnowledgeBaseDocumentResponse,
  KnowledgeBaseDocumentListResponse,
  SemanticSearchResponse,
  DocumentProcessStatus,
} from '@/types/knowledge'

// ── Knowledge Bases ─────────────────────────────────────────────────────

export function useKnowledgeBases(offset = 0, limit = 20) {
  return useQuery<KnowledgeBaseListResponse>({
    queryKey: ['knowledge-bases', { offset, limit }],
    queryFn: () =>
      apiClient.get<KnowledgeBaseListResponse>(
        `/knowledge-bases?offset=${offset}&limit=${limit}`,
      ),
  })
}

export function useKnowledgeBase(kbId: string | undefined) {
  return useQuery<KnowledgeBaseResponse>({
    queryKey: ['knowledge-base', kbId],
    queryFn: () =>
      apiClient.get<KnowledgeBaseResponse>(`/knowledge-bases/${kbId}`),
    enabled: !!kbId,
  })
}

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient()
  return useMutation<
    KnowledgeBaseResponse,
    Error,
    { name: string; description?: string; embedding_model?: string }
  >({
    mutationFn: (body) =>
      apiClient.post<KnowledgeBaseResponse>('/knowledge-bases', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
    },
  })
}

export function useUpdateKnowledgeBase(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation<
    KnowledgeBaseResponse,
    Error,
    { name?: string; description?: string }
  >({
    mutationFn: (body) =>
      apiClient.patch<KnowledgeBaseResponse>(
        `/knowledge-bases/${kbId}`,
        body,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-base', kbId] })
    },
  })
}

export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (kbId) => apiClient.delete(`/knowledge-bases/${kbId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
    },
  })
}

// ── Documents ───────────────────────────────────────────────────────────

export function useKbDocuments(kbId: string | undefined, offset = 0, limit = 50) {
  return useQuery<KnowledgeBaseDocumentListResponse>({
    queryKey: ['kb-documents', kbId, { offset, limit }],
    queryFn: () =>
      apiClient.get<KnowledgeBaseDocumentListResponse>(
        `/knowledge-bases/${kbId}/documents?offset=${offset}&limit=${limit}`,
      ),
    enabled: !!kbId,
  })
}

export function useAddKbDocument(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation<
    KnowledgeBaseDocumentResponse,
    Error,
    { title: string; content: string; file_id?: string; metadata_json?: string }
  >({
    mutationFn: (body) =>
      apiClient.post<KnowledgeBaseDocumentResponse>(
        `/knowledge-bases/${kbId}/documents`,
        body,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-base', kbId] })
    },
  })
}

export function useDeleteKbDocument(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (docId) =>
      apiClient.delete(`/knowledge-bases/${kbId}/documents/${docId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-base', kbId] })
    },
  })
}

export function useProcessKbDocument(kbId: string) {
  const queryClient = useQueryClient()
  return useMutation<DocumentProcessStatus, Error, string>({
    mutationFn: (docId) =>
      apiClient.post<DocumentProcessStatus>(
        `/knowledge-bases/${kbId}/documents/${docId}/process`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kb-documents', kbId] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-base', kbId] })
    },
  })
}

// ── Semantic Search ─────────────────────────────────────────────────────

export function useSemanticSearch(kbId: string) {
  return useMutation<
    SemanticSearchResponse,
    Error,
    { query: string; top_k?: number; similarity_threshold?: number }
  >({
    mutationFn: (body) =>
      apiClient.post<SemanticSearchResponse>(
        `/knowledge-bases/${kbId}/search`,
        body,
      ),
  })
}
