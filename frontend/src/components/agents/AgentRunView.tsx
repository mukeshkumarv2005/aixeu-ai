/** AgentRunView — run history list and run detail display. */

import { useState } from 'react'
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Timer,
  DollarSign,
  FileText,
  ChevronDown,
  ChevronUp,
  StopCircle,
  AlertTriangle,
  Send,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentRunResponse, AgentRunListResponse } from '@/types/agent'

// ── Status config ──────────────────────────────────────────────────────────

const RUN_STATUS_CONFIG: Record<
  string,
  { label: string; icon: typeof Play; color: string; bg: string }
> = {
  queued: {
    label: 'Queued',
    icon: Clock,
    color: 'text-surface-500',
    bg: 'bg-surface-100 dark:bg-surface-800',
  },
  running: {
    label: 'Running',
    icon: Timer,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-100 dark:bg-blue-900/20',
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle2,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-100 dark:bg-green-900/20',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-100 dark:bg-red-900/20',
  },
  cancelled: {
    label: 'Cancelled',
    icon: StopCircle,
    color: 'text-surface-500',
    bg: 'bg-surface-100 dark:bg-surface-800',
  },
  timed_out: {
    label: 'Timed Out',
    icon: AlertTriangle,
    color: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-100 dark:bg-yellow-900/20',
  },
}

function getStatusConfig(status: string) {
  return RUN_STATUS_CONFIG[status] ?? {
    label: status,
    icon: AlertCircle,
    color: 'text-surface-500',
    bg: 'bg-surface-100 dark:bg-surface-800',
  }
}

// ── Utility ────────────────────────────────────────────────────────────────

function formatDuration(started: string | null, finished: string | null): string {
  if (!started) return '—'
  const start = new Date(started).getTime()
  const end = finished ? new Date(finished).getTime() : Date.now()
  const ms = end - start
  if (ms < 1_000) return '<1s'
  if (ms < 60_000) return `${Math.round(ms / 1_000)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1_000)}s`
}

function formatCost(cost: number | null): string {
  if (cost === null || cost === undefined) return '—'
  if (cost < 0.01) return '<$0.01'
  return `$${cost.toFixed(2)}`
}

// ── Props ──────────────────────────────────────────────────────────────────

interface AgentRunListProps {
  /** The paginated runs data (or undefined while loading). */
  data?: AgentRunListResponse
  /** True while query is loading. */
  isLoading: boolean
  /** True if query errored. */
  isError: boolean
  /** Error object from query. */
  error?: Error | null
  /** Called to refetch. */
  onRefetch: () => void
  /** Called when user wants to cancel a run. */
  onCancelRun?: (runId: string) => void
  /** Whether a cancel mutation is in flight. */
  isCancelling?: boolean
}

// ── Run list component ─────────────────────────────────────────────────────

export function AgentRunList({
  data,
  isLoading,
  isError,
  error,
  onRefetch,
  onCancelRun,
  isCancelling,
}: AgentRunListProps) {
  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900/30 dark:bg-red-950/20">
        <AlertCircle size={24} className="text-red-400" />
        <p className="text-sm text-red-600 dark:text-red-400">
          {error?.message ?? 'Failed to load run history.'}
        </p>
        <button
          onClick={onRefetch}
          className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      </div>
    )
  }

  // ── Empty ──────────────────────────────────────────────────────────────
  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300 p-8 dark:border-surface-700">
        <Play size={32} className="text-surface-300 dark:text-surface-600" />
        <p className="text-sm font-medium text-surface-500 dark:text-surface-400">
          No runs yet
        </p>
        <p className="text-xs text-surface-400 dark:text-surface-500 text-center max-w-sm">
          Execute this agent to see its run history here.
        </p>
      </div>
    )
  }

  // ── Runs list ──────────────────────────────────────────────────────────
  return (
    <div className="space-y-2">
      {data.items.map((run) => (
        <RunRow
          key={run.id}
          run={run}
          onCancel={onCancelRun}
          isCancelling={isCancelling}
        />
      ))}
    </div>
  )
}

// ── Individual run row ─────────────────────────────────────────────────────

interface RunRowProps {
  run: AgentRunResponse
  onCancel?: (runId: string) => void
  isCancelling?: boolean
}

