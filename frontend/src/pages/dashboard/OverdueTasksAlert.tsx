/** OverdueTasksAlert — warning banner listing overdue tasks. */

import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronRight, Clock, Loader2, X } from 'lucide-react'
import { useState } from 'react'
import type { TaskResponse } from '@/types/task'

interface OverdueTasksAlertProps {
  tasks: TaskResponse[]
  loading?: boolean
  error?: string | null
  total: number
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function OverdueTasksAlert({ tasks, loading, error, total }: OverdueTasksAlertProps) {
  const [dismissed, setDismissed] = useState(false)
  const navigate = useNavigate()

  if (dismissed || total === 0) return null

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10">
      <div className="flex items-start gap-3 px-4 py-3">
        {loading ? (
          <Loader2 size={18} className="mt-0.5 shrink-0 animate-spin text-red-400" />
        ) : (
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-500" />
        )}
        <div className="min-w-0 flex-1">
          {error ? (
            <p className="text-sm text-red-500">{error}</p>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-red-700 dark:text-red-300">
                  {total} overdue task{total !== 1 ? 's' : ''}
                </p>
                <button
                  onClick={() => setDismissed(true)}
                  className="rounded p-0.5 text-red-400 hover:text-red-600 dark:hover:text-red-200"
                  title="Dismiss"
                >
                  <X size={14} />
                </button>
              </div>
              {tasks.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {tasks.slice(0, 5).map((task) => (
                    <li key={task.id}>
                      <button
                        onClick={() => navigate(`/tasks/${task.id}`)}
                        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-red-600 transition-colors hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/20"
                      >
                        <Clock size={12} className="shrink-0" />
                        <span className="flex-1 truncate">{task.title}</span>
                        {task.due_date && (
                          <span className="shrink-0 text-xs text-red-400">
                            Due {formatDate(task.due_date)}
                          </span>
                        )}
                        <ChevronRight size={12} className="shrink-0 text-red-300" />
                      </button>
                    </li>
                  ))}
                  {total > 5 && (
                    <li className="px-2 py-1">
                      <button
                        onClick={() => navigate('/tasks?status=todo,in_progress,review')}
                        className="text-xs font-medium text-red-500 hover:text-red-700 dark:hover:text-red-300"
                      >
                        View all {total} overdue tasks
                      </button>
                    </li>
                  )}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
