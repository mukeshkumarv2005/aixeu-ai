/** Agents page — list all agents with search, filter, and create. */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  SlidersHorizontal,
  Loader2,
  AlertCircle,
  X,
  Bot,
} from 'lucide-react'
import { useAgents } from '@/api/agents'
import { AgentCard } from '@/components/agents/AgentCard'

const DEFAULT_LIMIT = 50

export default function AgentsPage() {
  const navigate = useNavigate()

  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [enabledFilter, setEnabledFilter] = useState<string>('')

  // Search debounce
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchQuery(value)
      const timer = setTimeout(() => setDebouncedSearch(value), 300)
      return () => clearTimeout(timer)
    },
    [],
  )

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useAgents({
    search: debouncedSearch || undefined,
    limit: DEFAULT_LIMIT,
  })

  const agents = data?.items ?? []

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            AI Agents
          </h1>
          {data && (
            <p className="mt-1 text-sm text-surface-500">
              {data.total} agent{data.total !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <button
          onClick={() => navigate('/agents/new')}
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
        >
          <Plus size={16} />
          New Agent
        </button>
      </div>

      {/* ── Filters row ────────────────────────────────────────────────── */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative min-w-[200px] flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search agents..."
            className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-8 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('')
                setDebouncedSearch('')
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-surface-400 hover:text-surface-600"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Enabled filter */}
        <select
          value={enabledFilter}
          onChange={(e) => setEnabledFilter(e.target.value)}
          className="rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
        >
          <option value="">All agents</option>
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>

        {enabledFilter && (
          <button
            onClick={() => setEnabledFilter('')}
            className="flex items-center gap-1 rounded-lg border border-surface-300 px-3 py-2 text-xs font-medium text-surface-500 hover:bg-surface-50 dark:border-surface-600 dark:hover:bg-surface-800"
          >
            <SlidersHorizontal size={12} />
            Clear filters
          </button>
        )}
      </div>

      {/* ── Content ────────────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
          <AlertCircle size={32} className="text-red-400" />
          <div>
            <p className="text-base font-medium text-red-700 dark:text-red-300">
              Failed to load agents
            </p>
            <p className="mt-1 text-sm text-red-500">
              {(error as Error)?.message ?? 'An unexpected error occurred.'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-20 dark:border-surface-700 dark:bg-surface-900/50">
          <Bot className="mb-4 h-12 w-12 text-surface-400" />
          <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
            {debouncedSearch
              ? 'No matching agents'
              : 'No agents yet'}
          </h3>
          <p className="mb-6 max-w-md text-center text-sm text-surface-500">
            {debouncedSearch
              ? 'Try adjusting your search query.'
              : 'Create your first AI agent to automate tasks and answer questions.'}
          </p>
          {!debouncedSearch && (
            <button
              onClick={() => navigate('/agents/new')}
              className="flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
            >
              <Plus size={16} />
              Create Your First Agent
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Apply client-side enabled filter */}
          {(() => {
            const filtered =
              enabledFilter === 'true'
                ? agents.filter((a) => a.enabled)
                : enabledFilter === 'false'
                  ? agents.filter((a) => !a.enabled)
                  : agents

            if (filtered.length === 0) {
              return (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-16 dark:border-surface-700 dark:bg-surface-900/50">
                  <Bot className="mb-3 h-10 w-10 text-surface-400" />
                  <p className="text-sm text-surface-500">
                    No {enabledFilter === 'true' ? 'enabled' : 'disabled'} agents found.
                  </p>
                </div>
              )
            }

            return (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {filtered.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            )
          })()}

          {/* Pagination info */}
          {data && data.total > 0 && (
            <p className="mt-4 text-center text-xs text-surface-400">
              Showing {agents.length} of {data.total} agent{data.total !== 1 ? 's' : ''}
            </p>
          )}
        </>
      )}
    </div>
  )
}