function RunRow({ run, onCancel, isCancelling }: RunRowProps) {
  const [expanded, setExpanded] = useState(false)
  const cfg = getStatusConfig(run.status)
  const StatusIcon = cfg.icon

  const canCancel = run.status === 'queued' || run.status === 'running'

  return (
    <div
      className={cn(
        'rounded-xl border bg-white transition-colors dark:bg-surface-950',
        expanded
          ? 'border-surface-300 dark:border-surface-700'
          : 'border-surface-200 dark:border-surface-800',
      )}
    >
      {/* ── Header row ───────────────────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        {/* Status icon */}
        <span className={cn('shrink-0', cfg.color)}>
          <StatusIcon size={16} />
        </span>

        {/* Status + Input */}
        <div className="min-w-0 flex-1">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
              cfg.bg,
              cfg.color,
            )}
          >
            {cfg.label}
          </span>
          {run.input_text && (
            <p className="mt-1 truncate text-xs text-surface-500 dark:text-surface-400">
              {run.input_text}
            </p>
          )}
        </div>

        {/* Duration */}
        <span className="shrink-0 text-[11px] text-surface-400">
          {formatDuration(run.started_at, run.finished_at)}
        </span>

        {/* Cost */}
        <span className="shrink-0 text-[11px] text-surface-400">
          {formatCost(run.cost)}
        </span>

        {/* Cancel button */}
        {canCancel && onCancel && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onCancel(run.id)
            }}
            disabled={isCancelling}
            className="shrink-0 rounded-lg border border-surface-200 bg-white px-2 py-1 text-[10px] font-medium text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 disabled:opacity-50 transition-colors"
            title="Cancel run"
          >
            {isCancelling ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              'Cancel'
            )}
          </button>
        )}

        {/* Expand */}
        {expanded ? (
          <ChevronUp size={14} className="shrink-0 text-surface-300" />
        ) : (
          <ChevronDown size={14} className="shrink-0 text-surface-300" />
        )}
      </button>

      {/* ── Expanded detail ──────────────────────────────── */}
      {expanded && (
        <div className="border-t border-surface-200 px-4 py-3 dark:border-surface-800 space-y-3">
          {/* Timestamps */}
          <div className="flex flex-wrap gap-4 text-[11px] text-surface-400">
            {run.started_at && (
              <span className="flex items-center gap-1">
                <Clock size={11} />
                Started {new Date(run.started_at).toLocaleString()}
              </span>
            )}
            {run.finished_at && (
              <span className="flex items-center gap-1">
                <CheckCircle2 size={11} />
                Finished {new Date(run.finished_at).toLocaleString()}
              </span>
            )}
            {run.cost !== null && (
              <span className="flex items-center gap-1">
                <DollarSign size={11} />
                Cost: {formatCost(run.cost)}
              </span>
            )}
          </div>

          {/* Input */}
          {run.input_text && (
            <div>
              <h4 className="mb-1 text-[11px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider flex items-center gap-1">
                <Send size={11} />
                Input
              </h4>
              <div className="rounded-lg bg-surface-50 p-3 text-xs text-surface-700 dark:bg-surface-900 dark:text-surface-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                {run.input_text}
              </div>
            </div>
          )}

          {/* Result */}
          {run.result && (
            <div>
              <h4 className="mb-1 text-[11px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider flex items-center gap-1">
                <FileText size={11} />
                Result
              </h4>
              <div className="rounded-lg bg-surface-50 p-3 text-xs text-surface-700 dark:bg-surface-900 dark:text-surface-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                {run.result}
              </div>
            </div>
          )}

          {/* Error */}
          {run.error_message && (
            <div>
              <h4 className="mb-1 text-[11px] font-semibold text-red-500 uppercase tracking-wider flex items-center gap-1">
                <XCircle size={11} />
                Error
              </h4>
              <div className="rounded-lg bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/20 dark:text-red-400 whitespace-pre-wrap">
                {run.error_message}
              </div>
            </div>
          )}

          {/* Token usage */}
          {run.token_usage && Object.keys(run.token_usage).length > 0 && (
            <div>
              <h4 className="mb-1 text-[11px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider">
                Token Usage
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(run.token_usage).map(([key, value]) => (
                  <span
                    key={key}
                    className="rounded-md bg-surface-100 px-2 py-1 text-[11px] text-surface-600 dark:bg-surface-800 dark:text-surface-400"
                  >
                    {key.replace(/_/g, ' ')}: {String(value)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Export status config for reuse ─────────────────────────────────────────

export { RUN_STATUS_CONFIG, formatDuration, formatCost }
