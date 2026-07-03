/** AI Agents — TanStack Query hooks for all agent CRUD, runs, tools, templates. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  AgentResponse,
  AgentListResponse,
  AgentRunResponse,
  AgentRunListResponse,
  AgentRunExecuteRequest,
  AgentRunExecuteResponse,
  AgentToolResponse,
  AgentToolCreate,
  AgentToolUpdate,
  AgentTemplateResponse,
  AgentTemplateListResponse,
  AgentTemplateCreate,
  AgentTemplateUpdate,
  AgentCreate,
  AgentUpdate,
} from '@/types/agent'

// ── Query key factory ────────────────────────────────────────────────────────

export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...agentKeys.lists(), filters] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
  runs: () => [...agentKeys.all, 'runs'] as const,
  run: (runId: string) => [...agentKeys.runs(), runId] as const,
  agentRuns: (agentId: string) => [...agentKeys.all, 'agent-runs', agentId] as const,
  tools: () => [...agentKeys.all, 'tools'] as const,
  agentTools: (agentId: string) => [...agentKeys.tools(), agentId] as const,
  templates: () => [...agentKeys.all, 'templates'] as const,
  template: (id: string) => [...agentKeys.templates(), id] as const,
}

// ── Agent CRUD ───────────────────────────────────────────────────────────────

interface AgentListFilters extends Record<string, unknown> {
  search?: string
  offset?: number
  limit?: number
}

export function useAgents(filters: AgentListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.search) params.set('search', filters.search)
  if (filters.offset) params.set('offset', String(filters.offset))
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()

  return useQuery<AgentListResponse>({
    queryKey: agentKeys.list(filters),
    queryFn: () => apiClient.get<AgentListResponse>(`/agents${qs ? `?${qs}` : ''}`),
    staleTime: 30_000,
  })
}

export function useAgent(agentId: string | undefined) {
  return useQuery<AgentResponse>({
    queryKey: agentKeys.detail(agentId ?? ''),
    queryFn: () => apiClient.get<AgentResponse>(`/agents/${agentId}`),
    enabled: !!agentId,
    staleTime: 15_000,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation<AgentResponse, Error, AgentCreate>({
    mutationFn: (body) => apiClient.post<AgentResponse>('/agents', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() })
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()
  return useMutation<AgentResponse, Error, { agentId: string; body: AgentUpdate }>({
    mutationFn: ({ agentId, body }) =>
      apiClient.patch<AgentResponse>(`/agents/${agentId}`, body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(data.id) })
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() })
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (agentId) => apiClient.delete(`/agents/${agentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
    },
  })
}

// ── Agent Execution ──────────────────────────────────────────────────────────

export function useExecuteAgent() {
  const queryClient = useQueryClient()
  return useMutation<
    AgentRunExecuteResponse,
    Error,
    { agentId: string; body: AgentRunExecuteRequest }
  >({
    mutationFn: ({ agentId, body }) =>
      apiClient.post<AgentRunExecuteResponse>(`/agents/${agentId}/execute`, body),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({
        queryKey: agentKeys.agentRuns(vars.agentId),
      })
    },
  })
}

// ── Runs ─────────────────────────────────────────────────────────────────────

interface AgentRunFilters {
  status?: string
  offset?: number
  limit?: number
}

export function useAgentRuns(agentId: string | undefined, filters: AgentRunFilters = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.offset) params.set('offset', String(filters.offset))
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()

  return useQuery<AgentRunListResponse>({
    queryKey: [...agentKeys.agentRuns(agentId ?? ''), filters],
    queryFn: () =>
      apiClient.get<AgentRunListResponse>(
        `/agents/${agentId}/runs${qs ? `?${qs}` : ''}`,
      ),
    enabled: !!agentId,
    staleTime: 10_000,
  })
}

export function useAgentRun(runId: string | undefined) {
  return useQuery<AgentRunResponse>({
    queryKey: agentKeys.run(runId ?? ''),
    queryFn: () => apiClient.get<AgentRunResponse>(`/agents/runs/${runId}`),
    enabled: !!runId,
    staleTime: 15_000,
  })
}

export function useCancelRun() {
  const queryClient = useQueryClient()
  return useMutation<AgentRunResponse, Error, string>({
    mutationFn: (runId) =>
      apiClient.post<AgentRunResponse>(`/agents/runs/${runId}/cancel`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.runs() })
      queryClient.invalidateQueries({
        queryKey: agentKeys.agentRuns(data.agent_id),
      })
    },
  })
}

// ── Tools ────────────────────────────────────────────────────────────────────

export function useAgentTools(agentId: string | undefined) {
  return useQuery<AgentToolResponse[]>({
    queryKey: agentKeys.agentTools(agentId ?? ''),
    queryFn: () =>
      apiClient.get<AgentToolResponse[]>(`/agents/${agentId}/tools`),
    enabled: !!agentId,
    staleTime: 15_000,
  })
}

export function useAddTool() {
  const queryClient = useQueryClient()
  return useMutation<
    AgentToolResponse,
    Error,
    { agentId: string; body: AgentToolCreate }
  >({
    mutationFn: ({ agentId, body }) =>
      apiClient.post<AgentToolResponse>(`/agents/${agentId}/tools`, body),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({
        queryKey: agentKeys.agentTools(vars.agentId),
      })
    },
  })
}

export function useUpdateTool() {
  const queryClient = useQueryClient()
  return useMutation<
    AgentToolResponse,
    Error,
    { toolId: string; agentId: string; body: AgentToolUpdate }
  >({
    mutationFn: ({ toolId, body }) =>
      apiClient.patch<AgentToolResponse>(`/agents/tools/${toolId}`, body),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({
        queryKey: agentKeys.agentTools(vars.agentId),
      })
    },
  })
}

export function useRemoveTool() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, { toolId: string; agentId: string }>({
    mutationFn: ({ toolId }) => apiClient.delete(`/agents/tools/${toolId}`),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({
        queryKey: agentKeys.agentTools(vars.agentId),
      })
    },
  })
}

// ── Templates ────────────────────────────────────────────────────────────────

interface TemplateListFilters {
  category?: string
  include_builtin?: boolean
  offset?: number
  limit?: number
}

export function useTemplates(filters: TemplateListFilters = {}) {
  const params = new URLSearchParams()
  if (filters.category) params.set('category', filters.category)
  if (filters.include_builtin !== undefined)
    params.set('include_builtin', String(filters.include_builtin))
  if (filters.offset) params.set('offset', String(filters.offset))
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()

  return useQuery<AgentTemplateListResponse>({
    queryKey: [...agentKeys.templates(), filters],
    queryFn: () =>
      apiClient.get<AgentTemplateListResponse>(
        `/agents/templates${qs ? `?${qs}` : ''}`,
      ),
    staleTime: 60_000,
  })
}

export function useTemplate(templateId: string | undefined) {
  return useQuery<AgentTemplateResponse>({
    queryKey: agentKeys.template(templateId ?? ''),
    queryFn: () =>
      apiClient.get<AgentTemplateResponse>(`/agents/templates/${templateId}`),
    enabled: !!templateId,
    staleTime: 30_000,
  })
}

export function useCreateTemplate() {
  const queryClient = useQueryClient()
  return useMutation<AgentTemplateResponse, Error, AgentTemplateCreate>({
    mutationFn: (body) =>
      apiClient.post<AgentTemplateResponse>('/agents/templates', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.templates() })
    },
  })
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient()
  return useMutation<
    AgentTemplateResponse,
    Error,
    { templateId: string; body: AgentTemplateUpdate }
  >({
    mutationFn: ({ templateId, body }) =>
      apiClient.patch<AgentTemplateResponse>(
        `/agents/templates/${templateId}`,
        body,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.templates() })
    },
  })
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (templateId) =>
      apiClient.delete(`/agents/templates/${templateId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.templates() })
    },
  })
}

export function useCreateAgentFromTemplate() {
  const queryClient = useQueryClient()
  return useMutation<AgentResponse, Error, { templateId: string; name?: string }>({
    mutationFn: ({ templateId, name }) => {
      const params = name ? `?name=${encodeURIComponent(name)}` : ''
      return apiClient.post<AgentResponse>(
        `/agents/templates/${templateId}/create-agent${params}`,
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() })
    },
  })
}
