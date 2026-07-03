/** TaskDetail page — full task view with edit, comments, labels, attachments. */

import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowDown,
  ArrowUp,
  Loader2,
  AlertCircle,
  Pencil,
  Trash2,
  CheckCircle2,
  Circle,
  Eye,
  Minus,
  Archive,
  RefreshCw,
  RotateCcw,
  Clock,
  Calendar,
  Paperclip,
  FileText,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useTask,
  useUpdateTask,
  useDeleteTask,
  useCompleteTask,
  useArchiveTask,
  useRestoreTask,
  useAddLabel,
  useRemoveLabel,
  useAddComment,
  useUpdateComment,
  useDeleteComment,
} from '@/api/tasks'
import { TaskForm } from '@/components/tasks/TaskForm'
import { TaskComments } from '@/components/tasks/TaskComments'
import { TaskLabels } from '@/components/tasks/TaskLabels'
import { TaskAIAssistant } from '@/components/tasks/TaskAIAssistant'
import type { TaskUpdate, TaskStatus } from '@/types/task'

// ── Local status & priority display configs ───────────────────────────────────

const STATUS_DISPLAY: Record<TaskStatus, { label: string; className: string; icon: React.ComponentType<{ size?: number }> }> = {
  todo: { label: 'To Do', className: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400', icon: Circle },
  in_progress: { label: 'In Progress', className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400', icon: Loader2 },
  review: { label: 'Review', className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400', icon: Eye },
  done: { label: 'Done', className: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400', icon: CheckCircle2 },
  archived: { label: 'Archived', className: 'bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-500', icon: Archive },
}

const PRIORITY_DISPLAY: Record<string, { label: string; className: string; icon: React.ComponentType<{ size?: number }> }> = {
  critical: { label: 'Critical', className: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/10', icon: AlertTriangle },
  high: { label: 'High', className: 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/10', icon: ArrowUp },
  medium: { label: 'Medium', className: 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/10', icon: Minus },
  low: { label: 'Low', className: 'text-surface-500 dark:text-surface-400 bg-surface-50 dark:bg-surface-800', icon: ArrowDown },
}

// ── Confirm dialog ───────────────────────────────────────────────────────────

function ConfirmDeleteDialog({
  open,
  onConfirm,
  onCancel,
  isPending,
}: {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-xl border border-surface-200 bg-white p-6 shadow-2xl dark:border-surface-800 dark:bg-surface-950">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
            <AlertTriangle size={20} className="text-red-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-surface-900 dark:text-white">
              Delete task
            </h3>
            <p className="text-sm text-surface-500">
              This action cannot be undone.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {isPending && <Loader2 size={14} className="animate-spin" />}
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Attachment display ───────────────────────────────────────────────────────

function Attachment({ att }: { att: { id: string; file_id: string } }) {
  return (
    <a
      href={`/api/v1/files/${att.file_id}/download`}
      className="flex items-center gap-3 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-sm hover:bg-surface-100 dark:border-surface-700 dark:bg-surface-900 dark:hover:bg-surface-800 transition-colors"
    >
      <Paperclip size={16} className="shrink-0 text-surface-400" />
      <span className="flex-1 truncate text-xs text-surface-500">
        File {att.file_id.slice(0, 8)}
      </span>
    </a>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()

  // ── Queries ──────────────────────────────────────────────────────────────
  const {
    data: task,
    isLoading,
    isError,
    error,
    refetch,
  } = useTask(taskId ?? '')

  // ── Mutations ────────────────────────────────────────────────────────────
  const updateMutation = useUpdateTask()
  const deleteMutation = useDeleteTask()
  const completeMutation = useCompleteTask()
  const archiveMutation = useArchiveTask()
  const restoreMutation = useRestoreTask()
  const addLabelMutation = useAddLabel()
  const removeLabelMutation = useRemoveLabel()
  const addCommentMutation = useAddComment()
  const updateCommentMutation = useUpdateComment()
  const deleteCommentMutation = useDeleteComment()

  // ── Local state ──────────────────────────────────────────────────────────
  const [editing, setEditing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleUpdate = async (data: TaskUpdate) => {
    if (!taskId) return
    await updateMutation.mutateAsync({ taskId, body: data })
    setEditing(false)
  }

  const handleDelete = async () => {
    if (!taskId) return
    await deleteMutation.mutateAsync(taskId)
    navigate('/tasks', { replace: true })
  }

  const handleComplete = async () => {
    if (!taskId) return
    await completeMutation.mutateAsync(taskId)
  }

  const handleArchive = async () => {
    if (!taskId) return
    await archiveMutation.mutateAsync(taskId)
  }

  const handleRestore = async () => {
    if (!taskId) return
    await restoreMutation.mutateAsync(taskId)
  }

  const handleAddLabel = async (data: { name: string; color?: string | null }) => {
    if (!taskId) return
    await addLabelMutation.mutateAsync({ taskId, ...data })
  }

  const handleRemoveLabel = async (labelId: string) => {
    if (!taskId) return
    await removeLabelMutation.mutateAsync({ taskId, labelId })
  }

  const handleAddComment = async (content: string) => {
    if (!taskId) return
    await addCommentMutation.mutateAsync({ taskId, content })
  }

  const handleUpdateComment = async (commentId: string, content: string) => {
    if (!taskId) return
    await updateCommentMutation.mutateAsync({ taskId, commentId, content })
  }

  const handleDeleteComment = async (commentId: string) => {
    if (!taskId) return
    await deleteCommentMutation.mutateAsync({ taskId, commentId })
  }

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
    const is404 =
      (error as any)?.status === 404 ||
      (error as any)?.response?.status === 404 ||
      (error as Error)?.message?.toLowerCase().includes('not found')

    if (is404) {
      return (
        <div className="mx-auto max-w-xl px-4 py-20 text-center">
          <FileText size={48} className="mx-auto mb-4 text-surface-300 dark:text-surface-600" />
          <h2 className="mb-2 text-xl font-semibold text-surface-900 dark:text-white">
            Task not found
          </h2>
          <p className="mb-6 text-sm text-surface-500">
            The task you're looking for doesn't exist or has been deleted.
          </p>
          <button
            onClick={() => navigate('/tasks')}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
          >
            <ArrowLeft size={14} />
            Back to Tasks
          </button>
        </div>
      )
    }

    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <AlertCircle size={48} className="mx-auto mb-4 text-red-400" />
        <h2 className="mb-2 text-xl font-semibold text-red-700 dark:text-red-300">
          Failed to load task
        </h2>
        <p className="mb-6 text-sm text-red-500">
          {(error as Error)?.message ?? 'An unexpected error occurred.'}
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            <RefreshCw size={14} />
            Retry
          </button>
          <button
            onClick={() => navigate('/tasks')}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 transition-colors"
          >
            <ArrowLeft size={14} />
            Back to Tasks
          </button>
        </div>
      </div>
    )
  }

  // ── Not found (null data) ────────────────────────────────────────────────
  if (!task) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <FileText size={48} className="mx-auto mb-4 text-surface-300 dark:text-surface-600" />
        <h2 className="mb-2 text-xl font-semibold text-surface-900 dark:text-white">
          Task not found
        </h2>
        <p className="mb-6 text-sm text-surface-500">
          This task could not be loaded.
        </p>
        <button
          onClick={() => navigate('/tasks')}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Tasks
        </button>
      </div>
    )
  }

  const statusCfg = STATUS_DISPLAY[task.status as TaskStatus]
  const priorityCfg = PRIORITY_DISPLAY[task.priority]
  const isDone = task.status === 'done'
  const isArchived = task.status === 'archived'

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* ── Delete confirmation ───────────────────────────────────────── */}
      <ConfirmDeleteDialog
        open={showDeleteConfirm}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
        isPending={deleteMutation.isPending}
      />

      {/* ── Back link ──────────────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/tasks')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
      >
        <ArrowLeft size={14} />
        Back to Tasks
      </button>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* HEADER                                                             */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {/* Status badge */}
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium',
                statusCfg?.className ?? '',
              )}
            >
              {statusCfg?.icon && <statusCfg.icon size={12} />}
              {task.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>

            {/* Priority badge */}
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium',
                priorityCfg?.className ?? '',
              )}
            >
              {priorityCfg?.icon && <priorityCfg.icon size={12} />}
              {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-surface-900 dark:text-white break-words">
            {task.title}
          </h1>

          {task.description && (
            <p className="mt-2 whitespace-pre-wrap text-sm text-surface-600 dark:text-surface-400">
              {task.description}
            </p>
          )}

          {/* ── Meta row ────────────────────────────────────────────────── */}
          <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-surface-400">
            {task.estimated_minutes && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {task.estimated_minutes} min
              </span>
            )}
            {task.due_date && (
              <span
                className={cn(
                  'flex items-center gap-1',
                  new Date(task.due_date) < new Date() && !isDone && !isArchived
                    ? 'text-red-500 font-medium'
                    : '',
                )}
              >
                <Calendar size={12} />
                Due {new Date(task.due_date).toLocaleDateString()}
              </span>
            )}
            {task.reminder_at && (
              <span className="flex items-center gap-1">
                <AlertTriangle size={12} />
                Reminder {new Date(task.reminder_at).toLocaleDateString()}
              </span>
            )}
            {task.created_at && (
              <span>Created {new Date(task.created_at).toLocaleDateString()}</span>
            )}
            {task.updated_at && task.updated_at !== task.created_at && (
              <span>Updated {new Date(task.updated_at).toLocaleDateString()}</span>
            )}
          </div>
        </div>

        {/* ── Action buttons ──────────────────────────────────────────── */}
        <div className="flex shrink-0 items-center gap-2">
          {!editing && !isArchived && (
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 transition-colors"
            >
              <Pencil size={14} />
              Edit
            </button>
          )}

          {!editing && isDone && (
            <button
              onClick={handleRestore}
              disabled={restoreMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 disabled:opacity-50 transition-colors"
            >
              {restoreMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RotateCcw size={14} />
              )}
              Reopen
            </button>
          )}

          {!editing && !isDone && !isArchived && (
            <button
              onClick={handleComplete}
              disabled={completeMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {completeMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <CheckCircle2 size={14} />
              )}
              Complete
            </button>
          )}

          {!editing && !isArchived && isDone && (
            <button
              onClick={handleArchive}
              disabled={archiveMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 disabled:opacity-50 transition-colors"
            >
              {archiveMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Archive size={14} />
              )}
              Archive
            </button>
          )}

          {!editing && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-900/30 dark:bg-surface-900 dark:text-red-400 dark:hover:bg-red-900/10 disabled:opacity-50 transition-colors"
            >
              <Trash2 size={14} />
              Delete
            </button>
          )}
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* CONTENT — edit mode vs display mode                                 */}
      {/* ════════════════════════════════════════════════════════════════════ */}

      {editing ? (
        /* ── Edit form ───────────────────────────────────────────────── */
        <div className="mb-8 rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-950">
          <h2 className="mb-4 text-sm font-semibold text-surface-900 dark:text-white">
            Edit Task
          </h2>
          <TaskForm
            task={task}
            onSubmit={handleUpdate}
            isPending={updateMutation.isPending}
            onCancel={() => setEditing(false)}
          />
        </div>
      ) : (
        /* ── Detail sections ─────────────────────────────────────────── */
        <div className="grid gap-6 lg:grid-cols-3">
          {/* ── Left column — comments ────────────────────────────────── */}
          <div className="lg:col-span-2 space-y-6">
            {/* Labels */}
            <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
              <TaskLabels
                labels={task.labels}
                availableLabels={task.labels ?? []}
                isLoading={false}
                isError={false}
                onAdd={handleAddLabel}
                onRemove={handleRemoveLabel}
                isPending={addLabelMutation.isPending || removeLabelMutation.isPending}
                onCreateLabel={(name: string) => handleAddLabel({ name })}
              />
            </div>

            {/* Comments */}
            <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
              <TaskComments
                comments={task.comments}
                isLoading={false}
                isError={false}
                onAdd={handleAddComment}
                onUpdate={handleUpdateComment}
                onDelete={handleDeleteComment}
                isPending={
                  addCommentMutation.isPending ||
                  updateCommentMutation.isPending ||
                  deleteCommentMutation.isPending
                }
              />
            </div>
          </div>

          {/* ── Right column — metadata sidebar ────────────────────────── */}
          <div className="space-y-6">
            {/* Attachments */}
            <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
              <div className="mb-3 flex items-center gap-2">
                <Paperclip size={16} className="text-surface-400" />
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                  Attachments
                </h3>
                {task.attachments && task.attachments.length > 0 && (
                  <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[11px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                    {task.attachments.length}
                  </span>
                )}
              </div>

              {(!task.attachments || task.attachments.length === 0) ? (
                <p className="py-4 text-center text-xs text-surface-400">
                  No attachments
                </p>
              ) : (
                <div className="space-y-2">
                  {task.attachments.map((att) => (
                    <Attachment key={att.id} att={att} />
                  ))}
                </div>
              )}
            </div>

            {/* Linked Resources */}
            {(task.kb_document_id || task.chat_conversation_id || task.uploaded_document_id) && (
              <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
                <div className="mb-3 flex items-center gap-2">
                  <FileText size={16} className="text-surface-400" />
                  <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                    Linked Resources
                  </h3>
                </div>
                <div className="space-y-2">
                  {task.kb_document_id && (
                    <Link
                      to={`/knowledge/${task.kb_document_id}`}
                      className="flex items-center gap-2 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-sm hover:bg-surface-100 dark:border-surface-700 dark:bg-surface-900 dark:hover:bg-surface-800 transition-colors"
                    >
                      <FileText size={14} className="shrink-0 text-primary-500" />
                      <span className="flex-1 truncate text-xs text-surface-600 dark:text-surface-400">
                        KB Document
                      </span>
                      <span className="shrink-0 text-surface-400">
                        &rarr;
                      </span>
                    </Link>
                  )}
                  {task.chat_conversation_id && (
                    <Link
                      to={`/chat/${task.chat_conversation_id}`}
                      className="flex items-center gap-2 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-sm hover:bg-surface-100 dark:border-surface-700 dark:bg-surface-900 dark:hover:bg-surface-800 transition-colors"
                    >
                      <FileText size={14} className="shrink-0 text-green-500" />
                      <span className="flex-1 truncate text-xs text-surface-600 dark:text-surface-400">
                        Chat Conversation
                      </span>
                      <span className="shrink-0 text-surface-400">
                        &rarr;
                      </span>
                    </Link>
                  )}
                  {task.uploaded_document_id && (
                    <Link
                      to={`/documents/${task.uploaded_document_id}`}
                      className="flex items-center gap-2 rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-sm hover:bg-surface-100 dark:border-surface-700 dark:bg-surface-900 dark:hover:bg-surface-800 transition-colors"
                    >
                      <FileText size={14} className="shrink-0 text-amber-500" />
                      <span className="flex-1 truncate text-xs text-surface-600 dark:text-surface-400">
                        Uploaded Document
                      </span>
                      <span className="shrink-0 text-surface-400">
                        &rarr;
                      </span>
                    </Link>
                  )}
                </div>
              </div>
            )}

            {/* AI Assistant */}
            <TaskAIAssistant taskId={task.id} taskTitle={task.title} />

            {/* Task info */}
            <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
              <div className="mb-3 flex items-center gap-2">
                <FileText size={16} className="text-surface-400" />
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                  Details
                </h3>
              </div>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-surface-400">Status</dt>
                  <dd className="font-medium text-surface-900 dark:text-white">
                    {task.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-surface-400">Priority</dt>
                  <dd className="font-medium text-surface-900 dark:text-white">
                    {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                  </dd>
                </div>
                {task.estimated_minutes && (
                  <div className="flex justify-between">
                    <dt className="text-surface-400">Est. time</dt>
                    <dd className="font-medium text-surface-900 dark:text-white">
                      {task.estimated_minutes} min
                    </dd>
                  </div>
                )}
                {task.due_date && (
                  <div className="flex justify-between">
                    <dt className="text-surface-400">Due date</dt>
                    <dd
                      className={cn(
                        'font-medium',
                        new Date(task.due_date) < new Date() && !isDone && !isArchived
                          ? 'text-red-500'
                          : 'text-surface-900 dark:text-white',
                      )}
                    >
                      {new Date(task.due_date).toLocaleDateString()}
                    </dd>
                  </div>
                )}
                {task.reminder_at && (
                  <div className="flex justify-between">
                    <dt className="text-surface-400">Reminder</dt>
                    <dd className="font-medium text-surface-900 dark:text-white">
                      {new Date(task.reminder_at).toLocaleDateString()}
                    </dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-surface-400">Created</dt>
                  <dd className="font-medium text-surface-900 dark:text-white">
                    {new Date(task.created_at).toLocaleDateString()}
                  </dd>
                </div>
                {task.updated_at && (
                  <div className="flex justify-between">
                    <dt className="text-surface-400">Updated</dt>
                    <dd className="font-medium text-surface-900 dark:text-white">
                      {new Date(task.updated_at).toLocaleDateString()}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
