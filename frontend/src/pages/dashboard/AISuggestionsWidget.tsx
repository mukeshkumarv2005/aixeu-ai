/** AISuggestionsWidget — AI-predicted next actions for the dashboard.
 *
 * States: loading (skeleton), error, empty, data (list of suggestions).
 * Each suggestion is clickable — navigates to the source task if pinned,
 * or to task creation with a pre-filled draft.
 */

import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  Lightbulb,
  AlertCircle,
  Brain,
} from 'lucide-react'
import { useAINextActions } from '@/api/task-ai'
import type { AINextActionItem } from '@/types/task-ai'

// ── Priority config for visual styling ─────────────────────────────────────

const PRIORITY_BADGE: Record<string, { label: string; className: string }> = {
  high: {
    label: 'High',
    className:
      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  },
  medium: {
    label: 'Medium',
    className:
      'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  },
  low: {
    label: 'Low',
    className:
      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  },
}

function badgeForPriority(p: string) {
  return PRIORITY_BADGE[p] ?? PRIORITY_BADGE.medium
}

// ── Component ──────────────────────────────────────────────────────────────

export function AISuggestionsWidget() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useAINextActions()

  const suggestions = data?.actions ?? []

  const handleClick = (item: AINextActionItem) => {
    if (item.source_task_id) {
      navigate(`/tasks/${item.source_task_id}`)
    } else {
      // Navigate to task create — the user can flesh out the title
      navigate('/tasks/create')
    }
  }

  return (
    <div className="rounded-xl border border-primary-200 bg-white dark:border-primary-900/30 dark:bg-surface-950">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-primary-100 px-4 py-3 dark:border-primary-900/20">
        <div className="rounded-lg bg-primary-100 p-1.5 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
          <Brain size={16} />
        </div>
        <h3 className="flex-1 text-sm font-semibold text-surface-900 dark:text-white">
          AI Suggestions
        </h3>
        {data?.summary && (
          <span className="text-[10px] text-surface-400">AI-generated</span>
        )}
      </div>

      <div className="p-3">
        {/* Loading */}
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg px-2 py-2"
              >
                <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 w-2/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                  <div className="h-2.5 w-1/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <AlertCircle size={24} className="text-red-400" />
            <p className="text-sm text-red-500">
              {error instanceof Error
                ? error.message
                : 'Failed to load suggestions'}
            </p>
          </div>
        )}

        {/* Empty */}
        {!isLoading && !error && suggestions.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <Lightbulb size={24} className="text-surface-300 dark:text-surface-600" />
            <p className="text-sm text-surface-500">No suggestions yet</p>
            <p className="text-xs text-surface-400">
              AI suggestions appear as you create and complete tasks.
            </p>
          </div>
        )}

        {/* Data */}
        {!isLoading && !error && suggestions.length > 0 && (
          <div className="space-y-1">
            {suggestions.slice(0, 5).map((item, idx) => {
              const badge = badgeForPriority(item.priority)

              return (
                <button
                  key={idx}
                  onClick={() => handleClick(item)}
                  className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-primary-50/60 dark:hover:bg-primary-900/10"
                >
                  <div className="rounded-lg bg-primary-50 p-1.5 text-primary-500 dark:bg-primary-900/20 dark:text-primary-400">
                    <Sparkles size={14} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                        {item.title}
                      </p>
                      <span
                        className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${badge.className}`}
                      >
                        {badge.label}
                      </span>
                    </div>
                    {item.context && (
                      <p className="mt-0.5 truncate text-xs text-surface-400">
                        {item.context}
                      </p>
                    )}
                  </div>
                  <ArrowRight
                    size={14}
                    className="shrink-0 text-surface-300 dark:text-surface-600"
                  />
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
