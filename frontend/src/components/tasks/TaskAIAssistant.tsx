/** TaskAIAssistant — AI-powered actions for a single task detail view.
 *
 * Provides one-click buttons for:
 *  - Effort estimation
 *  - Priority / due-date suggestion
 *  - Subtask generation
 *
 * Each action calls the corresponding backend mutation and shows the result
 * inline below the button. States: idle, loading, result, error.
 */

import { useState } from 'react'
import {
  Clock,
  ListChecks,
  ArrowUpDown,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Brain,
} from 'lucide-react'
import {
  useAIEstimateEffort,
  useAIPrioritySuggestion,
  useAISubtasks,
} from '@/api/task-ai'
import type {
  AIEffortEstimateResponse,
  AIPrioritySuggestionResponse,
  AISubtaskItem,
} from '@/types/task-ai'

// ── Props ─────────────────────────────────────────────────────────────────────

export interface TaskAIAssistantProps {
  taskId: string
  taskTitle: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export function TaskAIAssistant({ taskId, taskTitle: _taskTitle }: TaskAIAssistantProps) {
  const [expanded, setExpanded] = useState(false)

  const estimateMutation = useAIEstimateEffort()
  const priorityMutation = useAIPrioritySuggestion()
  const subtaskMutation = useAISubtasks()

  const [estimateResult, setEstimateResult] =
    useState<AIEffortEstimateResponse | null>(null)
  const [priorityResult, setPriorityResult] =
    useState<AIPrioritySuggestionResponse | null>(null)
  const [subtaskResult, setSubtaskResult] = useState<AISubtaskItem[] | null>(null)

  const [estimateError, setEstimateError] = useState<string | null>(null)
  const [priorityError, setPriorityError] = useState<string | null>(null)
  const [subtaskError, setSubtaskError] = useState<string | null>(null)

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleEstimate = async () => {
    setEstimateError(null)
    setEstimateResult(null)
    try {
      const res = await estimateMutation.mutateAsync(taskId)
      setEstimateResult(res)
    } catch (err: any) {
      setEstimateError(err?.message ?? 'Failed to estimate effort.')
    }
  }

  const handleSuggestPriority = async () => {
    setPriorityError(null)
    setPriorityResult(null)
    try {
      const res = await priorityMutation.mutateAsync(taskId)
      setPriorityResult(res)
    } catch (err: any) {
      setPriorityError(err?.message ?? 'Failed to suggest priority.')
    }
  }

  const handleGenerateSubtasks = async () => {
    setSubtaskError(null)
    setSubtaskResult(null)
    try {
      const res = await subtaskMutation.mutateAsync({
        task_id: taskId,
        count: 5,
      })
      setSubtaskResult(res.subtasks)
    } catch (err: any) {
      setSubtaskError(err?.message ?? 'Failed to generate subtasks.')
    }
  }

  // ── Loading helpers ───────────────────────────────────────────────────────

  const estimating = estimateMutation.isPending
  const suggesting = priorityMutation.isPending
  const generating = subtaskMutation.isPending
  const anyLoading = estimating || suggesting || generating

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="rounded-xl border border-primary-200 bg-white p-4 dark:border-primary-900/30 dark:bg-surface-950">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2"
      >
        <Brain size={16} className="shrink-0 text-primary-500" />
        <h3 className="flex-1 text-left text-sm font-semibold text-surface-900 dark:text-white">
          AI Assistant
        </h3>
        {anyLoading ? (
          <Loader2 size={14} className="animate-spin text-primary-500" />
        ) : expanded ? (
          <ChevronUp size={14} className="text-surface-400" />
        ) : (
          <ChevronDown size={14} className="text-surface-400" />
        )}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {/* ── Estimate Effort ───────────────────────────────────────────── */}
          <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 dark:border-surface-700 dark:bg-surface-900">
            <button
              onClick={handleEstimate}
              disabled={estimating}
              className="flex w-full items-center gap-2 text-left text-sm font-medium text-surface-700 hover:text-surface-900 dark:text-surface-300 dark:hover:text-white disabled:opacity-60"
            >
              <Clock size={14} className="text-blue-500" />
              <span className="flex-1">Estimate effort</span>
              {estimating && (
                <Loader2 size={14} className="animate-spin text-blue-500" />
              )}
              {estimateResult && !estimating && (
                <span className="text-xs text-blue-600 dark:text-blue-400">
                  {estimateResult.estimated_minutes} min
                </span>
              )}
            </button>

            {/* Result detail */}
            {estimateResult && !estimating && (
              <div className="mt-2 text-xs text-surface-600 dark:text-surface-400">
                <div className="flex items-center gap-1">
                  <CheckCircle2 size={11} className="text-green-500" />
                  <span className="font-medium">{estimateResult.estimated_minutes} minutes</span>
                  <span className="text-surface-400">— {estimateResult.confidence} confidence</span>
                </div>
                {estimateResult.reasoning && (
                  <p className="mt-1 text-surface-500">{estimateResult.reasoning}</p>
                )}
              </div>
            )}

            {/* Error */}
            {estimateError && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-red-500">
                <AlertCircle size={11} className="mt-0.5 shrink-0" />
                <span>{estimateError}</span>
              </div>
            )}
          </div>

