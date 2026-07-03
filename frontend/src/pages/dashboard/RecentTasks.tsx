/** RecentTasks — shows the 5 most recent tasks with clickable cards. */

import { useNavigate } from 'react-router-dom'
import { ListChecks, ArrowRight, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TaskResponse } from '@/types/task'
import { STATUS_CONFIG, PRIORITY_CONFIG } from '@/components/tasks/TaskCard'

interface RecentTasksProps {
  tasks: TaskResponse[]
  loading?: boolean
  error?: string | null
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export function RecentTasks({ tasks, loading, error }: RecentTasksProps) {
  const navigate = useNavigate()

  return (
    <WidgetCard title="Recent Tasks">
      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-2/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-2.5 w-1/4 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-sm text-red-500">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && tasks.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <ListChecks size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500">No tasks yet</p>
          <p className="text-xs text-surface-400">
            Create your first task to start tracking work.
          </p>
        </div>
      )}

      {/* Data */}
      {!loading && !error && tasks.length > 0 && (
        <div className="space-y-1">
          {tasks.slice(0, 5).map((task) => {
            const statusCfg = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.todo
            const priorityCfg = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium

            return (
              <button
                key={task.id}
                onClick={() => navigate(`/tasks/${task.id}`)}
                className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
              >
                <div className="rounded-lg bg-primary-50 p-1.5 text-primary-500 dark:bg-primary-900/20 dark:text-primary-400">
                  <ListChecks size={14} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                      {task.title}
                    </p>
                    <span className={cn('shrink-0 text-[10px] font-medium', priorityCfg.color)}>
                      {priorityCfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-surface-400">
                    <span className={cn('inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium', statusCfg.bg)}>
                      <span className={cn('h-1 w-1 rounded-full', statusCfg.dot)} />
                      {statusCfg.label}
                    </span>
                    <span>{formatDate(task.created_at)}</span>
                  </div>
                </div>
                <ArrowRight size={14} className="shrink-0 text-surface-300 dark:text-surface-600" />
              </button>
            )
          })}
        </div>
      )}
    </WidgetCard>
  )
}

function WidgetCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          {title}
        </h3>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}
