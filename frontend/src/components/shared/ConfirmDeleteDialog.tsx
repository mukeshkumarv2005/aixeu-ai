/** ConfirmDeleteDialog — reusable confirmation modal for destructive actions. */

import { Loader2, AlertTriangle } from 'lucide-react'

interface ConfirmDeleteDialogProps {
  title: string
  message: string
  onConfirm: () => void | Promise<void>
  onCancel: () => void
  isLoading?: boolean
  confirmLabel?: string
  cancelLabel?: string
}

export function ConfirmDeleteDialog({
  title,
  message,
  onConfirm,
  onCancel,
  isLoading = false,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
}: ConfirmDeleteDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={!isLoading ? onCancel : undefined}
      />

      {/* Dialog */}
      <div className="relative mx-4 w-full max-w-md rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-800 dark:bg-surface-950">
        {/* Icon */}
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
          <AlertTriangle size={24} className="text-red-500" />
        </div>

        {/* Title */}
        <h2 className="mb-2 text-center text-lg font-semibold text-surface-900 dark:text-white">
          {title}
        </h2>

        {/* Message */}
        <p className="mb-6 text-center text-sm text-surface-500 dark:text-surface-400">
          {message}
        </p>

        {/* Actions */}
        <div className="flex justify-center gap-3">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 disabled:opacity-50 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {isLoading && <Loader2 size={14} className="animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
