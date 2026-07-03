/** TemplateBrowser — browse templates by category, create agent from template. */

import { useState } from 'react'
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  Bot,
  Sparkles,
  Zap,
  BookOpen,
  Code2,
  PenLine,
  Headphones,
  Puzzle,
  Search,
  X,
  Star,
  LayoutGrid,
  List,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TEMPLATE_CATEGORIES } from '@/types/agent'
import type { AgentTemplateResponse, AgentTemplateListResponse } from '@/types/agent'

// ── Category config ─────────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<
  string,
  { label: string; icon: typeof Bot; description: string }
> = {
  general: {
    label: 'General',
    icon: Bot,
    description: 'Versatile agents for everyday tasks.',
  },
  research: {
    label: 'Research',
    icon: BookOpen,
    description: 'Agents optimized for research and analysis.',
  },
  coding: {
    label: 'Coding',
    icon: Code2,
    description: 'Programmers and code assistants.',
  },
  writing: {
    label: 'Writing',
    icon: PenLine,
    description: 'Content creation and editing agents.',
  },
  assistant: {
    label: 'Assistant',
    icon: Headphones,
    description: 'Personal and productivity assistants.',
  },
  custom: {
    label: 'Custom',
    icon: Puzzle,
    description: 'User-created custom templates.',
  },
}

function getCategoryConfig(category: string | null) {
  if (category && CATEGORY_CONFIG[category]) return CATEGORY_CONFIG[category]
  return {
    label: category ?? 'Uncategorized',
    icon: Puzzle,
    description: '',
  }
}

// ── Model display ───────────────────────────────────────────────────────────

const MODEL_DISPLAY: Record<string, string> = {
  'gpt-4': 'GPT-4',
  'gpt-4-turbo': 'GPT-4 Turbo',
  'gpt-3.5-turbo': 'GPT-3.5',
  'claude-opus-4': 'Opus 4',
  'claude-sonnet-5': 'Sonnet 5',
  'claude-haiku-4.5': 'Haiku 4.5',
}

function getModelLabel(model: string): string {
  return MODEL_DISPLAY[model] ?? model
}

// ── Props ──────────────────────────────────────────────────────────────────

interface TemplateBrowserProps {
  data: AgentTemplateListResponse | undefined
  isLoading: boolean
  isError: boolean
  error?: Error | null
  onRefetch: () => void
  onCreateAgent: (templateId: string, name?: string) => Promise<void>
  isCreating: boolean
  /** Optional search string to filter templates on the client. */
  searchQuery?: string
  onSearchChange?: (query: string) => void
}

// ── Component ──────────────────────────────────────────────────────────────

