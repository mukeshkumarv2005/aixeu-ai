/** Storage page — upload, list, download, and delete user files. */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Upload,
  FileText,
  Download,
  Trash2,
  AlertCircle,
  Loader2,
  File,
  CheckCircle2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient, ApiError } from '@/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FileInfo {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  storage_path: string
  is_temporary: boolean
  created_at: string
  updated_at: string
}

interface FileInfoList {
  files: FileInfo[]
  total: number
}

interface FileUploadResponse {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  storage_path: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StoragePage() {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Fetch file list ──────────────────────────────────────────────
  const fetchFiles = useCallback(async () => {
    try {
      setError(null)
      const data = await apiClient.get<FileInfoList>('/storage/files')
      setFiles(data.files)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  // ── Upload ───────────────────────────────────────────────────────
  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true)
      setError(null)
      try {
        const formData = new FormData()
        formData.append('file', file, file.name)
        await apiClient.upload<FileUploadResponse>('/storage/upload', formData)
        await fetchFiles()
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : 'Upload failed',
        )
      } finally {
        setUploading(false)
      }
    },
    [fetchFiles],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        handleUpload(file)
        // Reset input so the same file can be re-uploaded
        e.target.value = ''
      }
    },
    [handleUpload],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files?.[0]
      if (file) handleUpload(file)
    },
    [handleUpload],
  )

  // ── Download ─────────────────────────────────────────────────────
  const handleDownload = useCallback(
    async (fileId: string, filename: string) => {
      try {
        const token =
          (await import('@/stores/auth')).useAuthStore.getState().accessToken
        const res = await fetch(`/api/v1/storage/${fileId}/download`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!res.ok) throw new Error('Download failed')

        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.click()
        URL.revokeObjectURL(url)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Download failed')
      }
    },
    [],
  )

  // ── Delete ───────────────────────────────────────────────────────
  const handleDelete = useCallback(
    async (fileId: string) => {
      setDeleteId(fileId)
      try {
        await apiClient.delete(`/storage/${fileId}`)
        setFiles((prev) => prev.filter((f) => f.id !== fileId))
        setTotal((prev) => prev - 1)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Delete failed')
      } finally {
        setDeleteId(null)
      }
    },
    [],
  )

  // ── Render ───────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <h1 className="text-xl font-bold text-gray-900 dark:text-white">
        File Storage
      </h1>

      {/* ── Error banner ─────────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            &times;
          </button>
        </div>
      )}

      {/* ── Upload zone ──────────────────────────────────────── */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors',
          dragOver
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
            : 'border-gray-300 bg-white hover:border-gray-400 dark:border-gray-700 dark:bg-gray-950 dark:hover:border-gray-600',
          uploading && 'pointer-events-none opacity-60',
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          disabled={uploading}
        />
        {uploading ? (
          <>
            <Loader2 size={32} className="animate-spin text-indigo-500" />
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
              Uploading…
            </p>
          </>
        ) : (
          <>
            <Upload
              size={32}
              className="text-gray-400 dark:text-gray-500"
            />
            <p className="mt-3 text-sm font-medium text-gray-700 dark:text-gray-300">
              Drop a file here, or click to browse
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Max 50 MB per file
            </p>
          </>
        )}
      </div>

      {/* ── File list ────────────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={24} className="animate-spin text-gray-400" />
        </div>
      ) : files.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 py-12 dark:border-gray-700">
          <FileText size={40} className="text-gray-300 dark:text-gray-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
            No files uploaded yet
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Drop a file above or click to browse
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    File
                  </th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 sm:table-cell">
                    Size
                  </th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 md:table-cell">
                    Type
                  </th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 lg:table-cell">
                    Date
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {files.map((file) => (
                  <tr
                    key={file.id}
                    className="bg-white transition-colors hover:bg-gray-50 dark:bg-gray-950 dark:hover:bg-gray-900/50"
                  >
                    <td className="max-w-0 px-4 py-3">
                      <div className="flex items-center gap-2">
                        <File size={16} className="shrink-0 text-gray-400" />
                        <span className="truncate text-sm font-medium text-gray-900 dark:text-white">
                          {file.filename}
                        </span>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3 text-sm text-gray-600 dark:text-gray-400 sm:table-cell">
                      {formatSize(file.size_bytes)}
                    </td>
                    <td className="hidden max-w-0 truncate px-4 py-3 text-sm text-gray-600 dark:text-gray-400 md:table-cell">
                      {file.mime_type}
                    </td>
                    <td className="hidden px-4 py-3 text-sm text-gray-500 dark:text-gray-400 lg:table-cell">
                      {formatDate(file.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleDownload(file.id, file.filename)}
                          className="rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-indigo-600 dark:hover:bg-gray-800 dark:hover:text-indigo-400"
                          title="Download"
                        >
                          <Download size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(file.id)}
                          disabled={deleteId === file.id}
                          className="rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                          title="Delete"
                        >
                          {deleteId === file.id ? (
                            <Loader2 size={16} className="animate-spin" />
                          ) : (
                            <Trash2 size={16} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-gray-200 px-4 py-2.5 dark:border-gray-800">
            <span className="flex items-center gap-1.5 text-xs text-gray-500">
              <CheckCircle2 size={12} />
              {total} {total === 1 ? 'file' : 'files'} total
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