          {/* ── Suggest Priority ──────────────────────────────────────────── */}
          <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 dark:border-surface-700 dark:bg-surface-900">
            <button
              onClick={handleSuggestPriority}
              disabled={suggesting}
              className="flex w-full items-center gap-2 text-left text-sm font-medium text-surface-700 hover:text-surface-900 dark:text-surface-300 dark:hover:text-white disabled:opacity-60"
            >
              <ArrowUpDown size={14} className="text-amber-500" />
              <span className="flex-1">Suggest priority &amp; due date</span>
              {suggesting && (
                <Loader2 size={14} className="animate-spin text-amber-500" />
              )}
              {priorityResult && !suggesting && (
                <span className="text-xs capitalize text-amber-600 dark:text-amber-400">
                  {priorityResult.priority}
                </span>
              )}
            </button>

            {/* Result detail */}
            {priorityResult && !suggesting && (
              <div className="mt-2 text-xs text-surface-600 dark:text-surface-400">
                <div className="flex items-center gap-1">
                  <CheckCircle2 size={11} className="text-green-500" />
                  <span className="font-medium capitalize">{priorityResult.priority}</span>
                  {priorityResult.due_date && (
                    <>
                      <span className="text-surface-400">·</span>
                      <span>Due {new Date(priorityResult.due_date).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
                {priorityResult.reasoning && (
                  <p className="mt-1 text-surface-500">{priorityResult.reasoning}</p>
                )}
              </div>
            )}

            {/* Error */}
            {priorityError && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-red-500">
                <AlertCircle size={11} className="mt-0.5 shrink-0" />
                <span>{priorityError}</span>
              </div>
            )}
          </div>

          {/* ── Generate Subtasks ─────────────────────────────────────────── */}
          <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 dark:border-surface-700 dark:bg-surface-900">
            <button
              onClick={handleGenerateSubtasks}
              disabled={generating}
              className="flex w-full items-center gap-2 text-left text-sm font-medium text-surface-700 hover:text-surface-900 dark:text-surface-300 dark:hover:text-white disabled:opacity-60"
            >
              <ListChecks size={14} className="text-purple-500" />
              <span className="flex-1">Generate subtasks</span>
              {generating && (
                <Loader2 size={14} className="animate-spin text-purple-500" />
              )}
              {subtaskResult && !generating && (
                <span className="text-xs text-purple-600 dark:text-purple-400">
                  {subtaskResult.length} subtasks
                </span>
              )}
            </button>

            {/* Result detail */}
            {subtaskResult && !generating && subtaskResult.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {subtaskResult.map((sub, idx) => (
                  <div
                    key={idx}
                    className="rounded-md bg-white px-2.5 py-1.5 text-xs shadow-sm dark:bg-surface-950"
                  >
                    <p className="font-medium text-surface-800 dark:text-surface-200">
                      {idx + 1}. {sub.title}
                    </p>
                    {sub.description && (
                      <p className="mt-0.5 text-surface-500">
                        {sub.description}
                      </p>
                    )}
                    {sub.estimated_minutes && (
                      <p className="mt-0.5 text-surface-400">
                        ~{sub.estimated_minutes} min
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {subtaskResult && !generating && subtaskResult.length === 0 && (
              <p className="mt-2 text-xs text-surface-500">
                AI determined no subtasks are needed.
              </p>
            )}

            {/* Error */}
            {subtaskError && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-red-500">
                <AlertCircle size={11} className="mt-0.5 shrink-0" />
                <span>{subtaskError}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
