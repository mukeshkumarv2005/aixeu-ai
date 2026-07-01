/** Recent documents widget — shows the 5 most recently uploaded files. */

import { useNavigate } from 'react-router-dom'
import { FileText, ArrowRight, AlertCircle } from 'lucide-react'
import type { FileInfo } from '@/types/dashboard'

interface RecentDocumentsProps {
  files: FileInfo[]
  loading?: boolean
  error?: string | null
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function RecentDocuments({ files, loading, error }: RecentDocumentsProps) {
  const navigate = useNavigate()

  return (
    <WidgetCard title="Recent Documents">
      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-2/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-2.5 w-1/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
              </div>
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

      {/* Empty */}
      {!loading && !error && files.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <FileText size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500">No files uploaded</p>
          <p className="text-xs text-surface-400">
            Upload documents to see them here.
          </p>
        </div>
      )}

      {/* Data */}
      {!loading && !error && files.length > 0 && (
        <div className="space-y-1">
          {files.map((file) => {
            const ext = file.filename.split('.').pop()?.toUpperCase() || 'FILE'
            return (
              <button
                key={file.id}
                onClick={() => navigate('/storage')}
                className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
              >
                <div className="rounded-lg bg-accent-50 p-1.5 text-accent-500 dark:bg-accent-900/20 dark:text-accent-400">
                  <FileText size={14} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                    {file.filename}
                  </p>
                  <p className="text-xs text-surface-400">
                    {formatSize(file.size_bytes)} · {ext} · {formatDate(file.created_at)}
                  </p>
                </div>
                <ArrowRight size={14} className="shrink-0 text-surface-300 dark:text-surface-600" />
              </button>
            )
          })}
        </div>
      )}
    </WidgetCard>
  )
}

function WidgetCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          {title}
        </h3>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}
