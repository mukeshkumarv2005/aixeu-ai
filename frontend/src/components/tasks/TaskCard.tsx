/** TaskCard — card used in list view, kanban columns, and search results. */

import { Link } from 'react-router-dom'
import {
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle2,
  Archive,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TaskResponse, TaskStatus } from '@/types/task'

// ── Status config ──────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<TaskStatus, { label: string; bg: string; dot: string }> = {
  todo: {
    label: 'To Do',
    bg: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
    dot: 'bg-surface-400',
  },
  in_progress: {
    label: 'In Progress',
    bg: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
    dot: 'bg-blue-500',
  },
  review: {
    label: 'Review',
    bg: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
    dot: 'bg-yellow-500',
  },
  done: {
    label: 'Done',
    bg: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
    dot: 'bg-green-500',
  },
  archived: {
    label: 'Archived',
    bg: 'bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-500',
    dot: 'bg-surface-400',
  },
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string }> = {
  critical: { label: 'Critical', color: 'text-red-600 dark:text-red-400' },
  high: { label: 'High', color: 'text-orange-600 dark:text-orange-400' },
  medium: { label: 'Medium', color: 'text-yellow-600 dark:text-yellow-400' },
  low: { label: 'Low', color: 'text-surface-500 dark:text-surface-400' },
}

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskCardProps {
  task: TaskResponse
}

// ── Component ──────────────────────────────────────────────────────────────

export function TaskCard({ task }: TaskCardProps) {
  const status = task.status as TaskStatus
  const statusCfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.todo
  const priorityCfg = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium

  const isOverdue =
    task.due_date &&
    task.status !== 'done' &&
    task.status !== 'archived' &&
    new Date(task.due_date) < new Date()

  return (
    <Link
      to={`/tasks/${task.id}`}
      className={cn(
        'group block rounded-xl border bg-white p-4 shadow-sm transition-all hover:shadow-md dark:bg-surface-950',
        isOverdue
          ? 'border-red-200 dark:border-red-900/50'
          : 'border-surface-200 dark:border-surface-800',
      )}
    >
      {/* Title + Priority */}
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="line-clamp-2 text-sm font-semibold text-surface-900 dark:text-white">
          {task.title}
        </h3>
        <span className={cn('shrink-0 text-xs font-medium', priorityCfg.color)}>
          {priorityCfg.label}
        </span>
      </div>

      {/* Description preview */}
      {task.description && (
        <p className="mb-3 line-clamp-2 text-xs text-surface-500 dark:text-surface-400">
          {task.description}
        </p>
      )}

      {/* Labels */}
      {task.labels.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {task.labels.slice(0, 4).map((label) => (
            <span
              key={label.id}
              className="inline-block max-w-[120px] truncate rounded-full px-2 py-0.5 text-[10px] font-medium"
              style={{
                backgroundColor: label.color ? `${label.color}20` : undefined,
                color: label.color ?? undefined,
              }}
            >
              {label.name}
            </span>
          ))}
          {task.labels.length > 4 && (
            <span className="text-[10px] text-surface-400">
              +{task.labels.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Footer: status + due date + meta */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Status badge */}
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
              statusCfg.bg,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', statusCfg.dot)} />
            {statusCfg.label}
          </span>

          {/* Overdue indicator */}
          {isOverdue && (
            <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-red-500">
              <AlertCircle size={10} />
              Overdue
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Estimated time */}
          {task.estimated_minutes && (
            <span className="inline-flex items-center gap-0.5 text-[10px] text-surface-400">
              <Clock size={10} />
              {task.estimated_minutes}m
            </span>
          )}

          {/* Due date */}
          {task.due_date && (
            <span className="inline-flex items-center gap-0.5 text-[10px] text-surface-400">
              <Calendar size={10} />
              {new Date(task.due_date).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
              })}
            </span>
          )}

          {/* Chevron */}
          <ChevronRight size={12} className="text-surface-300 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
      </div>

      {/* Done indicator */}
      {task.status === 'done' && task.completed_at && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400">
          <CheckCircle2 size={10} />
          Completed {new Date(task.completed_at).toLocaleDateString()}
        </div>
      )}

      {/* Archived indicator */}
      {task.status === 'archived' && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-surface-400">
          <Archive size={10} />
          Archived
        </div>
      )}
    </Link>
  )
}

/** Pure mapping for reuse (kanban headers, dropdowns). */
export { STATUS_CONFIG, PRIORITY_CONFIG }
