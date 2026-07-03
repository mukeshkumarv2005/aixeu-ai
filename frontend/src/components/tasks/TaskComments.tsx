/** TaskComments — threaded comments section for a task detail page. */

import { useState } from 'react'
import { Loader2, Trash2, Pencil, Check, X, MessageSquare, AlertCircle } from 'lucide-react'
import type { TaskComment } from '@/types/task'

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskCommentsProps {
  comments: TaskComment[] | undefined
  isLoading: boolean
  isError: boolean
  /** Called to add a new comment. */
  onAdd: (content: string) => Promise<void>
  /** Called to update an existing comment. */
  onUpdate: (commentId: string, content: string) => Promise<void>
  /** Called to delete a comment. */
  onDelete: (commentId: string) => Promise<void>
  /** Whether an add/update/delete mutation is in flight. */
  isPending: boolean
}

// ── Component ──────────────────────────────────────────────────────────────

export function TaskComments({
  comments,
  isLoading,
  isError,
  onAdd,
  onUpdate,
  onDelete,
  isPending,
}: TaskCommentsProps) {
  const [newContent, setNewContent] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const handleAdd = async () => {
    const trimmed = newContent.trim()
    if (!trimmed) return
    setLocalError(null)
    try {
      await onAdd(trimmed)
      setNewContent('')
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to add comment')
    }
  }

  const handleUpdate = async (commentId: string) => {
    const trimmed = editContent.trim()
    if (!trimmed) return
    setLocalError(null)
    try {
      await onUpdate(commentId, trimmed)
      setEditingId(null)
      setEditContent('')
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to update comment')
    }
  }

  const handleDelete = async (commentId: string) => {
    setLocalError(null)
    try {
      await onDelete(commentId)
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to delete comment')
    }
  }

  const startEditing = (comment: TaskComment) => {
    setEditingId(comment.id)
    setEditContent(comment.content)
  }

  const cancelEditing = () => {
    setEditingId(null)
    setEditContent('')
  }

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
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center dark:border-red-900/30 dark:bg-red-900/10">
        <AlertCircle size={24} className="text-red-400" />
        <p className="text-sm font-medium text-red-700 dark:text-red-300">
          Failed to load comments
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-4 flex items-center gap-2">
        <MessageSquare size={16} className="text-surface-400" />
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Comments
        </h3>
        {comments && comments.length > 0 && (
          <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[11px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            {comments.length}
          </span>
        )}
      </div>

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {localError && (
        <p className="mb-3 text-sm text-red-500">{localError}</p>
      )}

      {/* ── Add comment ─────────────────────────────────────────────────── */}
      <div className="mb-6 rounded-xl border border-surface-200 bg-white p-3 dark:border-surface-800 dark:bg-surface-950">
        <textarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Write a comment..."
          rows={3}
          className="w-full resize-none rounded-lg border-0 bg-transparent p-0 text-sm text-surface-900 placeholder-surface-400 focus:outline-none dark:text-white dark:placeholder-surface-500"
        />
        <div className="mt-2 flex items-center justify-between border-t border-surface-100 pt-2 dark:border-surface-800">
          <span className="text-xs text-surface-400">
            Markdown supported
          </span>
          <button
            onClick={handleAdd}
            disabled={isPending || !newContent.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            {isPending && <Loader2 size={12} className="animate-spin" />}
            Comment
          </button>
        </div>
      </div>

      {/* ── Comments list ───────────────────────────────────────────────── */}
      {(!comments || comments.length === 0) ? (
        <p className="py-6 text-center text-sm text-surface-400">
          No comments yet. Start the conversation.
        </p>
      ) : (
        <div className="space-y-3">
          {comments.map((comment) => (
            <div
              key={comment.id}
              className="rounded-xl border border-surface-200 bg-white p-3 dark:border-surface-800 dark:bg-surface-950"
            >
              {/* Author + timestamp */}
              <div className="mb-1.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-surface-900 dark:text-white">
                    {comment.author_id.slice(0, 8)}
                  </span>
                  <span className="text-[10px] text-surface-400">
                    {new Date(comment.created_at).toLocaleString()}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => startEditing(comment)}
                    className="rounded p-0.5 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
                    title="Edit"
                  >
                    <Pencil size={12} />
                  </button>
                  <button
                    onClick={() => handleDelete(comment.id)}
                    className="rounded p-0.5 text-surface-400 hover:text-red-500"
                    title="Delete"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              {/* Content (or edit form) */}
              {editingId === comment.id ? (
                <div>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-surface-300 bg-white p-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                  />
                  <div className="mt-1.5 flex items-center justify-end gap-2">
                    <button
                      onClick={cancelEditing}
                      className="rounded p-1 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
                    >
                      <X size={14} />
                    </button>
                    <button
                      onClick={() => handleUpdate(comment.id)}
                      disabled={isPending || !editContent.trim()}
                      className="flex items-center gap-1 rounded bg-primary-500 px-2 py-1 text-xs font-medium text-white hover:bg-primary-600 disabled:opacity-50"
                    >
                      {isPending && <Loader2 size={10} className="animate-spin" />}
                      <Check size={12} />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <p className="whitespace-pre-wrap text-sm text-surface-700 dark:text-surface-300">
                  {comment.content}
                </p>
              )}

              {/* Updated indicator */}
              {comment.updated_at && comment.updated_at !== comment.created_at && (
                <p className="mt-1 text-[10px] text-surface-400">
                  Edited {new Date(comment.updated_at).toLocaleString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
