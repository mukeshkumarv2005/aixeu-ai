/** AgentStatusWidget — aggregate agent counts: total, enabled, disabled. */

import { Bot, Loader2, AlertCircle, Power, PowerOff } from 'lucide-react'
import { useAgents } from '@/api/agents'
import { WidgetCard } from '@/components/dashboard/WidgetCard'

export function AgentStatusWidget() {
  const { data, isLoading, error } = useAgents({ limit: 100 })

  const total = data?.total ?? 0
  const enabled = data?.items.filter((a) => a.enabled).length ?? 0
  const disabled = total - enabled

  return (
    <WidgetCard title="Agents">
      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={20} className="animate-spin text-surface-400" />
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-sm text-red-500">
            {error instanceof Error
              ? error.message
              : 'Failed to load agents'}
          </p>
        </div>
      )}

      {/* Data / empty */}
      {!isLoading && !error && (
        <div>
          {total === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <Bot size={24} className="text-surface-300 dark:text-surface-600" />
              <p className="text-sm text-surface-500">No agents yet</p>
              <p className="text-xs text-surface-400">
                Create an agent to see its status here.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {/* Total */}
              <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 text-center dark:border-surface-700 dark:bg-surface-900/50">
                <Bot size={18} className="mx-auto mb-1 text-primary-500" />
                <p className="text-lg font-bold text-surface-900 dark:text-white">
                  {total}
                </p>
                <p className="text-[10px] text-surface-500">Total</p>
              </div>

              {/* Enabled */}
              <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-center dark:border-green-900/30 dark:bg-green-900/10">
                <Power size={18} className="mx-auto mb-1 text-green-500" />
                <p className="text-lg font-bold text-green-700 dark:text-green-400">
                  {enabled}
                </p>
                <p className="text-[10px] text-green-600 dark:text-green-500">
                  Enabled
                </p>
              </div>

              {/* Disabled */}
              <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 text-center dark:border-surface-700 dark:bg-surface-900/50">
                <PowerOff size={18} className="mx-auto mb-1 text-surface-400" />
                <p className="text-lg font-bold text-surface-700 dark:text-surface-300">
                  {disabled}
                </p>
                <p className="text-[10px] text-surface-500">Disabled</p>
              </div>
            </div>
          )}
        </div>
      )}
    </WidgetCard>
  )
}
