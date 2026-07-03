/** Storage page — upload, list, search, sort, rename, download, delete user files. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Upload,
  FileText,
  Download,
  Trash2,
  AlertCircle,
  Loader2,
  File,
  CheckCircle2,
  Search,
  Grid3X3,
  List,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Pencil,
  X,
  Image,
  FileSpreadsheet,
  Presentation,
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
  checksum?: string | null
  processing_status?: string
  is_temporary: boolean
  created_at: string
  updated_at: string | null
}

interface FileInfoList {
  files: FileInfo[]
  total: number
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

function getFileIcon(mime: string) {
  if (mime.startsWith('image/')) return Image
  if (mime.includes('spreadsheet') || mime.includes('csv')) return FileSpreadsheet
  if (mime.includes('presentation')) return Presentation
  if (mime.includes('markdown') || mime.includes('plain') || mime.includes('pdf') || mime.includes('document'))
    return FileText
  return File
}

function getFileColor(mime: string): string {
  if (mime.startsWith('image/')) return 'text-green-500 bg-green-50 dark:bg-green-900/20'
  if (mime.includes('pdf')) return 'text-red-500 bg-red-50 dark:bg-red-900/20'
  if (mime.includes('spreadsheet') || mime.includes('csv')) return 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
  if (mime.includes('presentation')) return 'text-orange-500 bg-orange-50 dark:bg-orange-900/20'
  if (mime.includes('markdown')) return 'text-blue-500 bg-blue-50 dark:bg-blue-900/20'
  return 'text-primary-500 bg-primary-50 dark:bg-primary-900/20'
}

function getMimeShortLabel(mime: string): string {
  const map: Record<string, string> = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'text/plain': 'TXT',
    'text/markdown': 'MD',
    'text/csv': 'CSV',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX',
    'image/png': 'PNG',
    'image/jpeg': 'JPG',
    'image/webp': 'WEBP',
  }
  return map[mime] || mime.split('/').pop()?.toUpperCase() || 'FILE'
}

type SortKey = 'filename' | 'size_bytes' | 'created_at'
type SortDir = 'asc' | 'desc'
type ViewMode = 'list' | 'grid'

// ---------------------------------------------------------------------------
// Dialog component (simple modal overlay)
// ---------------------------------------------------------------------------

function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) {
  useEffect(() => {
    if (open) {
      const handler = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose()
      }
      document.addEventListener('keydown', handler)
      return () => document.removeEventListener('keydown', handler)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="relative w-full max-w-md rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-800 dark:bg-surface-950">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-surface-900 dark:text-white">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-surface-400 transition-colors hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800 dark:hover:text-surface-300"
          >
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StoragePage() {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Search & sort state ──────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [viewMode, setViewMode] = useState<ViewMode>('list')

  // ── Rename state ─────────────────────────────────────────────────
  const [renameTarget, setRenameTarget] = useState<FileInfo | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [renameSaving, setRenameSaving] = useState(false)

  // ── Delete confirmation state ────────────────────────────────────
  const [confirmDelete, setConfirmDelete] = useState<FileInfo | null>(null)
  const [deleteSaving, setDeleteSaving] = useState(false)

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

  // ── Filter & sort ────────────────────────────────────────────────
  const filteredFiles = useMemo(() => {
    let result = files

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (f) =>
          f.filename.toLowerCase().includes(q) ||
          f.mime_type.toLowerCase().includes(q),
      )
    }

    // Sort
    result = [...result].sort((a, b) => {
      let cmp: number
      if (sortKey === 'filename') {
        cmp = a.filename.localeCompare(b.filename)
      } else if (sortKey === 'size_bytes') {
        cmp = a.size_bytes - b.size_bytes
      } else {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [files, searchQuery, sortKey, sortDir])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <ArrowUpDown size={12} className="opacity-0 group-hover:opacity-50" />
    return sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
  }

  // ── Upload (with XHR progress) ───────────────────────────────────
  const handleUpload = useCallback(
    async (file: File) => {
      setUploadStatus('uploading')
      setUploadProgress(0)
      setError(null)

      try {
        const formData = new FormData()
        formData.append('file', file, file.name)

        // Use XMLHttpRequest for progress tracking
        await new Promise<void>((resolve, reject) => {
          const xhr = new XMLHttpRequest()
          xhr.open('POST', '/api/v1/storage/upload')

          // Inject Bearer token
          import('@/stores/auth').then(({ useAuthStore }) => {
            const token = useAuthStore.getState().accessToken
            if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
          })

          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              setUploadProgress(Math.round((e.loaded / e.total) * 100))
            }
          }

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              setUploadProgress(100)
              setUploadStatus('done')
              resolve()
            } else {
              let detail = 'Upload failed'
              try {
                const body = JSON.parse(xhr.responseText)
                detail = body.detail ?? detail
              } catch {
                // ignore
              }
              reject(new ApiError(xhr.status, detail))
            }
          }

          xhr.onerror = () => reject(new Error('Network error'))
          xhr.send(formData)
        })

        await fetchFiles()
      } catch (err) {
        setUploadStatus('error')
        setError(err instanceof ApiError ? err.message : 'Upload failed')
      } finally {
        // Reset progress after a brief delay
        setTimeout(() => {
          setUploadStatus('idle')
          setUploadProgress(null)
        }, 1500)
      }
    },
    [fetchFiles],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        handleUpload(file)
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

  // ── Rename ───────────────────────────────────────────────────────
  const handleRenameOpen = (file: FileInfo) => {
    setRenameTarget(file)
    setRenameValue(file.filename)
  }

  const handleRenameSave = async () => {
    if (!renameTarget || !renameValue.trim()) return
    setRenameSaving(true)
    setError(null)
    try {
      const updated = await apiClient.patch<FileInfo>(
        `/storage/${renameTarget.id}`,
        { filename: renameValue.trim() },
      )
      setFiles((prev) =>
        prev.map((f) => (f.id === renameTarget.id ? { ...f, filename: updated.filename } : f)),
      )
      setRenameTarget(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Rename failed')
    } finally {
      setRenameSaving(false)
    }
  }

  // ── Delete (with confirmation) ───────────────────────────────────
  const handleDeleteConfirm = (file: FileInfo) => {
    setConfirmDelete(file)
  }

  const handleDeleteExecute = async () => {
    if (!confirmDelete) return
    setDeleteSaving(true)
    setError(null)
    try {
      await apiClient.delete(`/storage/${confirmDelete.id}`)
      setFiles((prev) => prev.filter((f) => f.id !== confirmDelete.id))
      setTotal((prev) => prev - 1)
      setConfirmDelete(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete failed')
    } finally {
      setDeleteSaving(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────

  const isUploading = uploadStatus === 'uploading'

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10">
      {/* ── Page header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-surface-900 dark:text-white">
            File Storage
          </h1>
          <p className="mt-0.5 text-sm text-surface-500">
            Upload, manage, and organize your documents
          </p>
        </div>
      </div>

      {/* ── Error banner ──────────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="shrink-0 text-red-500 hover:text-red-700"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Upload zone ───────────────────────────────────────── */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-colors',
          dragOver
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-surface-300 bg-white hover:border-surface-400 dark:border-surface-700 dark:bg-surface-950 dark:hover:border-surface-600',
          isUploading && 'pointer-events-none opacity-60',
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />
        {isUploading ? (
          <div className="w-full max-w-md space-y-2">
            <div className="flex items-center gap-2 text-sm text-surface-600 dark:text-surface-400">
              <Loader2 size={18} className="animate-spin text-primary-500" />
              <span>Uploading…</span>
              {uploadProgress != null && (
                <span className="font-mono text-xs text-surface-400">
                  {uploadProgress}%
                </span>
              )}
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-surface-200 dark:bg-surface-800">
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-300"
                style={{ width: `${uploadProgress ?? 0}%` }}
              />
            </div>
          </div>
        ) : uploadStatus === 'done' ? (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 size={18} />
            <span>Upload complete</span>
          </div>
        ) : (
          <>
            <Upload
              size={28}
              className="text-surface-400 dark:text-surface-500"
            />
            <p className="mt-2 text-sm font-medium text-surface-700 dark:text-surface-300">
              Drop a file here, or click to browse
            </p>
            <p className="mt-0.5 text-xs text-surface-500">
              Supported: PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, PNG, JPG, WEBP
              &middot; Max 50 MB
            </p>
          </>
        )}
      </div>

      {/* ── Toolbar: search, sort, view toggle ─────────────────── */}
      {!loading && files.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
            />
            <input
              type="text"
              placeholder="Search files…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-surface-200 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder-surface-400 transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-surface-800 dark:bg-surface-950 dark:text-white dark:placeholder-surface-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Sort controls (desktop) */}
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="text-xs text-surface-500">Sort by</span>
            {(
              [
                { key: 'filename' as SortKey, label: 'Name' },
                { key: 'size_bytes' as SortKey, label: 'Size' },
                { key: 'created_at' as SortKey, label: 'Date' },
              ] as const
            ).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => handleSort(key)}
                className={cn(
                  'group flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                  sortKey === key
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                    : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800',
                )}
              >
                {label}
                <SortIcon column={key} />
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div className="flex rounded-lg border border-surface-200 dark:border-surface-800">
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'rounded-l-lg p-1.5 transition-colors',
                viewMode === 'list'
                  ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800',
              )}
              title="List view"
            >
              <List size={16} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'rounded-r-lg p-1.5 transition-colors',
                viewMode === 'grid'
                  ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800',
              )}
              title="Grid view"
            >
              <Grid3X3 size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ── Content ───────────────────────────────────────────── */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-surface-400" />
        </div>
      ) : filteredFiles.length === 0 && searchQuery ? (
        // ── Search empty ──────────────────────────────────────────
        <div className="flex flex-col items-center rounded-xl border border-dashed border-surface-300 py-16 dark:border-surface-700">
          <Search size={36} className="text-surface-300 dark:text-surface-600" />
          <p className="mt-3 text-sm text-surface-500">
            No files match &ldquo;{searchQuery}&rdquo;
          </p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-2 text-xs text-primary-500 hover:text-primary-600"
          >
            Clear search
          </button>
        </div>
      ) : files.length === 0 ? (
        // ── Empty state ─────────────────────────────────────────
        <div className="flex flex-col items-center rounded-xl border border-dashed border-surface-300 py-16 dark:border-surface-700">
          <FileText size={40} className="text-surface-300 dark:text-surface-600" />
          <p className="mt-3 text-sm font-medium text-surface-700 dark:text-surface-300">
            No files uploaded yet
          </p>
          <p className="mt-1 text-xs text-surface-500">
            Drop a file above or click to browse
          </p>
        </div>
      ) : viewMode === 'list' ? (
        // ── List view ───────────────────────────────────────────
        <>
          <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-surface-200 dark:divide-surface-800">
                <thead className="bg-surface-50 dark:bg-surface-900/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-surface-500">
                      File
                    </th>
                    <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-surface-500 sm:table-cell">
                      Size
                    </th>
                    <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-surface-500 md:table-cell">
                      Type
                    </th>
                    <th className="hidden px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-surface-500 lg:table-cell">
                      Date
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-surface-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                  {filteredFiles.map((file) => {
                    const Icon = getFileIcon(file.mime_type)
                    return (
                      <tr
                        key={file.id}
                        className="bg-white transition-colors hover:bg-surface-50 dark:bg-surface-950 dark:hover:bg-surface-900/50"
                      >
                        <td className="max-w-0 px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div
                              className={cn(
                                'rounded-lg p-1.5',
                                getFileColor(file.mime_type),
                              )}
                            >
                              <Icon size={14} />
                            </div>
                            <span className="truncate text-sm font-medium text-surface-900 dark:text-white">
                              {file.filename}
                            </span>
                          </div>
                        </td>
                        <td className="hidden whitespace-nowrap px-4 py-3 text-sm text-surface-600 dark:text-surface-400 sm:table-cell">
                          {formatSize(file.size_bytes)}
                        </td>
                        <td className="hidden max-w-0 truncate px-4 py-3 text-sm text-surface-600 dark:text-surface-400 md:table-cell">
                          {getMimeShortLabel(file.mime_type)}
                        </td>
                        <td className="hidden whitespace-nowrap px-4 py-3 text-sm text-surface-500 dark:text-surface-400 lg:table-cell">
                          {formatDate(file.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleRenameOpen(file)}
                              className="rounded-lg p-1.5 text-surface-500 transition-colors hover:bg-surface-100 hover:text-accent-600 dark:hover:bg-surface-800 dark:hover:text-accent-400"
                              title="Rename"
                            >
                              <Pencil size={15} />
                            </button>
                            <button
                              onClick={() => handleDownload(file.id, file.filename)}
                              className="rounded-lg p-1.5 text-surface-500 transition-colors hover:bg-surface-100 hover:text-primary-600 dark:hover:bg-surface-800 dark:hover:text-primary-400"
                              title="Download"
                            >
                              <Download size={15} />
                            </button>
                            <button
                              onClick={() => handleDeleteConfirm(file)}
                              className="rounded-lg p-1.5 text-surface-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                              title="Delete"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        // ── Grid view ──────────────────────────────────────────
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredFiles.map((file) => {
            const Icon = getFileIcon(file.mime_type)
            return (
              <div
                key={file.id}
                className="group relative rounded-xl border border-surface-200 bg-white p-4 transition-all hover:shadow-md dark:border-surface-800 dark:bg-surface-950"
              >
                {/* File icon */}
                <div className="mb-3 flex items-start justify-between">
                  <div
                    className={cn(
                      'rounded-lg p-2.5',
                      getFileColor(file.mime_type),
                    )}
                  >
                    <Icon size={20} />
                  </div>
                  <span className="rounded bg-surface-100 px-1.5 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                    {getMimeShortLabel(file.mime_type)}
                  </span>
                </div>

                {/* Name */}
                <p className="truncate text-sm font-medium text-surface-900 dark:text-white">
                  {file.filename}
                </p>

                {/* Size + Date */}
                <p className="mt-1 text-xs text-surface-500">
                  {formatSize(file.size_bytes)} &middot;{' '}
                  {new Date(file.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })}
                </p>

                {/* Hover actions */}
                <div className="mt-3 flex items-center gap-1 border-t border-surface-100 pt-3 opacity-0 transition-opacity group-hover:opacity-100 dark:border-surface-800">
                  <button
                    onClick={() => handleRenameOpen(file)}
                    className="flex-1 rounded-md py-1.5 text-xs font-medium text-surface-600 transition-colors hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800"
                  >
                    Rename
                  </button>
                  <button
                    onClick={() => handleDownload(file.id, file.filename)}
                    className="rounded-md p-1.5 text-surface-500 transition-colors hover:bg-surface-100 hover:text-primary-600 dark:hover:bg-surface-800 dark:hover:text-primary-400"
                    title="Download"
                  >
                    <Download size={14} />
                  </button>
                  <button
                    onClick={() => handleDeleteConfirm(file)}
                    className="rounded-md p-1.5 text-surface-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Footer ────────────────────────────────────────────── */}
      {!loading && filteredFiles.length > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-surface-200 px-4 py-2.5 dark:border-surface-800">
          <span className="flex items-center gap-1.5 text-xs text-surface-500">
            <CheckCircle2 size={12} />
            {filteredFiles.length === total
              ? `${total} ${total === 1 ? 'file' : 'files'} total`
              : `${filteredFiles.length} of ${total} ${total === 1 ? 'file' : 'files'}`}
          </span>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-xs text-primary-500 hover:text-primary-600"
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* ── Rename Dialog ─────────────────────────────────────── */}
      <Dialog
        open={renameTarget !== null}
        onClose={() => setRenameTarget(null)}
        title="Rename file"
      >
        <input
          type="text"
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleRenameSave()
            if (e.key === 'Escape') setRenameTarget(null)
          }}
          autoFocus
          className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-surface-800 dark:bg-surface-950 dark:text-white dark:placeholder-surface-500"
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={() => setRenameTarget(null)}
            className="rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-sm font-medium text-surface-700 transition-colors hover:bg-surface-50 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300 dark:hover:bg-surface-900"
          >
            Cancel
          </button>
          <button
            onClick={handleRenameSave}
            disabled={renameSaving || !renameValue.trim()}
            className="rounded-lg bg-primary-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-600 disabled:opacity-50"
          >
            {renameSaving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              'Save'
            )}
          </button>
        </div>
      </Dialog>

      {/* ── Delete Confirmation Dialog ─────────────────────────── */}
      <Dialog
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        title="Delete file"
      >
        <p className="text-sm text-surface-600 dark:text-surface-400">
          Are you sure you want to delete{' '}
          <span className="font-medium text-surface-900 dark:text-white">
            &ldquo;{confirmDelete?.filename}&rdquo;
          </span>
          ? This action cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={() => setConfirmDelete(null)}
            className="rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-sm font-medium text-surface-700 transition-colors hover:bg-surface-50 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300 dark:hover:bg-surface-900"
          >
            Cancel
          </button>
          <button
            onClick={handleDeleteExecute}
            disabled={deleteSaving}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
          >
            {deleteSaving ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              'Delete'
            )}
          </button>
        </div>
      </Dialog>
    </div>
  )
}
