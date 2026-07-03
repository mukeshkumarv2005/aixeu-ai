/** AISummaryWidget — On-demand AI work summary for the dashboard.
 *
 * States: idle (button visible), loading (spinner), error (message),
 *         data (summary text displayed inline with a regenerate option).
 */

import { useCallback, useState } from 'react'
import {
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { useAISummary } from '@/api/task-ai'

// ── Component ──────────────────────────────────────────────────────────────

export function AISummaryWidget() {
  const summaryMutation = useAISummary()
  const [summary, setSummary] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = useCallback(async () => {
    setError(null)
    try {
      const res = await summaryMutation.mutateAsync({})
      setSummary(res.summary)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to generate summary.')
    }
  }, [summaryMutation])

  const hasData = summary && !error

  return (
    <div className="rounded-xl border border-primary-200 bg-white dark:border-primary-900/30 dark:bg-surface-950">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-primary-100 px-4 py-3 dark:border-primary-900/20">
        <div className="rounded-lg bg-primary-100 p-1.5 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
          <FileText size={16} />
        </div>
        <h3 className="flex-1 text-sm font-semibold text-surface-900 dark:text-white">
          Work Summary
        </h3>
        {hasData && (
          <span className="text-[10px] text-surface-400">AI-generated</span>
        )}
      </div>

      {/* Body */}
      <div className="p-4">
        {hasData ? (
          /* Data state — summary text displayed */
          <div className="space-y-3">
            <p className="text-sm leading-relaxed text-surface-700 dark:text-surface-300">
              {summary}
            </p>
            <button
              onClick={handleGenerate}
              disabled={summaryMutation.isPending}
              className="flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:text-primary-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-primary-400 dark:hover:text-primary-300 transition-colors"
            >
              {summaryMutation.isPending ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <RefreshCw size={12} />
              )}
              {summaryMutation.isPending ? 'Regenerating…' : 'Regenerate'}
            </button>
          </div>
        ) : (
          /* Idle or error state */
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <div className="rounded-full bg-primary-50 p-3 dark:bg-primary-900/20">
              <Sparkles size={24} className="text-primary-400" />
            </div>

            {error ? (
              /* Error */
              <div className="space-y-2">
                <p className="text-sm text-red-500">{error}</p>
                <button
                  onClick={handleGenerate}
                  className="text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  Try again
                </button>
              </div>
            ) : (
              /* Idle */
              <>
                <p className="text-sm text-surface-500">
                  Generate an AI summary of your recent work activity.
                </p>
                <button
                  onClick={handleGenerate}
                  disabled={summaryMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {summaryMutation.isPending ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Sparkles size={14} />
                  )}
                  {summaryMutation.isPending
                    ? 'Generating…'
                    : 'Generate Summary'}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
