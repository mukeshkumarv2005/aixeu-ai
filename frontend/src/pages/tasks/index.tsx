/** Tasks page — list, board, and calendar views with filtering and search. */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  List,
  Columns,
  CalendarDays,
  Plus,
  Search,
  SlidersHorizontal,
  Loader2,
  AlertCircle,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useTasks,
  useTaskBoard,
  useTaskCalendar,
  useTaskStats,
} from '@/api/tasks'
import { TaskCard } from '@/components/tasks/TaskCard'
import { TaskKanban } from '@/components/tasks/TaskKanban'
import { TaskCalendar } from '@/components/tasks/TaskCalendar'
import { TASK_STATUSES, TASK_PRIORITIES } from '@/types/task'
import type { TaskResponse } from '@/types/task'

// ── Tab config ─────────────────────────────────────────────────────────────

type TabKey = 'list' | 'board' | 'calendar'

const TABS: { key: TabKey; label: string; icon: typeof List }[] = [
  { key: 'list', label: 'List', icon: List },
  { key: 'board', label: 'Board', icon: Columns },
  { key: 'calendar', label: 'Calendar', icon: CalendarDays },
]

// ── Default filters ────────────────────────────────────────────────────────

const DEFAULT_LIMIT = 50

// ── Component ──────────────────────────────────────────────────────────────

export default function TasksPage() {
  const navigate = useNavigate()

  // ── Tab state ──────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<TabKey>('list')

  // ── List filters ──────────────────────────────────────────────────────
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Search debounce
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchQuery(value)
      const timer = setTimeout(() => setDebouncedSearch(value), 300)
      return () => clearTimeout(timer)
    },
    [],
  )

  // ── Queries ───────────────────────────────────────────────────────────
  const {
    data: listData,
    isLoading: listLoading,
    isError: listError,
    error: listErr,
    refetch: refetchList,
  } = useTasks({
    status: statusFilter || undefined,
    priority: priorityFilter || undefined,
    search: debouncedSearch || undefined,
    limit: DEFAULT_LIMIT,
  })

  const {
    data: boardData,
    isLoading: boardLoading,
    isError: boardError,
    error: boardErr,
    refetch: refetchBoard,
  } = useTaskBoard()

  const [calStart, setCalStart] = useState<string>('')
  const [calEnd, setCalEnd] = useState<string>('')
  const {
    data: calData,
    isLoading: calLoading,
    isError: calError,
    error: calErr,
    refetch: refetchCal,
  } = useTaskCalendar(calStart || undefined, calEnd || undefined)

  // ── Stats badge ───────────────────────────────────────────────────────
  const { data: stats } = useTaskStats()

  // ── Calendar month change handler ─────────────────────────────────────
  const handleMonthChange = (start: string, end: string) => {
    setCalStart(start)
    setCalEnd(end)
  }

  // ── Active query ──────────────────────────────────────────────────────
  const tasks = listData?.items ?? []

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Tasks
          </h1>
          {stats && (
            <p className="mt-1 text-sm text-surface-500">
              {stats.total} total
              {stats.overdue > 0 && (
                <span className="ml-1.5 text-red-500">
                  &middot; {stats.overdue} overdue
                </span>
              )}
              {stats.critical > 0 && (
                <span className="ml-1.5 text-red-400">
                  &middot; {stats.critical} critical
                </span>
              )}
            </p>
          )}
        </div>
        <button
          onClick={() => navigate('/tasks/new')}
          className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
        >
          <Plus size={16} />
          New Task
        </button>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────────── */}
      <div className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1 dark:bg-surface-800">
        {TABS.map(({ key, label, icon: Icon }) => (
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
      {/* TAB: List                                                    */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'list' && (
        <div>
          {/* ── Filters row ───────────────────────────────────────── */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
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
                placeholder="Search tasks..."
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

            {/* Status filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            >
              <option value="">All statuses</option>
              {TASK_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>

            {/* Priority filter */}
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            >
              <option value="">All priorities</option>
              {TASK_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </option>
              ))}
            </select>

            {(statusFilter || priorityFilter) && (
              <button
                onClick={() => {
                  setStatusFilter('')
                  setPriorityFilter('')
                }}
                className="flex items-center gap-1 rounded-lg border border-surface-300 px-3 py-2 text-xs font-medium text-surface-500 hover:bg-surface-50 dark:border-surface-600 dark:hover:bg-surface-800"
              >
                <SlidersHorizontal size={12} />
                Clear filters
              </button>
            )}
          </div>

          {/* ── List content ────────────────────────────────────────── */}
          {listLoading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
            </div>
          ) : listError ? (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
              <AlertCircle size={32} className="text-red-400" />
              <div>
                <p className="text-base font-medium text-red-700 dark:text-red-300">
                  Failed to load tasks
                </p>
                <p className="mt-1 text-sm text-red-500">
                  {(listErr as Error)?.message ?? 'An unexpected error occurred.'}
                </p>
              </div>
              <button
                onClick={() => refetchList()}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-20 dark:border-surface-700 dark:bg-surface-900/50">
              <List className="mb-4 h-12 w-12 text-surface-400" />
              <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
                {debouncedSearch || statusFilter || priorityFilter
                  ? 'No matching tasks'
                  : 'No tasks yet'}
              </h3>
              <p className="mb-6 max-w-md text-center text-sm text-surface-500">
                {debouncedSearch || statusFilter || priorityFilter
                  ? 'Try adjusting your search or filters.'
                  : 'Create your first task to get started.'}
              </p>
              {!debouncedSearch && !statusFilter && !priorityFilter && (
                <button
                  onClick={() => navigate('/tasks/new')}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-600 transition-colors"
                >
                  <Plus size={16} />
                  Create Your First Task
                </button>
              )}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {tasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          )}

          {/* ── Pagination info ──────────────────────────────────────── */}
          {listData && listData.total > 0 && (
            <p className="mt-4 text-center text-xs text-surface-400">
              Showing {tasks.length} of {listData.total} task{listData.total !== 1 ? 's' : ''}
            </p>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════ */}
      {/* TAB: Board                                                   */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'board' && (
        <TaskKanban
          data={boardData as Record<string, TaskResponse[]> | undefined}
          isLoading={boardLoading}
          isError={boardError}
          error={boardErr}
          onRetry={refetchBoard}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════ */}
      {/* TAB: Calendar                                                */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'calendar' && (
        <TaskCalendar
          tasks={calData?.items}
          isLoading={calLoading}
          isError={calError}
          error={calErr}
          onRetry={refetchCal}
          onMonthChange={handleMonthChange}
        />
      )}
    </div>
  )
}
