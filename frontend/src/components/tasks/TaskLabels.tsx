/** TaskLabels — label management for a task detail view. */

import { useState } from 'react'
import { Plus, Loader2, X, Tag, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TaskLabel } from '@/types/task'

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskLabelsProps {
  labels: TaskLabel[] | undefined
  /** All available labels for the autocomplete dropdown. */
  availableLabels: TaskLabel[]
  isLoading: boolean
  isError: boolean
  onAdd: (data: { name: string; color?: string | null }) => Promise<void>
  onRemove: (labelId: string) => Promise<void>
  isPending: boolean
  onCreateLabel?: (name: string) => Promise<void>
}

// ── Predefined colors ──────────────────────────────────────────────────────

const COLOR_OPTIONS = [
  { value: '#ef4444', label: 'Red' },
  { value: '#f97316', label: 'Orange' },
  { value: '#eab308', label: 'Yellow' },
  { value: '#22c55e', label: 'Green' },
  { value: '#06b6d4', label: 'Cyan' },
  { value: '#3b82f6', label: 'Blue' },
  { value: '#8b5cf6', label: 'Purple' },
  { value: '#ec4899', label: 'Pink' },
  { value: '#78716c', label: 'Stone' },
]

// ── Component ──────────────────────────────────────────────────────────────

export function TaskLabels({
  labels,
  availableLabels,
  isLoading,
  isError,
  onAdd,
  onRemove,
  isPending,
  onCreateLabel,
}: TaskLabelsProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(COLOR_OPTIONS[3].value) // default green
  const [localError, setLocalError] = useState<string | null>(null)

  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-500">
        <AlertCircle size={14} />
        Failed to load labels
      </div>
    )
  }

  // Filter available labels that aren't already attached
  const attachedIds = new Set(labels?.map((l) => l.id) ?? [])
  const filteredAvailable = availableLabels.filter(
    (l) => !attachedIds.has(l.id) && l.name.toLowerCase().includes(search.toLowerCase()),
  )

  const handleAdd = async (label: TaskLabel) => {
    setLocalError(null)
    try {
      await onAdd({ name: label.name, color: label.color })
      setShowDropdown(false)
      setSearch('')
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to add label')
    }
  }

  const handleRemove = async (labelId: string) => {
    setLocalError(null)
    try {
      await onRemove(labelId)
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to remove label')
    }
  }

  const handleCreate = async () => {
    const trimmed = newName.trim()
    if (!trimmed || !onCreateLabel) return
    setLocalError(null)
    try {
      await onCreateLabel(trimmed)
      setNewName('')
      setShowCreate(false)
    } catch (err) {
      setLocalError((err as Error)?.message ?? 'Failed to create label')
    }
  }

  return (
    <div>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-3 flex items-center gap-2">
        <Tag size={16} className="text-surface-400" />
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Labels
        </h3>
      </div>

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {localError && (
        <p className="mb-2 text-sm text-red-500">{localError}</p>
      )}

      {/* ── Current labels ──────────────────────────────────────────────── */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {(!labels || labels.length === 0) && (
          <span className="text-xs text-surface-400">No labels</span>
        )}
        {labels?.map((label) => (
          <span
            key={label.id}
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{
              backgroundColor: label.color ? `${label.color}20` : undefined,
              color: label.color ?? undefined,
            }}
          >
            {label.name}
            <button
              onClick={() => handleRemove(label.id)}
              disabled={isPending}
              className="ml-0.5 rounded-full p-0.5 hover:bg-black/10 disabled:opacity-50"
            >
              <X size={10} />
            </button>
          </span>
        ))}
      </div>

      {/* ── Add label trigger ───────────────────────────────────────────── */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-1.5 rounded-lg border border-dashed border-surface-300 px-3 py-1.5 text-xs font-medium text-surface-500 hover:border-surface-400 hover:text-surface-700 dark:border-surface-700 dark:text-surface-400 dark:hover:border-surface-600 dark:hover:text-surface-300 transition-colors"
        >
          <Plus size={12} />
          Add label
        </button>

        {/* ── Dropdown ──────────────────────────────────────────────────── */}
        {showDropdown && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => { setShowDropdown(false); setSearch(''); setShowCreate(false) }}
            />
            <div className="absolute left-0 top-full z-20 mt-1 w-64 rounded-xl border border-surface-200 bg-white p-2 shadow-lg dark:border-surface-800 dark:bg-surface-950">
              {showCreate ? (
                /* ── Create new label form ────────────────────────────── */
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="Label name"
                    className="w-full rounded-lg border border-surface-300 bg-white px-2 py-1.5 text-xs text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                    autoFocus
                    maxLength={32}
                  />
                  <div className="flex flex-wrap gap-1">
                    {COLOR_OPTIONS.map((c) => (
                      <button
                        key={c.value}
                        onClick={() => setNewColor(c.value)}
                        className={cn(
                          'h-5 w-5 rounded-full border-2 transition-all',
                          newColor === c.value ? 'border-surface-900 scale-110 dark:border-white' : 'border-transparent',
                        )}
                        style={{ backgroundColor: c.value }}
                        title={c.label}
                      />
                    ))}
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => { setShowCreate(false); setNewName('') }}
                      className="text-xs text-surface-500 hover:text-surface-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCreate}
                      disabled={!newName.trim() || isPending}
                      className="rounded-lg bg-primary-500 px-3 py-1 text-xs font-medium text-white hover:bg-primary-600 disabled:opacity-50"
                    >
                      Create
                    </button>
                  </div>
                </div>
              ) : (
                /* ── Search / pick existing ──────────────────────────── */
                <div className="space-y-1">
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search labels..."
                    className="w-full rounded-lg border border-surface-200 bg-surface-50 px-2 py-1.5 text-xs text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none dark:border-surface-700 dark:bg-surface-900 dark:text-white"
                    autoFocus
                  />
                  <div className="max-h-40 overflow-y-auto">
                    {filteredAvailable.length === 0 ? (
                      <p className="px-2 py-3 text-center text-xs text-surface-400">
                        {search ? 'No matching labels' : 'All labels added'}
                      </p>
                    ) : (
                      filteredAvailable.slice(0, 20).map((label) => (
                        <button
                          key={label.id}
                          onClick={() => handleAdd(label)}
                          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                        >
                          <span
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: label.color ?? '#78716c' }}
                          />
                          {label.name}
                        </button>
                      ))
                    )}
                  </div>
                  {onCreateLabel && (
                    <button
                      onClick={() => setShowCreate(true)}
                      className="flex w-full items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-primary-600 hover:bg-primary-50 dark:text-primary-400 dark:hover:bg-primary-900/20"
                    >
                      <Plus size={12} />
                      Create new label
                    </button>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
