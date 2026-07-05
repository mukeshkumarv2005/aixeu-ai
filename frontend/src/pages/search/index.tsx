/** SearchPage — full search results page with filters, pagination, saved searches.
 *
 * Displays a large search bar at the top, then lists results grouped by entity
 * type when the user performs a search. Includes a sidebar with entity-type
 * filters, saved-search management, and pagination controls.
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Search,
  X,
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  MessagesSquare,
  FileText,
  BookOpen,
  CheckSquare,
  Bookmark,
  Trash2,
  Plus,
  Clock,
  SlidersHorizontal,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useGlobalSearch,
  useSavedSearches,
  useSaveSearch,
  useDeleteSavedSearch,
  useRecentSearches,
  useRecordRecentSearch,
} from '@/api/search'
import type { SearchResult } from '@/types/search'

// ---------------------------------------------------------------------------
// Entity-type icon & color maps
// ---------------------------------------------------------------------------

const ENTITY_ICONS: Record<string, typeof MessageSquare> = {
  conversation: MessageSquare,
  message: MessagesSquare,
  file: FileText,
  kb_document: BookOpen,
  task: CheckSquare,
}

const ENTITY_COLORS: Record<string, string> = {
  conversation:
    'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  message:
    'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400',
  file: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
  kb_document:
    'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400',
  task: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
}

const ENTITY_LABELS: Record<string, string> = {
  conversation: 'Conversation',
  message: 'Message',
  file: 'File',
  kb_document: 'Knowledge Base',
  task: 'Task',
}

// ── Defaults ──────────────────────────────────────────────────────────────

const UI_FILTER_TYPES = [
  { value: 'chat', label: 'Chat' },
  { value: 'file', label: 'Files' },
  { value: 'kb_document', label: 'Knowledge Base' },
  { value: 'task', label: 'Tasks' },
]

const PAGE_SIZE = 20

// ── Component ─────────────────────────────────────────────────────────────

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // ── State from URL params ────────────────────────────────────────────
  const queryFromUrl = searchParams.get('q') ?? ''
  const typeFromUrl = searchParams.get('entity_types') ?? ''
  const pageFromUrl = parseInt(searchParams.get('page') ?? '1', 10)

  const [query, setQuery] = useState(queryFromUrl)
  const [selectedTypes, setSelectedTypes] = useState<string[]>(
    typeFromUrl ? typeFromUrl.split(',') : [],
  )
  const [showFilters, setShowFilters] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [_showSavedManager, _setShowSavedManager] = useState(false)

  const offset = (pageFromUrl - 1) * PAGE_SIZE

  // ── Queries ───────────────────────────────────────────────────────────
  const {
    data: searchData,
    isLoading: searchLoading,
    isError: searchError,
    error: searchErr,
    refetch: refetchSearch,
  } = useGlobalSearch({
    q: queryFromUrl,
    entity_types: selectedTypes.length > 0 ? selectedTypes.join(',') : undefined,
    status: statusFilter || undefined,
    priority: priorityFilter || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    offset,
    limit: PAGE_SIZE,
  })

  const { data: savedSearches } = useSavedSearches()
  const { data: recentSearches } = useRecentSearches()
  const { mutate: saveSearch, isPending: savingSearch } = useSaveSearch()
  const { mutate: deleteSavedSearch } = useDeleteSavedSearch()
  const { mutate: recordRecent } = useRecordRecentSearch()

  // Sync URL when filters change
  const updateUrl = useCallback(
    (q: string, types: string[], page: number) => {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (types.length > 0) params.set('entity_types', types.join(','))
      if (page > 1) params.set('page', String(page))
      setSearchParams(params, { replace: true })
    },
    [setSearchParams],
  )

  const handleSearch = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault()
      if (!query.trim()) return
      recordRecent(query.trim())
      updateUrl(query.trim(), selectedTypes, 1)
    },
    [query, selectedTypes, updateUrl, recordRecent],
  )

  const toggleType = useCallback(
    (type: string) => {
      setSelectedTypes((prev) => {
        let next: string[]
        if (type === 'chat') {
          const hasChat = prev.includes('conversation') || prev.includes('message')
          if (hasChat) {
            next = prev.filter((t) => t !== 'conversation' && t !== 'message')
          } else {
            next = [...prev, 'conversation', 'message']
          }
        } else {
          next = prev.includes(type)
            ? prev.filter((t) => t !== type)
            : [...prev, type]
        }
        updateUrl(query, next, 1)
        return next
      })
    },
    [query, updateUrl],
  )

  const handlePageChange = useCallback(
    (page: number) => {
      updateUrl(queryFromUrl, selectedTypes, page)
    },
    [queryFromUrl, selectedTypes, updateUrl],
  )

  const totalPages = searchData
    ? Math.ceil(searchData.total / PAGE_SIZE)
    : 0

  // Record recent search on initial load
  useEffect(() => {
    if (queryFromUrl) {
      recordRecent(queryFromUrl)
    }
    // Only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSaveSearch = useCallback(() => {
    if (!queryFromUrl) return
    saveSearch({
      query: queryFromUrl,
      filters:
        selectedTypes.length > 0
          ? { entity_types: selectedTypes }
          : undefined,
    })
  }, [queryFromUrl, selectedTypes, saveSearch])

  return (
    <div className="mx-auto w-full max-w-7xl">
      {/* ── Hero search ──────────────────────────────────────────── */}
      <div className="border-b border-surface-200 bg-gradient-to-b from-surface-50 to-white px-4 pb-6 pt-6 dark:border-surface-800 dark:from-surface-950 dark:to-surface-950 sm:px-6">
        <form onSubmit={handleSearch} className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2 rounded-xl border border-surface-200 bg-white px-4 py-3 shadow-sm transition-all focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 dark:border-surface-800 dark:bg-surface-950 dark:focus-within:border-primary-500 dark:focus-within:ring-primary-900/20">
            <Search size={18} className="shrink-0 text-surface-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search conversations, files, tasks, knowledge base…"
              className="min-w-0 flex-1 bg-transparent text-base text-surface-900 outline-none placeholder:text-surface-400 dark:text-white border-0 focus:ring-0 focus:border-0 focus:outline-none"
              autoFocus
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="rounded p-0.5 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
              >
                <X size={16} />
              </button>
            )}
            <button
              type="submit"
              disabled={!query.trim() || searchLoading}
              className="rounded-lg bg-primary-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
            >
              {searchLoading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                'Search'
              )}
            </button>
          </div>
        </form>

        {/* Entity type chips */}
        <div className="mx-auto mt-3 flex max-w-3xl flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-surface-400">
            Filter:
          </span>
          {UI_FILTER_TYPES.map((type) => {
            const active = type.value === 'chat'
              ? selectedTypes.includes('conversation') || selectedTypes.includes('message')
              : selectedTypes.includes(type.value)
            return (
              <button
                key={type.value}
                onClick={() => toggleType(type.value)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                  active
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                    : 'bg-surface-100 text-surface-500 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:hover:bg-surface-700',
                )}
              >
                {type.label}
              </button>
            )
          })}

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'ml-auto flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
              showFilters || statusFilter || priorityFilter || dateFrom || dateTo
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                : 'text-surface-500 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800',
            )}
          >
            <SlidersHorizontal size={12} />
            Filters
          </button>
        </div>

        {/* Advanced filters */}
        {showFilters && (
          <div className="mx-auto mt-3 flex max-w-3xl flex-wrap items-center gap-3 rounded-lg border border-surface-200 bg-surface-50 p-3 dark:border-surface-800 dark:bg-surface-900/50">
            <div className="flex items-center gap-2">
              <label className="text-xs text-surface-500">Status:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-surface-200 bg-white px-2 py-1 text-xs text-surface-700 outline-none dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300"
              >
                <option value="">Any</option>
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="done">Done</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-surface-500">Priority:</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="rounded-lg border border-surface-200 bg-white px-2 py-1 text-xs text-surface-700 outline-none dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300"
              >
                <option value="">Any</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="shrink-0 text-xs text-surface-500">From:</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-lg border border-surface-200 bg-white px-2 py-1 text-xs text-surface-700 outline-none dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="shrink-0 text-xs text-surface-500">To:</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-lg border border-surface-200 bg-white px-2 py-1 text-xs text-surface-700 outline-none dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300"
              />
            </div>
            {(statusFilter || priorityFilter || dateFrom || dateTo) && (
              <button
                onClick={() => {
                  setStatusFilter('')
                  setPriorityFilter('')
                  setDateFrom('')
                  setDateTo('')
                }}
                className="text-xs text-red-500 hover:text-red-600"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Main content ────────────────────────────────────────── */}
      <div className="flex gap-6 px-4 pb-12 pt-6 sm:px-6">
        {/* ── Sidebar ──────────────────────────────────────────── */}
        <aside className="hidden w-64 shrink-0 lg:block">
          {/* Saved searches */}
          <div className="mb-6">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-surface-500">
                <Bookmark size={14} />
                Saved Searches
              </h3>
              {queryFromUrl && (
                <button
                  onClick={handleSaveSearch}
                  disabled={savingSearch}
                  className="flex items-center gap-0.5 text-[11px] font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
                >
                  <Plus size={12} />
                  Save current
                </button>
              )}
            </div>
            {savedSearches && savedSearches.length > 0 ? (
              <div className="space-y-0.5">
                {savedSearches.map((s) => (
                  <div
                    key={s.id}
                    className="group flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-surface-100 dark:hover:bg-surface-800"
                  >
                    <button
                      onClick={() => {
                        setQuery(s.query)
                        updateUrl(s.query, [], 1)
                      }}
                      className="min-w-0 flex-1 truncate text-left text-xs text-surface-700 hover:text-surface-900 dark:text-surface-300 dark:hover:text-white"
                    >
                      {s.query}
                    </button>
                    <button
                      onClick={() => deleteSavedSearch(s.id)}
                      className="shrink-0 p-0.5 text-surface-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                      title="Delete saved search"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-surface-400">
                {queryFromUrl
                  ? 'Save this search to access it later.'
                  : 'No saved searches yet.'}
              </p>
            )}
          </div>

          {/* Recent searches */}
          <div>
            <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-surface-500">
              <Clock size={14} />
              Recent
            </h3>
            {recentSearches && recentSearches.length > 0 ? (
              <div className="space-y-0.5">
                {recentSearches.slice(0, 10).map((r) => (
                  <button
                    key={r.id}
                    onClick={() => {
                      setQuery(r.query)
                      updateUrl(r.query, selectedTypes, 1)
                    }}
                    className="block w-full truncate rounded-lg px-2 py-1.5 text-left text-xs text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800"
                  >
                    {r.query}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-surface-400">No recent searches.</p>
            )}
          </div>
        </aside>

        {/* ── Results area ──────────────────────────────────────── */}
        <div className="min-w-0 flex-1">
          {/* Page heading */}
          {queryFromUrl && (
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-surface-500">
                {searchLoading
                  ? 'Searching…'
                  : searchData
                    ? `${searchData.total} result${searchData.total !== 1 ? 's' : ''} for "${queryFromUrl}"`
                    : ''}
              </p>
              {searchData && searchData.total > 0 && (
                <span className="text-[11px] font-medium text-surface-400">
                  Page {pageFromUrl} of {totalPages || 1}
                </span>
              )}
            </div>
          )}

          {/* Initial empty state */}
          {!queryFromUrl && (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <Search
                size={48}
                className="text-surface-300 dark:text-surface-600"
              />
              <div>
                <h2 className="text-lg font-semibold text-surface-700 dark:text-surface-300">
                  Search across everything
                </h2>
                <p className="mt-1 text-sm text-surface-400">
                  Find conversations, files, knowledge base articles, tasks, and more.
                </p>
              </div>
            </div>
          )}

          {/* Loading */}
          {searchLoading && queryFromUrl && (
            <div className="flex items-center justify-center gap-2 py-16">
              <Loader2 size={20} className="animate-spin text-surface-400" />
              <span className="text-sm text-surface-500">Searching…</span>
            </div>
          )}

          {/* Error */}
          {searchError && !searchLoading && queryFromUrl && (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
              <AlertCircle size={28} className="text-red-400" />
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-300">
                  Search failed
                </p>
                <p className="mt-1 text-xs text-red-500">
                  {searchErr instanceof Error
                    ? searchErr.message
                    : 'An unexpected error occurred.'}
                </p>
              </div>
              <button
                onClick={() => refetchSearch()}
                className="flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                <RefreshCw size={12} />
                Retry
              </button>
            </div>
          )}

          {/* No results */}
          {!searchLoading &&
            !searchError &&
            queryFromUrl &&
            searchData &&
            searchData.results.length === 0 && (
              <div className="flex flex-col items-center gap-3 py-16 text-center">
                <Search
                  size={36}
                  className="text-surface-300 dark:text-surface-600"
                />
                <div>
                  <p className="text-sm font-medium text-surface-700 dark:text-surface-300">
                    No results found
                  </p>
                  <p className="mt-1 text-xs text-surface-400">
                    Try different keywords, adjust your filters, or search for
                    something more specific.
                  </p>
                </div>
              </div>
            )}

          {/* Results list */}
          {!searchLoading &&
            !searchError &&
            searchData &&
            searchData.results.length > 0 && (
              <>
                <div className="space-y-3">
                  {searchData.results.map((result, idx) => (
                    <ResultCard
                      key={`${result.entity_type}-${result.entity_id}-${idx}`}
                      result={result}
                    />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="mt-6 flex items-center justify-center gap-2">
                    <button
                      onClick={() => handlePageChange(pageFromUrl - 1)}
                      disabled={pageFromUrl <= 1}
                      className="flex items-center gap-1 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 transition-colors hover:bg-surface-50 disabled:opacity-40 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-400 dark:hover:bg-surface-900"
                    >
                      <ChevronLeft size={14} />
                      Previous
                    </button>

                    {Array.from(
                      { length: Math.min(totalPages, 7) },
                      (_, i) => {
                        // Show pages around current
                        let pageNum: number
                        if (totalPages <= 7) {
                          pageNum = i + 1
                        } else if (pageFromUrl <= 4) {
                          pageNum = i + 1
                        } else if (pageFromUrl >= totalPages - 3) {
                          pageNum = totalPages - 6 + i
                        } else {
                          pageNum = pageFromUrl - 3 + i
                        }
                        return pageNum
                      },
                    ).map((pageNum) => (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={cn(
                          'flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors',
                          pageNum === pageFromUrl
                            ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                            : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800',
                        )}
                      >
                        {pageNum}
                      </button>
                    ))}

                    <button
                      onClick={() => handlePageChange(pageFromUrl + 1)}
                      disabled={pageFromUrl >= totalPages}
                      className="flex items-center gap-1 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 transition-colors hover:bg-surface-50 disabled:opacity-40 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-400 dark:hover:bg-surface-900"
                    >
                      Next
                      <ChevronRight size={14} />
                    </button>
                  </div>
                )}
              </>
            )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ResultCard
// ---------------------------------------------------------------------------

interface ResultCardProps {
  result: SearchResult
}

function ResultCard({ result }: ResultCardProps) {
  const navigate = useNavigate()
  const Icon = ENTITY_ICONS[result.entity_type] ?? Search
  const colorClass =
    ENTITY_COLORS[result.entity_type] ?? 'bg-surface-100 text-surface-500'
  const entityLabel = ENTITY_LABELS[result.entity_type] ?? result.entity_type

  const handleClick = () => {
    navigate(result.url)
  }

  return (
    <button
      onClick={handleClick}
      className="group block w-full rounded-xl border border-surface-200 bg-white p-4 text-left shadow-sm transition-all hover:shadow-md dark:border-surface-800 dark:bg-surface-950"
    >
      <div className="flex items-start gap-3">
        {/* Entity type icon */}
        <span
          className={cn(
            'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
            colorClass,
          )}
        >
          <Icon size={16} />
        </span>

        <div className="min-w-0 flex-1">
          {/* Title */}
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-1 text-sm font-semibold text-surface-900 dark:text-white">
              {result.title}
            </h3>
            <span className="shrink-0 text-[10px] font-medium text-surface-400">
              {Math.round(result.score * 100)}% match
            </span>
          </div>

          {/* Entity type badge */}
          <span className="mt-0.5 inline-block text-[10px] font-medium uppercase tracking-wider text-surface-400">
            {entityLabel}
          </span>

          {/* Snippet */}
          <p className="mt-1 line-clamp-2 text-xs text-surface-500 dark:text-surface-400">
            {result.snippet}
          </p>

          {/* Metadata */}
          {Object.keys(result.entity_metadata).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {Boolean(result.entity_metadata.status) && (
                <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                  {String(result.entity_metadata.status)}
                </span>
              )}
              {Boolean(result.entity_metadata.priority) && (
                <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                  {String(result.entity_metadata.priority)}
                </span>
              )}
              {Boolean(result.entity_metadata.file_type) && (
                <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                  {String(result.entity_metadata.file_type)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  )
}
