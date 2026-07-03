/** RecentAgentRunsWidget — most recently updated agents with quick status view. */

import { useNavigate } from 'react-router-dom'
import { Bot, ArrowRight, AlertCircle, Power, PowerOff } from 'lucide-react'
import { useAgents } from '@/api/agents'
import { WidgetCard } from '@/components/dashboard/WidgetCard'

// ── Model display map (mirrors AgentCard) ──────────────────────────────────

const MODEL_LABELS: Record<string, string> = {
  'claude-opus-4': 'Claude Opus 4',
  'claude-sonnet-5': 'Claude Sonnet 5',
  'claude-haiku-4.5': 'Claude Haiku 4.5',
  'gpt-4': 'GPT-4',
  'gpt-4-turbo': 'GPT-4 Turbo',
  'gpt-3.5-turbo': 'GPT-3.5',
}

function modelLabel(model: string): string {
  return MODEL_LABELS[model] ?? model
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

export function RecentAgentRunsWidget() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useAgents({ limit: 5 })

  const agents = data?.items ?? []

  return (
    <WidgetCard
      title="Recent Agents"
      headerRight={
        agents.length > 0 && (
          <button
            onClick={() => navigate('/agents')}
            className="text-[10px] font-medium text-primary-500 hover:text-primary-600 transition-colors"
          >
            View all
          </button>
        )
      }
    >
      {/* Loading */}
      {isLoading && (
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
      {error && !isLoading && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-sm text-red-500">
            {error instanceof Error ? error.message : 'Failed to load agents'}
          </p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && agents.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <Bot size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500">No agents yet</p>
          <p className="text-xs text-surface-400">
            Create your first agent to see it here.
          </p>
        </div>
      )}

      {/* Data */}
      {!isLoading && !error && agents.length > 0 && (
        <div className="space-y-1">
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => navigate(`/agents/${agent.id}`)}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
            >
              <div className="rounded-lg bg-primary-50 p-1.5 text-primary-500 dark:bg-primary-900/20 dark:text-primary-400">
                <Bot size={14} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                    {agent.name}
                  </p>
                  {agent.enabled ? (
                    <Power
                      size={10}
                      className="shrink-0 text-green-500"
                    />
                  ) : (
                    <PowerOff
                      size={10}
                      className="shrink-0 text-surface-400"
                    />
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-surface-400">
                  <span>{modelLabel(agent.model)}</span>
                  <span>&middot;</span>
                  <span>{formatDate(agent.created_at)}</span>
                </div>
              </div>
              <ArrowRight
                size={14}
                className="shrink-0 text-surface-300 dark:text-surface-600"
              />
            </button>
          ))}
        </div>
      )}
    </WidgetCard>
  )
}
