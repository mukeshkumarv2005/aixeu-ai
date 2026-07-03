/** AI Task Assistant — TanStack Query hooks for all AI-powered task endpoints. */

import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type {
  AITaskGenerationRequest,
  AITaskGenerationResponse,
  AISubtaskRequest,
  AISubtaskResponse,
  AIEffortEstimateResponse,
  AIPrioritySuggestionResponse,
  AISummaryRequest,
  AISummaryResponse,
  AIConvertChatRequest,
  AIConvertChatResponse,
  AIConvertDocumentRequest,
  AIConvertDocumentResponse,
  AINextActionsResponse,
} from '@/types/task-ai'

// ── Query key factory ────────────────────────────────────────────────────────

export const aiTaskKeys = {
  all: ['ai-tasks'] as const,
  nextActions: () => [...aiTaskKeys.all, 'next-actions'] as const,
}

// ── Generate tasks from natural language ─────────────────────────────────────

export function useAITaskGenerate() {
  return useMutation<AITaskGenerationResponse, Error, AITaskGenerationRequest>({
    mutationFn: (body) =>
      apiClient.post<AITaskGenerationResponse>('/ai/tasks/generate', body),
  })
}

// ── Generate subtasks ────────────────────────────────────────────────────────

export function useAISubtasks() {
  return useMutation<AISubtaskResponse, Error, AISubtaskRequest>({
    mutationFn: (body) =>
      apiClient.post<AISubtaskResponse>('/ai/tasks/subtasks', body),
  })
}

// ── Estimate effort ──────────────────────────────────────────────────────────

export function useAIEstimateEffort() {
  return useMutation<AIEffortEstimateResponse, Error, string>({
    mutationFn: (taskId) =>
      apiClient.post<AIEffortEstimateResponse>(`/ai/tasks/${taskId}/estimate`),
  })
}

// ── Suggest priority and due date ────────────────────────────────────────────

export function useAIPrioritySuggestion() {
  return useMutation<AIPrioritySuggestionResponse, Error, string>({
    mutationFn: (taskId) =>
      apiClient.post<AIPrioritySuggestionResponse>(
        `/ai/tasks/${taskId}/suggest-priority`,
      ),
  })
}

// ── Summarize completed work ─────────────────────────────────────────────────

export function useAISummary() {
  return useMutation<AISummaryResponse, Error, AISummaryRequest>({
    mutationFn: (body) =>
      apiClient.post<AISummaryResponse>('/ai/tasks/summary', body),
  })
}

// ── Convert chat to task ─────────────────────────────────────────────────────

export function useAIConvertChat() {
  return useMutation<AIConvertChatResponse, Error, AIConvertChatRequest>({
    mutationFn: (body) =>
      apiClient.post<AIConvertChatResponse>('/ai/tasks/convert-chat', body),
  })
}

// ── Convert document to task ─────────────────────────────────────────────────

export function useAIConvertDocument() {
  return useMutation<AIConvertDocumentResponse, Error, AIConvertDocumentRequest>({
    mutationFn: (body) =>
      apiClient.post<AIConvertDocumentResponse>(
        '/ai/tasks/convert-document',
        body,
      ),
  })
}

// ── Get next-action suggestions ──────────────────────────────────────────────

export function useAINextActions() {
  return useQuery<AINextActionsResponse>({
    queryKey: aiTaskKeys.nextActions(),
    queryFn: () =>
      apiClient.get<AINextActionsResponse>('/ai/tasks/next-actions'),
    staleTime: 60_000,
  })
}
