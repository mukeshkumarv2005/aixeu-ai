/** AgentCard — card used in agent list view and search results. */

import { Link } from 'react-router-dom'
import {
  Bot,
  Power,
  PowerOff,
  ChevronRight,
  Zap,
  Play,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentResponse } from '@/types/agent'

// ── Model display helper ───────────────────────────────────────────────────

const MODEL_CONFIG: Record<string, { label: string; color: string }> = {
  'gpt-4': { label: 'GPT-4', color: 'text-emerald-600 dark:text-emerald-400' },
  'gpt-4-turbo': { label: 'GPT-4 Turbo', color: 'text-emerald-600 dark:text-emerald-400' },
  'gpt-3.5-turbo': { label: 'GPT-3.5', color: 'text-emerald-500 dark:text-emerald-400' },
  'claude-opus-4': { label: 'Claude Opus 4', color: 'text-purple-600 dark:text-purple-400' },
  'claude-sonnet-5': { label: 'Claude Sonnet 5', color: 'text-purple-600 dark:text-purple-400' },
  'claude-haiku-4.5': { label: 'Claude Haiku 4.5', color: 'text-purple-500 dark:text-purple-400' },
}

function getModelDisplay(model: string): { label: string; color: string } {
  return MODEL_CONFIG[model] ?? { label: model, color: 'text-surface-500 dark:text-surface-400' }
}

// ── Props ──────────────────────────────────────────────────────────────────

interface AgentCardProps {
  agent: AgentResponse
}

// ── Component ──────────────────────────────────────────────────────────────

export function AgentCard({ agent }: AgentCardProps) {
  const modelCfg = getModelDisplay(agent.model)

  return (
    <Link
      to={`/agents/${agent.id}`}
      className={cn(
        'group block rounded-xl border bg-white p-4 shadow-sm transition-all hover:shadow-md dark:bg-surface-950',
        agent.enabled
          ? 'border-surface-200 dark:border-surface-800'
          : 'border-surface-200/60 dark:border-surface-800/60 opacity-70',
      )}
    >
      {/* Header: Name + Enabled indicator */}
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
              agent.enabled
                ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                : 'bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500',
            )}
          >
            <Bot size={16} />
          </div>
          <h3 className="truncate text-sm font-semibold text-surface-900 dark:text-white">
            {agent.name}
          </h3>
        </div>

        {/* Enabled / Disabled badge */}
        {agent.enabled ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700 dark:bg-green-900/20 dark:text-green-400">
            <Power size={10} />
            Active
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            <PowerOff size={10} />
            Disabled
          </span>
        )}
      </div>

      {/* Description */}
      {agent.description && (
        <p className="mb-3 line-clamp-2 text-xs text-surface-500 dark:text-surface-400">
          {agent.description}
        </p>
      )}

      {/* System prompt preview */}
      {agent.system_prompt && (
        <div className="mb-3">
          <span className="text-[10px] font-medium text-surface-400 dark:text-surface-500">
            System prompt:
          </span>
          <p className="mt-0.5 line-clamp-1 text-[11px] text-surface-400 dark:text-surface-500 italic">
            {agent.system_prompt}
          </p>
        </div>
      )}

      {/* Footer: Model + Temperature */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium dark:bg-surface-800',
              modelCfg.color,
            )}
          >
            <Zap size={10} />
            {modelCfg.label}
          </span>

          {agent.temperature !== undefined && (
            <span className="text-[10px] text-surface-400">
              T:{agent.temperature}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {agent.enabled && (
            <span className="inline-flex items-center gap-1 text-[10px] text-primary-500 opacity-0 transition-opacity group-hover:opacity-100">
              <Play size={10} />
              Run
            </span>
          )}
          <ChevronRight
            size={12}
            className="text-surface-300 opacity-0 transition-opacity group-hover:opacity-100"
          />
        </div>
      </div>
    </Link>
  )
}
