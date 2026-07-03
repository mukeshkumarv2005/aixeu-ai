/** SearchBar — debounced input with dropdown, entity filters, recent searches.
 *
 * Shows a text input with Cmd+K / Ctrl+K keyboard shortcut. When focused and
 * the input is empty, displays recent searches. While typing, performs a live
 * search and shows a results dropdown with entity-type filter chips.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  X,
  Loader2,
  MessageSquare,
  MessagesSquare,
  FileText,
  BookOpen,
  CheckSquare,
  Clock,
  TrendingUp,
  ArrowRight,
  Command,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useGlobalSearch,
  useRecentSearches,
  useRecordRecentSearch,
} from '@/api/search'
import type { SearchResult } from '@/types/search'
import { ENTITY_TYPES } from '@/types/search'

// ---------------------------------------------------------------------------
// Entity-type icon map
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

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SearchBarProps {
  /** If true, navigates to /search on Enter instead of showing dropdown. */
  navigateOnEnter?: boolean
  placeholder?: string
  className?: string
  /** Called when the user selects a search result. */
  onResultSelect?: () => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SearchBar({
  navigateOnEnter = false,
  placeholder = 'Search across everything…',
  className,
  onResultSelect,
}: SearchBarProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  // Debounce search input
  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(query)
    }, 250)
    return () => clearTimeout(timerRef.current)
  }, [query])

  // Queries
  const {
    data: searchData,
    isLoading: searchLoading,
  } = useGlobalSearch({
    q: debouncedQuery,
    entity_types: selectedTypes.length > 0 ? selectedTypes.join(',') : undefined,
    limit: 8,
  })

  const { data: recentSearches } = useRecentSearches()
  const { mutate: recordRecent } = useRecordRecentSearch()

  // Show recent searches when focused + empty; show dropdown when typing
  const showRecent = isFocused && !debouncedQuery && recentSearches && recentSearches.length > 0
  const showResults = isFocused && debouncedQuery.length > 0

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false)
        setIsFocused(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        setIsFocused(true)
        setShowDropdown(true)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleSelectResult = useCallback(
    (result: SearchResult) => {
      recordRecent(query || result.title)
      onResultSelect?.()
      setShowDropdown(false)
      setIsFocused(false)
      navigate(result.url)
    },
    [navigate, onResultSelect, query, recordRecent],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowDropdown(false)
        setIsFocused(false)
        inputRef.current?.blur()
      }
      if (e.key === 'Enter') {
        if (debouncedQuery) {
          recordRecent(debouncedQuery)
          if (navigateOnEnter) {
            navigate(`/search?q=${encodeURIComponent(debouncedQuery)}`)
          } else {
            // Navigate to full search page
            navigate(`/search?q=${encodeURIComponent(debouncedQuery)}`)
          }
          setShowDropdown(false)
          setIsFocused(false)
          onResultSelect?.()
        }
      }
    },
    [debouncedQuery, navigate, navigateOnEnter, onResultSelect, recordRecent],
  )

  const handleClear = useCallback(() => {
    setQuery('')
    setDebouncedQuery('')
    inputRef.current?.focus()
  }, [])

  const toggleType = useCallback((type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
  }, [])

  const handleRecentClick = useCallback(
    (q: string) => {
      setQuery(q)
      setDebouncedQuery(q)
      inputRef.current?.focus()
    },
    [],
  )

  return (
    <div className={cn('relative', className)}>
      {/* ── Input ──────────────────────────────────────────────── */}
      <div
        className={cn(
          'flex items-center gap-2 rounded-xl border bg-white px-3 py-2.5 shadow-sm transition-all dark:bg-surface-950',
          isFocused
            ? 'border-primary-400 ring-2 ring-primary-100 dark:border-primary-500 dark:ring-primary-900/20'
            : 'border-surface-200 dark:border-surface-800',
        )}
      >
        <Search size={16} className="shrink-0 text-surface-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setShowDropdown(true)
          }}
          onFocus={() => {
            setIsFocused(true)
            setShowDropdown(true)
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent text-sm text-surface-900 outline-none placeholder:text-surface-400 dark:text-white"
        />
        {query && (
          <button
            onClick={handleClear}
            className="rounded p-0.5 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
          >
            <X size={14} />
          </button>
        )}
        <kbd className="hidden shrink-0 items-center gap-0.5 rounded-md border border-surface-200 bg-surface-50 px-1.5 py-0.5 text-[10px] font-medium text-surface-400 dark:border-surface-700 dark:bg-surface-900 md:flex">
          <Command size={10} />
          K
        </kbd>
      </div>

      {/* ── Dropdown ───────────────────────────────────────────── */}
      {showDropdown && isFocused && (
        <div
          ref={dropdownRef}
          className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-xl border border-surface-200 bg-white shadow-lg dark:border-surface-800 dark:bg-surface-950"
        >
          {/* ── Entity type filter chips ────────────────────────── */}
          <div className="flex flex-wrap gap-1.5 border-b border-surface-100 px-3 py-2 dark:border-surface-800">
            {ENTITY_TYPES.map((type) => {
              const active = selectedTypes.includes(type.value)
              return (
                <button
                  key={type.value}
                  onClick={() => toggleType(type.value)}
                  className={cn(
                    'rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors',
                    active
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                      : 'bg-surface-100 text-surface-500 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:hover:bg-surface-700',
                  )}
                >
                  {type.label}
                </button>
              )
            })}
          </div>

          {/* ── Recent searches ────────────────────────────────── */}
          {showRecent && (
            <div className="p-2">
              <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wider text-surface-400">
                Recent searches
              </p>
              {recentSearches.slice(0, 5).map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleRecentClick(r.query)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800"
                >
                  <Clock size={12} className="shrink-0 text-surface-400" />
                  <span className="truncate">{r.query}</span>
                </button>
              ))}
            </div>
          )}

          {/* ── Search results ─────────────────────────────────── */}
          {showResults && (
            <div className="max-h-80 overflow-y-auto">
              {/* Loading */}
              {searchLoading && (
                <div className="flex items-center justify-center gap-2 py-6">
                  <Loader2 size={16} className="animate-spin text-surface-400" />
                  <span className="text-xs text-surface-400">Searching…</span>
                </div>
              )}

              {/* Results */}
              {!searchLoading && searchData && searchData.results.length > 0 && (
                <>
                  <div className="divide-y divide-surface-100 dark:divide-surface-800">
                    {searchData.results.map((result, idx) => {
                      const Icon =
                        ENTITY_ICONS[result.entity_type] ?? Search
                      const colorClass =
                        ENTITY_COLORS[result.entity_type] ??
                        'bg-surface-100 text-surface-500'
                      return (
                        <button
                          key={`${result.entity_type}-${result.entity_id}-${idx}`}
                          onClick={() => handleSelectResult(result)}
                          className="flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
                        >
                          <span
                            className={cn(
                              'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg',
                              colorClass,
                            )}
                          >
                            <Icon size={14} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-surface-900 dark:text-white">
                              {result.title}
                            </p>
                            <p className="mt-0.5 line-clamp-1 text-xs text-surface-500">
                              {result.snippet}
                            </p>
                          </div>
                          <span className="shrink-0 self-center text-[10px] font-medium text-surface-400">
                            {Math.round(result.score * 100)}%
                          </span>
                        </button>
                      )
                    })}
                  </div>

                  {/* View all results */}
                  {searchData.total > searchData.results.length && (
                    <button
                      onClick={() => {
                        recordRecent(debouncedQuery)
                        navigate(
                          `/search?q=${encodeURIComponent(debouncedQuery)}`,
                        )
                        setShowDropdown(false)
                        setIsFocused(false)
                        onResultSelect?.()
                      }}
                      className="flex w-full items-center justify-center gap-1 border-t border-surface-100 px-3 py-2 text-xs font-medium text-primary-600 transition-colors hover:bg-primary-50 dark:border-surface-800 dark:text-primary-400 dark:hover:bg-primary-900/20"
                    >
                      View all {searchData.total} results
                      <ArrowRight size={12} />
                    </button>
                  )}
                </>
              )}

              {/* No results */}
              {!searchLoading &&
                searchData &&
                searchData.results.length === 0 && (
                  <div className="flex flex-col items-center gap-1 px-4 py-6 text-center">
                    <TrendingUp
                      size={24}
                      className="text-surface-300 dark:text-surface-600"
                    />
                    <p className="text-sm text-surface-500">
                      No results for &ldquo;{debouncedQuery}&rdquo;
                    </p>
                    <p className="text-xs text-surface-400">
                      Try different keywords or adjust filters
                    </p>
                  </div>
                )}

              {/* Error */}
              {!searchLoading && !searchData && debouncedQuery && (
                <div className="px-4 py-6 text-center">
                  <p className="text-xs text-red-500">
                    Search failed. Please try again.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
