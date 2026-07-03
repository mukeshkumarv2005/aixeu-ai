/** RelatedTasksWidget — compact card showing tasks linked to a resource.
 *
 * States: loading (spinner), empty (hidden), populated (task list).
 * Links each task to its detail page at `/tasks/:id`.
 */

import { Link } from 'react-router-dom'
import { ListChecks, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTasksByResource } from '@/api/tasks'

// ── Status badges ────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, string> = {
  todo: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
  review: 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400',
  done: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
  archived: 'bg-surface-100 text-surface-500 dark:bg-surface-800',
}

// ── Props ────────────────────────────────────────────────────────────────────

export interface RelatedTasksWidgetProps {
  /** Link tasks owned by this KB document. */
  kbDocumentId?: string
  /** Link tasks created from this uploaded file. */
  uploadedDocumentId?: string
  /** Link tasks spawned from this chat conversation. */
  chatConversationId?: string
  /** Max tasks to show inline (default 5). 0 = no limit. */
  maxTasks?: number
}

// ── Component ────────────────────────────────────────────────────────────────

export function RelatedTasksWidget({
  kbDocumentId,
  uploadedDocumentId,
  chatConversationId,
  maxTasks = 5,
}: RelatedTasksWidgetProps) {
  const hasResource = !!(
    kbDocumentId || uploadedDocumentId || chatConversationId
  )

  const { data, isLoading } = useTasksByResource({
    kb_document_id: kbDocumentId,
    uploaded_document_id: uploadedDocumentId,
    chat_conversation_id: chatConversationId,
  })

  const tasks = data?.items ?? []

  // Don't render when there's nothing to fetch for
  if (!hasResource) return null

  // ── Loading state ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
        <div className="mb-3 flex items-center gap-2">
          <ListChecks size={16} className="text-primary-500" />
          <span className="text-sm font-semibold text-surface-900 dark:text-white">
            Related Tasks
          </span>
        </div>
        <div className="flex items-center justify-center py-4">
          <Loader2 size={16} className="animate-spin text-surface-400" />
        </div>
      </div>
    )
  }

  // ── Empty state — hide the card entirely ────────────────────────────────
  if (tasks.length === 0) return null

  // ── Populated state ────────────────────────────────────────────────────
  const displayTasks = maxTasks > 0 ? tasks.slice(0, maxTasks) : tasks
  const hasMore = tasks.length > (maxTasks > 0 ? maxTasks : Infinity)

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <ListChecks size={16} className="text-primary-500" />
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Related Tasks
        </h3>
        <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs text-surface-500 dark:bg-surface-800">
          {data?.total ?? tasks.length}
        </span>
      </div>

      {/* Task rows */}
      <div className="space-y-1.5">
        {displayTasks.map((task) => (
          <Link
            key={task.id}
            to={`/tasks/${task.id}`}
            className="flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-surface-50 dark:hover:bg-surface-800"
          >
            <span className="min-w-0 flex-1 truncate font-medium text-surface-700 dark:text-surface-300">
              {task.title}
            </span>
            <span
              className={cn(
                'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                STATUS_BADGE[task.status] ?? STATUS_BADGE.todo,
              )}
            >
              {task.status.replace(/_/g, ' ')}
            </span>
          </Link>
        ))}

        {/* Overflow indicator */}
        {hasMore && (
          <Link
            to="/tasks"
            className="block rounded-lg px-3 py-1.5 text-xs font-medium text-primary-500 transition-colors hover:bg-primary-50 dark:hover:bg-primary-900/20"
          >
            View all {data?.total} tasks &rarr;
          </Link>
        )}
      </div>
    </div>
  )
}
