/** Token usage widget — live totals and a simple daily bar chart. */

import { useMemo } from 'react'
import { AlertCircle } from 'lucide-react'
import type { DailyTokenUsage } from '@/types/dashboard'

interface UsageWidgetProps {
  totalInputTokens: number
  totalOutputTokens: number
  totalMessages: number
  totalConversations: number
  storageTotalBytes: number
  storageTotalFiles: number
  dailyUsage: DailyTokenUsage[]
  loading?: boolean
  error?: string | null
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function UsageWidget({
  totalInputTokens,
  totalOutputTokens,
  totalMessages,
  totalConversations,
  storageTotalBytes,
  storageTotalFiles,
  dailyUsage,
  loading,
  error,
}: UsageWidgetProps) {
  const maxDaily = useMemo(
    () => Math.max(...dailyUsage.map((d) => d.input_tokens + d.output_tokens), 1),
    [dailyUsage],
  )

  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      {/* Header */}
      <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Usage Overview
        </h3>
      </div>

      <div className="p-4">
        {/* Loading */}
        {loading && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <div className="h-3 w-16 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-5 w-12 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <AlertCircle size={24} className="text-red-400" />
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        {/* Data */}
        {!loading && !error && (
          <>
            {/* Stat row */}
            <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Metric label="Input tokens" value={formatTokens(totalInputTokens)} color="text-primary-500" />
              <Metric label="Output tokens" value={formatTokens(totalOutputTokens)} color="text-accent-500" />
              <Metric label="Messages" value={String(totalMessages)} color="text-green-500" />
              <Metric label="Conversations" value={String(totalConversations)} color="text-amber-500" />
              <Metric label="Storage used" value={formatBytes(storageTotalBytes)} color="text-surface-500" />
              <Metric label="Files" value={String(storageTotalFiles)} color="text-surface-500" />
            </div>

            {/* Daily bar chart */}
            {dailyUsage.length > 0 && (
              <div>
                <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-surface-500">
                  Daily token usage
                </h4>
                <div className="flex items-end gap-1" style={{ height: 64 }}>
                  {dailyUsage.map((day) => {
                    const total = day.input_tokens + day.output_tokens
                    const heightPct = maxDaily > 0 ? (total / maxDaily) * 100 : 0
                    const dayLabel = new Date(day.date).toLocaleDateString(undefined, {
                      weekday: 'short',
                    })
                    return (
                      <div
                        key={day.date}
                        className="group relative flex flex-1 flex-col items-center"
                      >
                        <div
                          className="flex w-full max-w-[24px] flex-col-reverse rounded-t"
                          style={{ height: `${Math.max(heightPct, 2)}%` }}
                        >
                          <div
                            className="w-full rounded-t bg-primary-400 transition-colors hover:bg-primary-500"
                            style={{ height: `${(day.output_tokens / total) * 100}%` }}
                            title={`Output: ${formatTokens(day.output_tokens)}`}
                          />
                          <div
                            className="w-full bg-accent-400 transition-colors hover:bg-accent-500"
                            style={{ flex: 1 }}
                            title={`Input: ${formatTokens(day.input_tokens)}`}
                          />
                        </div>
                        <span className="mt-1 truncate text-[10px] text-surface-400">
                          {dayLabel}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

/** Inline metric display */
function Metric({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  return (
    <div>
      <p className="text-xs text-surface-500">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold ${color}`}>{value}</p>
    </div>
  )
}
