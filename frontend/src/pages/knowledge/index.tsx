/** Knowledge Base list page.
 *
 * Displays all user's knowledge bases in a card grid.
 * States: loading, error, empty, list.
 * Actions: create (dialog), delete (confirm), click-to-navigate.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Brain,
  BookOpen,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  X,
  Layers,
  FileText,
  Cpu,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useKnowledgeBases,
  useCreateKnowledgeBase,
  useDeleteKnowledgeBase,
} from '@/api/knowledge'
import type { KnowledgeBaseResponse } from '@/types/knowledge'

export default function KnowledgeBasePage() {
  const navigate = useNavigate()

  // ── Queries & Mutations ──────────────────────────────────────────────
  const { data, isLoading, isError, error, refetch } = useKnowledgeBases()
  const createMutation = useCreateKnowledgeBase()
  const deleteMutation = useDeleteKnowledgeBase()

  // ── Local state ──────────────────────────────────────────────────────
  const [showCreate, setShowCreate] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseResponse | null>(null)

  // Create form state
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [formModel, setFormModel] = useState('text-embedding-3-small')
  const [formError, setFormError] = useState<string | null>(null)

  // ── Handlers ─────────────────────────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formName.trim()) {
      setFormError('Name is required')
      return
    }
    setFormError(null)
    try {
      const kb = await createMutation.mutateAsync({
        name: formName.trim(),
        description: formDesc.trim() || undefined,
        embedding_model: formModel,
      })
      setShowCreate(false)
      resetForm()
      navigate(`/knowledge/${kb.id}`)
    } catch {
      setFormError('Failed to create knowledge base')
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteMutation.mutateAsync(deleteTarget.id)
      setDeleteTarget(null)
    } catch {
      // Error handled by query cache
    }
  }

  const resetForm = () => {
    setFormName('')
    setFormDesc('')
    setFormModel('text-embedding-3-small')
    setFormError(null)
  }

  // ── Loading state ────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error state ──────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p className="flex-1 text-sm">
            {(error as Error)?.message ?? 'Failed to load knowledge bases'}
          </p>
          <button
            onClick={() => refetch()}
            className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium hover:bg-red-200 dark:bg-red-800/30 dark:hover:bg-red-800/50"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const items = data?.items ?? []

  // ── Empty state ──────────────────────────────────────────────────────
  const isEmpty = items.length === 0

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Knowledge Bases
          </h1>
          <p className="mt-1 text-sm text-surface-500">
            Build semantic search indexes from your documents
          </p>
        </div>
        <button
          onClick={() => {
            resetForm()
            setShowCreate(true)
          }}
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
        >
          <Plus size={16} />
          Create KB
        </button>
      </div>

      {/* ── Empty state ─────────────────────────────────────────────── */}
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-20 dark:border-surface-700 dark:bg-surface-900/50">
          <Brain className="mb-4 h-12 w-12 text-surface-400" />
          <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
            No knowledge bases yet
          </h3>
          <p className="mb-6 max-w-md text-center text-sm text-surface-500">
            Create your first knowledge base to enable semantic search and
            RAG-augmented AI chat with your documents.
          </p>
          <button
            onClick={() => {
              resetForm()
              setShowCreate(true)
            }}
            className="flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
          >
            <Plus size={16} />
            Create Your First KB
          </button>
        </div>
      ) : (
        /* ── Card grid ─────────────────────────────────────────────── */
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((kb) => (
            <button
              key={kb.id}
              onClick={() => navigate(`/knowledge/${kb.id}`)}
              className="group relative rounded-xl border border-surface-200 bg-white p-5 text-left transition-all hover:border-primary-300 hover:shadow-sm dark:border-surface-800 dark:bg-surface-950 dark:hover:border-primary-700"
            >
              {/* Delete button */}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setDeleteTarget(kb)
                }}
                className="absolute right-3 top-3 rounded-lg p-1.5 text-surface-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-red-900/20"
                title="Delete knowledge base"
              >
                <Trash2 size={14} />
              </button>

              {/* Icon + Name */}
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400">
                  <BookOpen size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-base font-semibold text-surface-900 dark:text-white">
                    {kb.name}
                  </h3>
                </div>
              </div>

              {/* Description */}
              {kb.description && (
                <p className="mb-4 line-clamp-2 text-sm text-surface-500">
                  {kb.description}
                </p>
              )}

              {/* Stats row */}
              <div className="flex flex-wrap items-center gap-3 text-xs text-surface-400">
                <span className="flex items-center gap-1">
                  <FileText size={12} />
                  {kb.document_count} docs
                </span>
                <span className="flex items-center gap-1">
                  <Layers size={12} />
                  {kb.total_chunks} chunks
                </span>
                <span className="flex items-center gap-1">
                  <Cpu size={12} />
                  {kb.embedding_model}
                </span>
              </div>

              {/* Date */}
              <p className="mt-2 text-xs text-surface-400">
                Created {new Date(kb.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* ── Create Dialog ───────────────────────────────────────────── */}
      {showCreate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => {
            setShowCreate(false)
            resetForm()
          }}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-700 dark:bg-surface-950"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                Create Knowledge Base
              </h2>
              <button
                onClick={() => {
                  setShowCreate(false)
                  resetForm()
                }}
                className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              {/* Name */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g., Product Documentation"
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                  autoFocus
                  maxLength={255}
                />
              </div>

              {/* Description */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Description
                </label>
                <textarea
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="What is this knowledge base for?"
                  rows={3}
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                  maxLength={10000}
                />
              </div>

              {/* Embedding model */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Embedding Model
                </label>
                <select
                  value={formModel}
                  onChange={(e) => setFormModel(e.target.value)}
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                >
                  <option value="text-embedding-3-small">text-embedding-3-small</option>
                  <option value="text-embedding-3-large">text-embedding-3-large</option>
                  <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                </select>
              </div>

              {formError && (
                <p className="text-sm text-red-500">{formError}</p>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreate(false)
                    resetForm()
                  }}
                  className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Plus size={16} />
                  )}
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Delete confirmation ─────────────────────────────────────── */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="w-full max-w-sm rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-700 dark:bg-surface-950"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
              Delete Knowledge Base?
            </h2>
            <p className="mb-1 text-sm text-surface-500">
              This will permanently delete
              {' "'}
              {deleteTarget.name}
              {'" '}
              and all its documents and embeddings.
            </p>
            <p className="mb-5 text-sm text-red-500">This action cannot be undone.</p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                {deleteMutation.isPending ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Trash2 size={16} />
                )}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
