/** TaskCalendar — month-grid calendar showing tasks on their due dates. */

import { useState, useMemo } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  RefreshCw,
  CalendarDays,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TaskCard } from './TaskCard'
import type { TaskResponse } from '@/types/task'

// ── Props ──────────────────────────────────────────────────────────────────

interface TaskCalendarProps {
  tasks: TaskResponse[] | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
  onRetry: () => void
  /** Callback when month changes so parent can fetch new range. */
  onMonthChange: (start: string, end: string) => void
}

// ── Component ──────────────────────────────────────────────────────────────

export function TaskCalendar({
  tasks,
  isLoading,
  isError,
  error,
  onRetry,
  onMonthChange,
}: TaskCalendarProps) {
  const today = useMemo(() => new Date(), [])
  const [viewDate, setViewDate] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1))

  // Group tasks by date key (YYYY-MM-DD)
  const tasksByDate = useMemo(() => {
    const map = new Map<string, TaskResponse[]>()
    if (!tasks) return map
    for (const task of tasks) {
      if (!task.due_date) continue
      const key = task.due_date.slice(0, 10)
      const existing = map.get(key) ?? []
      existing.push(task)
      map.set(key, existing)
    }
    return map
  }, [tasks])

  // Navigate months
  const goToPrevMonth = () => {
    const prev = new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1)
    setViewDate(prev)
    notifyChange(prev)
  }

  const goToNextMonth = () => {
    const next = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1)
    setViewDate(next)
    notifyChange(next)
  }

  const goToToday = () => {
    const now = new Date(today.getFullYear(), today.getMonth(), 1)
    setViewDate(now)
    notifyChange(now)
  }

  const notifyChange = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const start = new Date(year, month, 1).toISOString().slice(0, 10)
    const end = new Date(year, month + 1, 0).toISOString().slice(0, 10)
    onMonthChange(start, end)
  }

  // Calendar grid
  const { grid, monthLabel } = useMemo(() => {
    const year = viewDate.getFullYear()
    const month = viewDate.getMonth()
    const firstDay = new Date(year, month, 1).getDay() // 0=Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    const label = new Date(year, month).toLocaleDateString(undefined, {
      month: 'long',
      year: 'numeric',
    })

    const weeks: (number | null)[][] = []
    let week: (number | null)[] = []

    // Leading blanks
    for (let i = 0; i < firstDay; i++) {
      week.push(null)
    }

    for (let day = 1; day <= daysInMonth; day++) {
      week.push(day)
      if (week.length === 7) {
        weeks.push(week)
        week = []
      }
    }

    // Trailing blanks
    while (week.length < 7) {
      week.push(null)
    }
    if (week.length > 0) {
      weeks.push(week)
    }

    return { grid: weeks, monthLabel: label }
  }, [viewDate])

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
        <AlertCircle size={32} className="text-red-400" />
        <div>
          <p className="text-base font-medium text-red-700 dark:text-red-300">
            Failed to load calendar
          </p>
          <p className="mt-1 text-sm text-red-500">
            {error?.message ?? 'An unexpected error occurred.'}
          </p>
        </div>
        <button
          onClick={onRetry}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
        >
          <RefreshCw size={14} className="mr-1.5 inline" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      {/* ── Calendar header ──────────────────────────────────────────────── */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrevMonth}
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
          >
            <ChevronLeft size={18} />
          </button>
          <h3 className="text-base font-semibold text-surface-900 dark:text-white">
            {monthLabel}
          </h3>
          <button
            onClick={goToNextMonth}
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <button
          onClick={goToToday}
          className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 hover:bg-surface-50 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-400 dark:hover:bg-surface-900"
        >
          <CalendarDays size={14} />
          Today
        </button>
      </div>

      {/* ── Calendar grid ────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-surface-200 dark:border-surface-800">
          {dayNames.map((name) => (
            <div
              key={name}
              className="px-2 py-2 text-center text-[11px] font-medium uppercase text-surface-400"
            >
              {name}
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="divide-y divide-surface-100 dark:divide-surface-800">
          {grid.map((week, weekIdx) => (
            <div key={weekIdx} className="grid min-h-[100px] grid-cols-7">
              {week.map((day, dayIdx) => {
                if (day === null) {
                  return (
                    <div
                      key={`blank-${dayIdx}`}
                      className="border-r border-surface-100 bg-surface-50 dark:border-surface-800 dark:bg-surface-900/30 last:border-r-0"
                    />
                  )
                }

                const dateKey = `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                const dayTasks = tasksByDate.get(dateKey) ?? []
                const isToday =
                  today.getFullYear() === viewDate.getFullYear() &&
                  today.getMonth() === viewDate.getMonth() &&
                  today.getDate() === day

                return (
                  <div
                    key={dateKey}
                    className={cn(
                      'min-h-[100px] border-r border-surface-100 p-1.5 last:border-r-0 dark:border-surface-800',
                      isToday && 'bg-primary-50/40 dark:bg-primary-900/10',
                    )}
                  >
                    <span
                      className={cn(
                        'mb-1 inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-medium',
                        isToday
                          ? 'bg-primary-500 text-white'
                          : 'text-surface-600 dark:text-surface-400',
                      )}
                    >
                      {day}
                    </span>
                    <div className="space-y-0.5">
                      {dayTasks.slice(0, 3).map((task) => (
                        <a
                          key={task.id}
                          href={`/tasks/${task.id}`}
                          onClick={(e) => {
                            e.preventDefault()
                            window.location.href = `/tasks/${task.id}`
                          }}
                          className={cn(
                            'block truncate rounded px-1 py-0.5 text-[10px] font-medium leading-tight transition-colors hover:opacity-80',
                            task.status === 'done'
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                              : task.priority === 'critical' || task.priority === 'high'
                                ? 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
                          )}
                        >
                          {task.title}
                        </a>
                      ))}
                      {dayTasks.length > 3 && (
                        <span className="block px-1 text-[10px] text-surface-400">
                          +{dayTasks.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* ── Selected-day detail panel ─────────────────────────────────────── */}
      {tasks && tasks.length > 0 && (
        <div className="mt-6">
          <h4 className="mb-3 text-sm font-semibold text-surface-900 dark:text-white">
            Tasks with due dates this month
          </h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {tasks
              .filter((t) => t.due_date)
              .slice(0, 12)
              .map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
