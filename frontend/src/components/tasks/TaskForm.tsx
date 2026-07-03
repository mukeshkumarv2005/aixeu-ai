/** TaskForm — shared create/edit form for tasks. */

import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { TASK_STATUSES, TASK_PRIORITIES } from '@/types/task'
import type { TaskCreate, TaskUpdate, TaskResponse } from '@/types/task'

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskFormProps {
  /** Existing task for editing; undefined for create mode. */
  task?: TaskResponse
  /** Pre-filled values from AI draft generation (create mode only). */
  draftDefaults?: Partial<TaskCreate>
  /** Called on submit with the form data. */
  onSubmit: (data: TaskCreate | TaskUpdate) => Promise<void>
  /** Whether a mutation is in flight. */
  isPending: boolean
  /** Called to navigate away. */
  onCancel: () => void
}

// ── Component ──────────────────────────────────────────────────────────────

export function TaskForm({
  task,
  draftDefaults,
  onSubmit,
  isPending,
  onCancel,
}: TaskFormProps) {
  const isEditing = !!task

  const [title, setTitle] = useState(draftDefaults?.title ?? task?.title ?? '')
  const [description, setDescription] = useState(
    draftDefaults?.description ?? task?.description ?? '',
  )
  const [status, setStatus] = useState(task?.status ?? 'todo')
  const [priority, setPriority] = useState(
    draftDefaults?.priority ?? task?.priority ?? 'medium',
  )
  const [dueDate, setDueDate] = useState(
    draftDefaults?.due_date ?? task?.due_date ?? '',
  )
  const [reminderAt, setReminderAt] = useState(task?.reminder_at ?? '')
  const [estimatedMinutes, setEstimatedMinutes] = useState(
    draftDefaults?.estimated_minutes
      ? String(draftDefaults.estimated_minutes)
      : task?.estimated_minutes
        ? String(task.estimated_minutes)
        : '',
  )
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const trimmedTitle = title.trim()
    if (!trimmedTitle) {
      setError('Title is required')
      return
    }

    const data: TaskCreate | TaskUpdate = {
      title: trimmedTitle,
      description: description.trim() || null,
      status,
      priority,
      due_date: dueDate || null,
      reminder_at: reminderAt || null,
      estimated_minutes: estimatedMinutes ? Number(estimatedMinutes) : null,
    }

    try {
      await onSubmit(data)
    } catch (err) {
      setError((err as Error)?.message ?? 'Failed to save task')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Title */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
          Title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What needs to be done?"
          className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
          autoFocus
          maxLength={512}
        />
      </div>

      {/* Description */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Add details, context, or notes..."
          rows={5}
          className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
        />
      </div>

      {/* Row: Status + Priority */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Status
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
          >
            {TASK_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Priority
          </label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
          >
            {TASK_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Row: Due date + Reminder */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Due Date
          </label>
          <input
            type="datetime-local"
            value={dueDate ? dueDate.slice(0, 16) : ''}
            onChange={(e) => setDueDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Reminder
          </label>
          <input
            type="datetime-local"
            value={reminderAt ? reminderAt.slice(0, 16) : ''}
            onChange={(e) => setReminderAt(e.target.value ? new Date(e.target.value).toISOString() : '')}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
          />
        </div>
      </div>

      {/* Estimated time */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
          Estimated Time (minutes)
        </label>
        <input
          type="number"
          min={0}
          max={99999}
          value={estimatedMinutes}
          onChange={(e) => setEstimatedMinutes(e.target.value)}
          placeholder="e.g. 60"
          className="w-full max-w-xs rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
        />
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 border-t border-surface-200 pt-5 dark:border-surface-800">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending || !title.trim()}
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-6 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        >
          {isPending && <Loader2 size={16} className="animate-spin" />}
          {isEditing ? 'Update Task' : 'Create Task'}
        </button>
      </div>
    </form>
  )
}
