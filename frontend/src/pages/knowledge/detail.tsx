/** Knowledge Base detail page.
 *
 * Displays KB metadata, documents list, and semantic search.
 * Tabs: Documents | Semantic Search.
 * States: loading, error, not-found, loaded.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Layers,
  Cpu,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  Search,
  X,
  Zap,
  Clock,
  Hash,
  ListTodo,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { RelatedTasksWidget } from '@/components/tasks/RelatedTasksWidget'
import { useAIConvertDocument } from '@/api/task-ai'
import {
  useKnowledgeBase,
  useKbDocuments,
  useAddKbDocument,
  useDeleteKbDocument,
  useProcessKbDocument,
  useSemanticSearch,
} from '@/api/knowledge'
import type {
  KnowledgeBaseDocumentResponse,
} from '@/types/knowledge'

type ActiveTab = 'documents' | 'search'

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
  processing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400',
}

export default function KnowledgeBaseDetailPage() {
  const { kbId } = useParams<{ kbId: string }>()
  const navigate = useNavigate()

  // ── Queries ──────────────────────────────────────────────────────────
  const {
    data: kb,
    isLoading: kbLoading,
    isError: kbError,
    error: kbErr,
  } = useKnowledgeBase(kbId)

  const {
    data: docsData,
    isLoading: docsLoading,
    isError: docsError,
    refetch: refetchDocs,
  } = useKbDocuments(kbId)

  // ── Mutations ────────────────────────────────────────────────────────
  const addDocMutation = useAddKbDocument(kbId ?? '')
  const deleteDocMutation = useDeleteKbDocument(kbId ?? '')
  const processDocMutation = useProcessKbDocument(kbId ?? '')
  const searchMutation = useSemanticSearch(kbId ?? '')
  const convertMutation = useAIConvertDocument()

  // ── Local state ──────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ActiveTab>('documents')
  const [showAddDoc, setShowAddDoc] = useState(false)
  const [convertError, setConvertError] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseDocumentResponse | null>(null)

  // Add document form
  const [docTitle, setDocTitle] = useState('')
  const [docContent, setDocContent] = useState('')
  const [docFormError, setDocFormError] = useState<string | null>(null)

  // Search form
  const [searchQuery, setSearchQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.0)

  // ── Loading KB ───────────────────────────────────────────────────────
  if (kbLoading) {
    return (
      <div className="flex h-full items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error / Not found ────────────────────────────────────────────────
  if (kbError || !kb) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p className="flex-1 text-sm">
            {(kbErr as Error)?.message ?? 'Knowledge base not found'}
          </p>
          <button
            onClick={() => navigate('/knowledge')}
            className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium hover:bg-red-200 dark:bg-red-800/30 dark:hover:bg-red-800/50"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  // ── Handlers ─────────────────────────────────────────────────────────
  const handleAddDocument = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!docTitle.trim() || !docContent.trim()) {
      setDocFormError('Title and content are required')
      return
    }
    setDocFormError(null)
    try {
      await addDocMutation.mutateAsync({
        title: docTitle.trim(),
        content: docContent.trim(),
      })
      setShowAddDoc(false)
      setDocTitle('')
      setDocContent('')
    } catch {
      setDocFormError('Failed to add document')
    }
  }

  const handleDeleteDocument = async () => {
    if (!deleteTarget) return
    try {
      await deleteDocMutation.mutateAsync(deleteTarget.id)
      setDeleteTarget(null)
    } catch {
      // handled by cache
    }
  }

  const handleProcessDocument = async (docId: string) => {
    try {
      await processDocMutation.mutateAsync(docId)
    } catch {
      // handled by cache
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    await searchMutation.mutateAsync({
      query: searchQuery.trim(),
      top_k: topK,
      similarity_threshold: similarityThreshold > 0 ? similarityThreshold : undefined,
    })
  }

  const handleConvertToTask = async () => {
    setConvertError(null)
    try {
      const res = await convertMutation.mutateAsync({
        document_id: kbId ?? '',
      })
      navigate('/tasks/create', {
        state: { draftFromConvert: res.task },
      })
    } catch (err: any) {
      setConvertError(err?.message ?? 'Failed to convert to task.')
    }
  }

  const documents = docsData?.items ?? []
  const searchResults = searchMutation.data?.results ?? []

  // ── Tab headers ──────────────────────────────────────────────────────
  const tabs: { key: ActiveTab; label: string; icon: typeof FileText }[] = [
    { key: 'documents', label: 'Documents', icon: FileText },
    { key: 'search', label: 'Semantic Search', icon: Search },
  ]

  return (
    <>
    <div className="mx-auto max-w-6xl px-4 py-6">
      {/* ── Back link ──────────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/knowledge')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
      >
        <ArrowLeft size={14} />
        Back to Knowledge Bases
      </button>

      {/* ── KB Header ──────────────────────────────────────────────── */}
      <div className="mb-6 rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-950">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400">
              <BookOpen size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
                {kb.name}
              </h1>
              {kb.description && (
                <p className="mt-1 text-sm text-surface-500">{kb.description}</p>
              )}
            </div>
          </div>

          {/* Convert to Task */}
          <button
            onClick={handleConvertToTask}
            disabled={convertMutation.isPending}
            className="flex items-center gap-2 rounded-lg border border-primary-200 bg-primary-50 px-3 py-2 text-sm font-medium text-primary-700 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-primary-900/30 dark:bg-primary-900/20 dark:text-primary-400 dark:hover:bg-primary-900/30 transition-colors"
          >
            {convertMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <ListTodo size={14} />
            )}
            {convertMutation.isPending ? 'Converting…' : 'Convert to Task'}
          </button>
        </div>

        {/* Convert error */}
        {convertError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-500">
            <AlertCircle size={14} />
            {convertError}
          </div>
        )}
        </div>

        {/* Stats row */}
        <div className="mt-5 flex flex-wrap gap-6 text-sm">
          <div className="flex items-center gap-2 text-surface-500">
            <FileText size={16} className="text-surface-400" />
            <span>
              <strong className="text-surface-900 dark:text-white">{kb.document_count}</strong> documents
            </span>
          </div>
          <div className="flex items-center gap-2 text-surface-500">
            <Layers size={16} className="text-surface-400" />
            <span>
              <strong className="text-surface-900 dark:text-white">{kb.total_chunks}</strong> chunks
            </span>
          </div>
          <div className="flex items-center gap-2 text-surface-500">
            <Cpu size={16} className="text-surface-400" />
            <span>{kb.embedding_model}</span>
          </div>
          <div className="flex items-center gap-2 text-surface-500">
            <Hash size={16} className="text-surface-400" />
            <span>{kb.dimension} dimensions</span>
          </div>
          <div className="flex items-center gap-2 text-surface-500">
            <Clock size={16} className="text-surface-400" />
            <span>
              Created {new Date(kb.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      {/* ── Related Tasks Widget ────────────────────────────────────── */}
      {kbId && (
        <div className="mb-4">
          <RelatedTasksWidget kbDocumentId={kbId} />
        </div>
      )}

      {/* ── Tabs ───────────────────────────────────────────────────── */}
      <div className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1 dark:bg-surface-800">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              'flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
              activeTab === key
                ? 'bg-white text-surface-900 shadow-sm dark:bg-surface-900 dark:text-white'
                : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-300',
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════ */}
      {/* TAB: Documents                                                */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'documents' && (
        <div>
          {/* Toolbar */}
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-surface-500">
              {docsData ? `${docsData.total} document(s)` : ''}
            </p>
            <button
              onClick={() => {
                setDocTitle('')
                setDocContent('')
                setDocFormError(null)
                setShowAddDoc(true)
              }}
              className="flex items-center gap-2 rounded-lg bg-primary-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
            >
              <Plus size={14} />
              Add Document
            </button>
          </div>

          {/* Documents list */}
          {docsLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-surface-400" />
            </div>
          ) : docsError ? (
            <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <p className="flex-1 text-sm">Failed to load documents</p>
              <button
                onClick={() => refetchDocs()}
                className="rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium hover:bg-red-200 dark:bg-red-800/30 dark:hover:bg-red-800/50"
              >
                Retry
              </button>
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-16 dark:border-surface-700 dark:bg-surface-900/50">
              <FileText className="mb-3 h-10 w-10 text-surface-400" />
              <h3 className="mb-1 text-base font-semibold text-surface-900 dark:text-white">
                No documents yet
              </h3>
              <p className="mb-4 text-sm text-surface-500">
                Add text documents to this knowledge base for indexing.
              </p>
              <button
                onClick={() => {
                  setDocTitle('')
                  setDocContent('')
                  setDocFormError(null)
                  setShowAddDoc(true)
                }}
                className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
              >
                <Plus size={14} />
                Add Your First Document
              </button>
            </div>
          ) : (
            /* Table */
            <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-200 bg-surface-50 dark:border-surface-800 dark:bg-surface-900">
                    <th className="px-4 py-3 text-left font-medium text-surface-500">Title</th>
                    <th className="hidden px-4 py-3 text-left font-medium text-surface-500 sm:table-cell">Status</th>
                    <th className="hidden px-4 py-3 text-right font-medium text-surface-500 md:table-cell">Chunks</th>
                    <th className="hidden px-4 py-3 text-left font-medium text-surface-500 lg:table-cell">Created</th>
                    <th className="px-4 py-3 text-right font-medium text-surface-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                  {documents.map((doc) => (
                    <tr
                      key={doc.id}
                      className="bg-white transition-colors hover:bg-surface-50 dark:bg-surface-950 dark:hover:bg-surface-900"
                    >
                      <td className="max-w-xs truncate px-4 py-3 font-medium text-surface-900 dark:text-white">
                        {doc.title}
                        {doc.error_message && (
                          <p className="mt-0.5 truncate text-xs text-red-500">{doc.error_message}</p>
                        )}
                      </td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <span
                          className={cn(
                            'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                            STATUS_BADGE[doc.status] ??
                              'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
                          )}
                        >
                          {doc.status}
                        </span>
                      </td>
                      <td className="hidden px-4 py-3 text-right text-surface-500 md:table-cell">
                        {doc.chunk_count}
                      </td>
                      <td className="hidden px-4 py-3 text-surface-500 lg:table-cell">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {doc.status !== 'completed' && (
                            <button
                              onClick={() => handleProcessDocument(doc.id)}
                              disabled={processDocMutation.isPending}
                              className="rounded-lg p-1.5 text-surface-400 hover:bg-blue-50 hover:text-blue-500 disabled:opacity-50 dark:hover:bg-blue-900/20"
                              title="Process document"
                            >
                              {processDocMutation.isPending ? (
                                <Loader2 size={14} className="animate-spin" />
                              ) : (
                                <Zap size={14} />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => setDeleteTarget(doc)}
                            className="rounded-lg p-1.5 text-surface-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                            title="Delete document"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════ */}
      {/* TAB: Semantic Search                                          */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'search' && (
        <div>
          {/* Search form */}
          <div className="mb-6 rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
            <form onSubmit={handleSearch} className="space-y-4">
              {/* Query input */}
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Search Query
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="What are you looking for?"
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                />
              </div>

              {/* Controls row */}
              <div className="flex flex-wrap items-end gap-4">
                <div className="flex-1">
                  <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                    Top K results: {topK}
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-full accent-primary-500"
                  />
                  <div className="flex justify-between text-xs text-surface-400">
                    <span>1</span>
                    <span>20</span>
                  </div>
                </div>
                <div className="flex-1">
                  <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                    Min Similarity: {similarityThreshold.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={10}
                    value={Math.round(similarityThreshold * 10)}
                    onChange={(e) => setSimilarityThreshold(Number(e.target.value) / 10)}
                    className="w-full accent-primary-500"
                  />
                  <div className="flex justify-between text-xs text-surface-400">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={searchMutation.isPending || !searchQuery.trim()}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {searchMutation.isPending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Search size={16} />
                  )}
                  Search
                </button>
              </div>
            </form>
          </div>

          {/* Results */}
          {searchMutation.isPending ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-surface-400" />
            </div>
          ) : searchMutation.isError ? (
            <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <p className="flex-1 text-sm">
                {(searchMutation.error as Error)?.message ?? 'Search failed'}
              </p>
            </div>
          ) : !searchMutation.data ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-16 dark:border-surface-700 dark:bg-surface-900/50">
              <Search className="mb-3 h-10 w-10 text-surface-400" />
              <h3 className="mb-1 text-base font-semibold text-surface-900 dark:text-white">
                Search your knowledge base
              </h3>
              <p className="text-sm text-surface-500">
                Enter a query above to find relevant documents.
              </p>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-16 dark:border-surface-700 dark:bg-surface-900/50">
              <Search className="mb-3 h-10 w-10 text-surface-400" />
              <h3 className="mb-1 text-base font-semibold text-surface-900 dark:text-white">
                No results found
              </h3>
              <p className="text-sm text-surface-500">
                Try a different query or lower the similarity threshold.
              </p>
            </div>
          ) : (
            <div>
              {/* Results header */}
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm text-surface-500">
                  Found {searchResults.length} result(s) in{' '}
                  {(searchMutation.data.search_time_ms / 1000).toFixed(2)}s
                </p>
                <p className="text-xs text-surface-400">
                  Model: {searchMutation.data.embedding_model}
                </p>
              </div>

              {/* Results list */}
              <div className="space-y-3">
                {searchResults.map((result, _i) => (
                  <div
                    key={`${result.document_id}-${result.chunk_index}`}
                    className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950"
                  >
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <h4 className="truncate text-sm font-semibold text-surface-900 dark:text-white">
                          {result.document_title}
                        </h4>
                        <p className="text-xs text-surface-400">
                          Chunk #{result.chunk_index + 1}
                        </p>
                      </div>
                      <span
                        className={cn(
                          'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                          result.similarity >= 0.8
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                            : result.similarity >= 0.6
                              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400'
                              : 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
                        )}
                      >
                        {(result.similarity * 100).toFixed(0)}% match
                      </span>
                    </div>
                    <p className="line-clamp-3 text-sm text-surface-600 dark:text-surface-400">
                      {result.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Add Document Dialog ──────────────────────────────────────── */}
      {showAddDoc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setShowAddDoc(false)}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-surface-200 bg-white p-6 shadow-xl dark:border-surface-700 dark:bg-surface-950"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                Add Document
              </h2>
              <button
                onClick={() => setShowAddDoc(false)}
                className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddDocument} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="Document title"
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                  autoFocus
                  maxLength={512}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                  Content <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={docContent}
                  onChange={(e) => setDocContent(e.target.value)}
                  placeholder="Document content to index..."
                  rows={8}
                  className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                />
              </div>

              {docFormError && (
                <p className="text-sm text-red-500">{docFormError}</p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddDoc(false)}
                  className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addDocMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {addDocMutation.isPending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Plus size={16} />
                  )}
                  Add
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Delete Document Confirmation ──────────────────────────────── */}
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
              Delete Document?
            </h2>
            <p className="mb-1 text-sm text-surface-500">
              This will permanently delete &ldquo;{deleteTarget.title}&rdquo;
              and its embeddings.
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
                onClick={handleDeleteDocument}
                disabled={deleteDocMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                {deleteDocMutation.isPending ? (
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
    </>
  )
}
