/** TaskKanban — Kanban board view grouping tasks by status column. */

import {
  Loader2,
  AlertCircle,
  Plus,
  RefreshCw,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { TaskCard, STATUS_CONFIG } from './TaskCard'
import type { TaskResponse, TaskStatus } from '@/types/task'

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskKanbanProps {
  data: Record<string, TaskResponse[]> | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
  onRetry: () => void
}

// ── Columns ────────────────────────────────────────────────────────────────

const KANBAN_COLUMNS: TaskStatus[] = ['todo', 'in_progress', 'review', 'done', 'archived']

const COLUMN_LABELS: Record<TaskStatus, string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  review: 'Review',
  done: 'Done',
  archived: 'Archived',
}

// ── Component ──────────────────────────────────────────────────────────────

export function TaskKanban({ data, isLoading, isError, error, onRetry }: TaskKanbanProps) {
  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
        <AlertCircle size={32} className="text-red-400" />
        <div>
          <p className="text-base font-medium text-red-700 dark:text-red-300">
            Failed to load board
          </p>
          <p className="mt-1 text-sm text-red-500">
            {error?.message ?? 'An unexpected error occurred.'}
          </p>
        </div>
        <button
          onClick={onRetry}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
        >
          <RefreshCw size={14} className="mr-1.5 inline" />
          Retry
        </button>
      </div>
    )
  }

  // ── Empty (no data at all) ───────────────────────────────────────────────
  const hasAnyTasks = data && Object.values(data).some((arr) => arr.length > 0)

  if (!hasAnyTasks) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-16 dark:border-surface-700 dark:bg-surface-900/50">
        <h3 className="mb-1 text-base font-semibold text-surface-900 dark:text-white">
          No tasks yet
        </h3>
        <p className="mb-4 text-sm text-surface-500">
          Create your first task to get started.
        </p>
        <Link
          to="/tasks/new"
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
        >
          <Plus size={14} />
          New Task
        </Link>
      </div>
    )
  }

  // ── Board ────────────────────────────────────────────────────────────────
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {KANBAN_COLUMNS.map((statusKey) => {
        const tasks = data?.[statusKey] ?? []
        const cfg = STATUS_CONFIG[statusKey]
        return (
          <div
            key={statusKey}
            className="flex min-w-[280px] max-w-[320px] flex-1 flex-col"
          >
            {/* Column header */}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={cn('h-2.5 w-2.5 rounded-full', cfg.dot)} />
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                  {COLUMN_LABELS[statusKey]}
                </h3>
                <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[11px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                  {tasks.length}
                </span>
              </div>
            </div>

            {/* Tasks */}
            <div className="flex flex-col gap-2">
              {tasks.length === 0 ? (
                <div className="rounded-lg border border-dashed border-surface-300 p-4 text-center text-xs text-surface-400 dark:border-surface-700">
                  No tasks
                </div>
              ) : (
                tasks.map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