export function TemplateBrowser({
  data,
  isLoading,
  isError,
  error,
  onRefetch,
  onCreateAgent,
  isCreating,
  searchQuery = '',
  onSearchChange,
}: TemplateBrowserProps) {
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [creatingId, setCreatingId] = useState<string | null>(null)

  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-8 dark:border-red-900/30 dark:bg-red-950/20">
        <AlertCircle size={24} className="text-red-400" />
        <p className="text-sm text-red-600 dark:text-red-400">
          {error?.message ?? 'Failed to load templates.'}
        </p>
        <button
          onClick={onRefetch}
          className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      </div>
    )
  }

  // ── Filter + search ────────────────────────────────────────────────────
  let templates = data?.items ?? []

  if (activeCategory) {
    templates = templates.filter((t) => t.category === activeCategory)
  }

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    templates = templates.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        (t.description ?? '').toLowerCase().includes(q) ||
        (t.system_prompt ?? '').toLowerCase().includes(q),
    )
  }

  // ── Empty ──────────────────────────────────────────────────────────────
  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300 p-8 dark:border-surface-700">
        <Sparkles size={32} className="text-surface-300 dark:text-surface-600" />
        <p className="text-sm font-medium text-surface-500 dark:text-surface-400">
          No templates available
        </p>
        <p className="text-xs text-surface-400 dark:text-surface-500 text-center max-w-sm">
          Templates help you get started quickly with pre-configured agents.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Toolbar: Search + Category filters + View toggle */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        {onSearchChange && (
          <div className="relative flex-1 max-w-xs">
            <Search
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search templates..."
              className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
            />
          </div>
        )}

        {/* View toggle */}
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 bg-white p-0.5 dark:border-surface-700 dark:bg-surface-900">
          <button
            onClick={() => setViewMode('grid')}
            className={cn(
              'rounded-md p-1.5 transition-colors',
              viewMode === 'grid'
                ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300',
            )}
            title="Grid view"
          >
            <LayoutGrid size={14} />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'rounded-md p-1.5 transition-colors',
              viewMode === 'list'
                ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300',
            )}
            title="List view"
          >
            <List size={14} />
          </button>
        </div>
      </div>

      {/* Category pills */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setActiveCategory(null)}
          className={cn(
            'rounded-full px-3 py-1 text-xs font-medium transition-colors',
            activeCategory === null
              ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
              : 'bg-surface-100 text-surface-600 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:hover:bg-surface-700',
          )}
        >
          All
        </button>
        {TEMPLATE_CATEGORIES.map((cat) => {
          const cfg = getCategoryConfig(cat)
          const Icon = cfg.icon
          return (
            <button
              key={cat}
              onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                activeCategory === cat
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:hover:bg-surface-700',
              )}
            >
              <Icon size={12} />
              {cfg.label}
            </button>
          )
        })}
      </div>

      {/* Results count */}
      <p className="text-xs text-surface-400">
        {templates.length} template{templates.length !== 1 ? 's' : ''}
        {activeCategory ? ` in ${getCategoryConfig(activeCategory).label}` : ''}
        {searchQuery.trim() ? ` matching "${searchQuery.trim()}"` : ''}
      </p>

      {/* ── Template cards ──────────────────────────────────────────────────── */}
      {templates.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-surface-300 py-10 dark:border-surface-700">
          <Search size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500 dark:text-surface-400">
            No templates match your filters.
          </p>
          <button
            onClick={() => {
              setActiveCategory(null)
              onSearchChange?.('')
            }}
            className="text-xs text-primary-500 hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onUse={async (name) => {
                setCreatingId(template.id)
                try {
                  await onCreateAgent(template.id, name)
                } finally {
                  setCreatingId(null)
                }
              }}
              isCreating={isCreating && creatingId === template.id}
            />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {templates.map((template) => (
            <TemplateRow
              key={template.id}
              template={template}
              onUse={async (name) => {
                setCreatingId(template.id)
                try {
                  await onCreateAgent(template.id, name)
                } finally {
                  setCreatingId(null)
                }
              }}
              isCreating={isCreating && creatingId === template.id}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Template Card (grid) ─────────────────────────────────────────────────────

interface TemplateCardProps {
  template: AgentTemplateResponse
  onUse: (name?: string) => Promise<void>
  isCreating: boolean
}

function TemplateCard({ template, onUse, isCreating }: TemplateCardProps) {
  const [showNameInput, setShowNameInput] = useState(false)
  const [agentName, setAgentName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const catCfg = getCategoryConfig(template.category)
  const CategoryIcon = catCfg.icon

  const handleUse = async () => {
    setError(null)
    try {
      await onUse(agentName.trim() || undefined)
      setShowNameInput(false)
      setAgentName('')
    } catch (err) {
      setError((err as Error)?.message ?? 'Failed to create agent.')
    }
  }

  return (
    <div className="group flex flex-col rounded-xl border border-surface-200 bg-white transition-all hover:shadow-md dark:border-surface-800 dark:bg-surface-950">
      {/* Card body */}
      <div className="flex flex-1 flex-col gap-2 p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div
              className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                template.is_builtin
                  ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400'
                  : 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400',
              )}
            >
              <CategoryIcon size={16} />
            </div>
            <h3 className="truncate text-sm font-semibold text-surface-900 dark:text-white">
              {template.name}
            </h3>
          </div>

          {template.is_builtin && (
            <span
              className="shrink-0 rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-600 dark:bg-purple-900/20 dark:text-purple-400"
              title="Built-in template"
            >
              <Star size={10} className="inline -mt-0.5 mr-0.5" />
              Built-in
            </span>
          )}
        </div>

        {/* Description */}
        {template.description && (
          <p className="line-clamp-2 text-xs text-surface-500 dark:text-surface-400">
            {template.description}
          </p>
        )}

        {/* System prompt preview */}
        {template.system_prompt && (
          <div className="mt-auto">
            <span className="text-[10px] font-medium text-surface-400 dark:text-surface-500">
              System prompt:
            </span>
            <p className="mt-0.5 line-clamp-2 text-[11px] text-surface-400 dark:text-surface-500 italic">
              {template.system_prompt}
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between gap-2 border-t border-surface-100 px-4 py-2.5 dark:border-surface-800">
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
          <Zap size={10} />
          {getModelLabel(template.model)}
        </span>

        {showNameInput ? (
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="Agent name (optional)"
              className="w-32 rounded border border-surface-300 px-2 py-1 text-[10px] text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleUse()
                if (e.key === 'Escape') setShowNameInput(false)
              }}
            />
            <button
              onClick={handleUse}
              disabled={isCreating}
              className="rounded bg-primary-500 px-2 py-1 text-[10px] font-medium text-white hover:bg-primary-600 disabled:opacity-50 transition-colors"
            >
              {isCreating ? (
                <Loader2 size={10} className="animate-spin" />
              ) : (
                'Create'
              )}
            </button>
            <button
              onClick={() => setShowNameInput(false)}
              className="rounded p-1 text-surface-400 hover:text-surface-600 transition-colors"
            >
              <X size={12} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowNameInput(true)}
            disabled={isCreating}
            className="inline-flex items-center gap-1 rounded-lg bg-primary-500 px-2.5 py-1 text-[10px] font-medium text-white hover:bg-primary-600 disabled:opacity-50 transition-colors"
          >
            {isCreating ? (
              <Loader2 size={10} className="animate-spin" />
            ) : (
              <>
                <Sparkles size={10} />
                Use Template
              </>
            )}
          </button>
        )}
      </div>

      {/* Create error */}
      {error && (
        <p className="px-4 pb-2 text-[10px] text-red-500">{error}</p>
      )}
    </div>
  )
}

// ── Template Row (list view) ─────────────────────────────────────────────────

function TemplateRow({ template, onUse, isCreating }: TemplateCardProps) {
  const [showNameInput, setShowNameInput] = useState(false)
  const [agentName, setAgentName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const catCfg = getCategoryConfig(template.category)
  const CategoryIcon = catCfg.icon

  const handleUse = async () => {
    setError(null)
    try {
      await onUse(agentName.trim() || undefined)
      setShowNameInput(false)
      setAgentName('')
    } catch (err) {
      setError((err as Error)?.message ?? 'Failed to create agent.')
    }
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white transition-all hover:shadow-sm dark:border-surface-800 dark:bg-surface-950">
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Icon */}
        <div
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
            template.is_builtin
              ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400'
              : 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400',
          )}
        >
          <CategoryIcon size={16} />
        </div>

        {/* Details */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="truncate text-sm font-medium text-surface-900 dark:text-white">
              {template.name}
            </h4>
            {template.is_builtin && (
              <span className="shrink-0 rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-600 dark:bg-purple-900/20 dark:text-purple-400">
                Built-in
              </span>
            )}
            <span className="shrink-0 rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              {catCfg.label}
            </span>
            <span className="shrink-0 text-[10px] text-surface-400">
              {getModelLabel(template.model)}
            </span>
          </div>

          {template.description && (
            <p className="mt-0.5 truncate text-xs text-surface-500 dark:text-surface-400">
              {template.description}
            </p>
          )}

          {error && (
            <p className="mt-1 text-[10px] text-red-500">{error}</p>
          )}
        </div>

        {/* Action */}
        {showNameInput ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="Name..."
              className="w-28 rounded border border-surface-300 px-2 py-1 text-[10px] text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleUse()
                if (e.key === 'Escape') setShowNameInput(false)
              }}
            />
            <button
              onClick={handleUse}
              disabled={isCreating}
              className="rounded bg-primary-500 px-2 py-1 text-[10px] font-medium text-white hover:bg-primary-600 disabled:opacity-50 transition-colors"
            >
              {isCreating ? (
                <Loader2 size={10} className="animate-spin" />
              ) : (
                'Create'
              )}
            </button>
            <button
              onClick={() => setShowNameInput(false)}
              className="rounded p-1 text-surface-400 hover:text-surface-600 transition-colors"
            >
              <X size={12} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowNameInput(true)}
            disabled={isCreating}
            className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 disabled:opacity-50 transition-colors"
          >
            {isCreating ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <>
                <Sparkles size={12} />
                Use Template
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}
