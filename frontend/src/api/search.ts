/** Global Search — TanStack Query hooks for all search endpoints. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  SearchResponse,
  SavedSearchResponse,
  SavedSearchCreate,
  SavedSearchUpdate,
  RecentSearchResponse,
} from '@/types/search'

// ── Query key factory ────────────────────────────────────────────────────

export const searchKeys = {
  all: ['search'] as const,
  results: (q: string, filters: Record<string, unknown>) =>
    [searchKeys.all, 'results', q, filters] as const,
  saved: () => [...searchKeys.all, 'saved'] as const,
  recent: () => [...searchKeys.all, 'recent'] as const,
}

// ── Global search ─────────────────────────────────────────────────────────

interface SearchParams {
  q: string
  entity_types?: string
  status?: string
  priority?: string
  kb_id?: string
  date_from?: string
  date_to?: string
  offset?: number
  limit?: number
}

export function useGlobalSearch(params: SearchParams) {
  const { q, ...rest } = params
  const filters = { ...rest }

  const urlParams = new URLSearchParams()
  if (q) urlParams.set('q', q)
  if (rest.entity_types) urlParams.set('entity_types', rest.entity_types)
  if (rest.status) urlParams.set('status', rest.status)
  if (rest.priority) urlParams.set('priority', rest.priority)
  if (rest.kb_id) urlParams.set('kb_id', rest.kb_id)
  if (rest.date_from) urlParams.set('date_from', rest.date_from)
  if (rest.date_to) urlParams.set('date_to', rest.date_to)
  if (rest.offset) urlParams.set('offset', String(rest.offset))
  if (rest.limit) urlParams.set('limit', String(rest.limit))
  const qs = urlParams.toString()

  return useQuery<SearchResponse>({
    queryKey: searchKeys.results(q, filters),
    queryFn: () =>
      apiClient.get<SearchResponse>(`/search${qs ? `?${qs}` : ''}`),
    enabled: q.length > 0,
    staleTime: 15_000,
  })
}

// ── Saved searches ────────────────────────────────────────────────────────

export function useSavedSearches() {
  return useQuery<SavedSearchResponse[]>({
    queryKey: searchKeys.saved(),
    queryFn: () => apiClient.get<SavedSearchResponse[]>('/search/saved'),
    staleTime: 60_000,
  })
}

export function useSaveSearch() {
  const queryClient = useQueryClient()
  return useMutation<SavedSearchResponse, Error, SavedSearchCreate>({
    mutationFn: (body) =>
      apiClient.post<SavedSearchResponse>('/search/saved', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: searchKeys.saved() })
    },
  })
}

export function useUpdateSavedSearch() {
  const queryClient = useQueryClient()
  return useMutation<
    SavedSearchResponse,
    Error,
    { searchId: string; body: SavedSearchUpdate }
  >({
    mutationFn: ({ searchId, body }) =>
      apiClient.patch<SavedSearchResponse>(`/search/saved/${searchId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: searchKeys.saved() })
    },
  })
}

export function useDeleteSavedSearch() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (searchId) => apiClient.delete(`/search/saved/${searchId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: searchKeys.saved() })
    },
  })
}

// ── Recent searches ───────────────────────────────────────────────────────

export function useRecentSearches() {
  return useQuery<RecentSearchResponse[]>({
    queryKey: searchKeys.recent(),
    queryFn: () => apiClient.get<RecentSearchResponse[]>('/search/recent'),
    staleTime: 30_000,
  })
}

export function useRecordRecentSearch() {
  const queryClient = useQueryClient()
  return useMutation<RecentSearchResponse, Error, string>({
    mutationFn: (query) =>
      apiClient.post<RecentSearchResponse>('/search/recent', { query }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: searchKeys.recent() })
    },
  })
}

export function useClearRecentSearches() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, void>({
    mutationFn: () => apiClient.delete('/search/recent'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: searchKeys.recent() })
    },
  })
}
