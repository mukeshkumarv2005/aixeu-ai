/** Document intelligence API hooks — TanStack Query wrappers
 * around the ``/api/v1/documents`` endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  DocumentMetadata,
  DocumentChunkList,
  DocumentAnalysis,
  DocumentStatus,
  DocumentProcessRequest,
} from '@/types/documents'

/** Get document processing status. */
export function useDocumentStatus(fileId: string) {
  return useQuery<DocumentStatus>({
    queryKey: ['documents', fileId, 'status'],
    queryFn: () => apiClient.get<DocumentStatus>(`/documents/${fileId}/status`),
    enabled: !!fileId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (
        data &&
        (data.processing_status === 'processing' ||
          data.processing_status === 'queued' ||
          data.processing_status === 'pending')
      ) {
        return 2000
      }
      return false
    },
  })
}

/** Get document metadata. */
export function useDocumentMetadata(fileId: string) {
  return useQuery<DocumentMetadata>({
    queryKey: ['documents', fileId, 'metadata'],
    queryFn: () => apiClient.get<DocumentMetadata>(`/documents/${fileId}/metadata`),
    enabled: !!fileId,
  })
}

/** Get paginated document chunks. */
export function useDocumentChunks(
  fileId: string,
  offset = 0,
  limit = 50,
) {
  return useQuery<DocumentChunkList>({
    queryKey: ['documents', fileId, 'chunks', offset, limit],
    queryFn: () =>
      apiClient.get<DocumentChunkList>(
        `/documents/${fileId}/chunks?offset=${offset}&limit=${limit}`,
      ),
    enabled: !!fileId,
  })
}

/** Get document AI analysis. */
export function useDocumentAnalysis(fileId: string) {
  return useQuery<DocumentAnalysis>({
    queryKey: ['documents', fileId, 'analysis'],
    queryFn: () => apiClient.get<DocumentAnalysis>(`/documents/${fileId}/analysis`),
    enabled: !!fileId,
  })
}

/** Trigger (or re-trigger) document processing. */
export function useProcessDocument(fileId: string) {
  const queryClient = useQueryClient()

  return useMutation<DocumentStatus, Error, DocumentProcessRequest | undefined>({
    mutationFn: (params) =>
      apiClient.post<DocumentStatus>(`/documents/${fileId}/process`, params ?? {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', fileId] })
    },
  })
}
