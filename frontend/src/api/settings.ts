/** Settings — TanStack Query hooks for user settings, API providers, sessions. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  UserSettingsResponse,
  UserSettingsUpdate,
  ApiProviderResponse,
  ApiProviderCreate,
  ApiProviderUpdate,
  ApiProviderListResponse,
  UserSessionListResponse,
  PasswordChangeRequest,
  SettingsExportResponse,
  SettingsImport,
} from '@/types/settings'

// ── Query key factory ────────────────────────────────────────────────────────

export const settingsKeys = {
  all: ['settings'] as const,
  settings: () => [...settingsKeys.all, 'user'] as const,
  providers: () => [...settingsKeys.all, 'providers'] as const,
  sessions: () => [...settingsKeys.all, 'sessions'] as const,
  export: () => [...settingsKeys.all, 'export'] as const,
}

// ── User Settings ────────────────────────────────────────────────────────────

export function useSettings() {
  return useQuery<UserSettingsResponse>({
    queryKey: settingsKeys.settings(),
    queryFn: () => apiClient.get<UserSettingsResponse>('/settings'),
    staleTime: 60_000,
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation<UserSettingsResponse, Error, UserSettingsUpdate>({
    mutationFn: (body) => apiClient.patch<UserSettingsResponse>('/settings', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.settings() })
    },
  })
}

export function useResetSettings() {
  const queryClient = useQueryClient()
  return useMutation<UserSettingsResponse, Error, string | undefined>({
    mutationFn: (category) => {
      const qs = category ? `?category=${encodeURIComponent(category)}` : ''
      return apiClient.post<UserSettingsResponse>(`/settings/reset${qs}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.settings() })
    },
  })
}

// ── API Providers ────────────────────────────────────────────────────────────

export function useProviders() {
  return useQuery<ApiProviderListResponse>({
    queryKey: settingsKeys.providers(),
    queryFn: () => apiClient.get<ApiProviderListResponse>('/settings/providers'),
    staleTime: 30_000,
  })
}

export function useAddProvider() {
  const queryClient = useQueryClient()
  return useMutation<ApiProviderResponse, Error, ApiProviderCreate>({
    mutationFn: (body) =>
      apiClient.post<ApiProviderResponse>('/settings/providers', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.providers() })
    },
  })
}

export function useUpdateProvider() {
  const queryClient = useQueryClient()
  return useMutation<ApiProviderResponse, Error, { id: string; body: ApiProviderUpdate }>({
    mutationFn: ({ id, body }) =>
      apiClient.patch<ApiProviderResponse>(`/settings/providers/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.providers() })
    },
  })
}

export function useDeleteProvider() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiClient.delete(`/settings/providers/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.providers() })
    },
  })
}

export function useValidateProvider() {
  const queryClient = useQueryClient()
  return useMutation<
    { valid: boolean; provider?: string; error?: string },
    Error,
    string
  >({
    mutationFn: (id) =>
      apiClient.post<{ valid: boolean; provider?: string; error?: string }>(
        `/settings/providers/${id}/validate`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.providers() })
    },
  })
}

// ── Sessions ─────────────────────────────────────────────────────────────────

export function useSessions() {
  return useQuery<UserSessionListResponse>({
    queryKey: settingsKeys.sessions(),
    queryFn: () => apiClient.get<UserSessionListResponse>('/settings/sessions'),
    staleTime: 15_000,
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiClient.delete(`/settings/sessions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.sessions() })
    },
  })
}

export function useRevokeAllOtherSessions() {
  const queryClient = useQueryClient()
  return useMutation<{ revoked: number }, Error, void>({
    mutationFn: () =>
      apiClient.delete<{ revoked: number }>('/settings/sessions'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.sessions() })
    },
  })
}

// ── Password ─────────────────────────────────────────────────────────────────

export function useChangePassword() {
  return useMutation<{ message: string }, Error, PasswordChangeRequest>({
    mutationFn: (body) =>
      apiClient.post<{ message: string }>('/settings/change-password', body),
  })
}

// ── Import / Export ──────────────────────────────────────────────────────────

export function useExportSettings() {
  return useQuery<SettingsExportResponse>({
    queryKey: settingsKeys.export(),
    queryFn: () => apiClient.get<SettingsExportResponse>('/settings/export'),
    staleTime: 30_000,
  })
}

export function useImportSettings() {
  const queryClient = useQueryClient()
  return useMutation<UserSettingsResponse, Error, SettingsImport>({
    mutationFn: (body) =>
      apiClient.post<UserSettingsResponse>('/settings/import', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}
