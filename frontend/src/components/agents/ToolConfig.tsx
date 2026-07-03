/** ToolConfig — agent tool list with add/remove and enable/disable. */

import { useState } from 'react'
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  Plus,
  Trash2,
  Power,
  PowerOff,
  Wrench,
  Search,
  BookOpen,
  FileText,
  ListTodo,
  MessageSquare,
  Calculator,
  Clock,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TOOL_TYPES } from '@/types/agent'
import type { AgentToolResponse, AgentToolCreate } from '@/types/agent'

// ── Tool type config ───────────────────────────────────────────────────────

const TOOL_TYPE_CONFIG: Record<
  string,
  { label: string; icon: typeof Wrench; description: string }
> = {
  knowledge_search: {
    label: 'Knowledge Search',
    icon: BookOpen,
    description: 'Search the knowledge base for relevant information.',
  },
  document_reader: {
    label: 'Document Reader',
    icon: FileText,
    description: 'Read and extract content from uploaded documents.',
  },
  task_manager: {
    label: 'Task Manager',
    icon: ListTodo,
    description: 'Create, update, and manage tasks.',
  },
  global_search: {
    label: 'Global Search',
    icon: Search,
    description: 'Search across the entire workspace.',
  },
  chat_history: {
    label: 'Chat History',
    icon: MessageSquare,
    description: 'Retrieve past conversations and context.',
  },
  calculator: {
    label: 'Calculator',
    icon: Calculator,
    description: 'Perform mathematical calculations.',
  },
  current_time: {
    label: 'Current Time',
    icon: Clock,
    description: 'Get the current date and time.',
  },
}

function getToolConfig(toolType: string) {
  return TOOL_TYPE_CONFIG[toolType] ?? {
    label: toolType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    icon: Wrench,
    description: 'Custom tool.',
  }
}

// ── Props ──────────────────────────────────────────────────────────────────

interface ToolConfigProps {
  tools: AgentToolResponse[] | undefined
  isLoading: boolean
  isError: boolean
  error?: Error | null
  onRefetch: () => void
  onAddTool: (data: AgentToolCreate) => Promise<void>
  onRemoveTool: (toolId: string) => Promise<void>
  onToggleTool: (toolId: string, enabled: boolean) => Promise<void>
  isAdding: boolean
  isRemoving: boolean
}

// ── Component ──────────────────────────────────────────────────────────────

export function ToolConfig({
  tools,
  isLoading,
  isError,
  error,
  onRefetch,
  onAddTool,
  onRemoveTool,
  onToggleTool,
  isAdding,
  isRemoving,
}: ToolConfigProps) {
  const [showAddForm, setShowAddForm] = useState(false)

  // ── Loading ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900/30 dark:bg-red-950/20">
        <AlertCircle size={24} className="text-red-400" />
        <p className="text-sm text-red-600 dark:text-red-400">
          {error?.message ?? 'Failed to load tools.'}
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

  // ── Available tool types for adding ────────────────────────────────────
  const usedTypes = new Set(tools?.map((t) => t.tool_type) ?? [])
  const availableTypes = TOOL_TYPES.filter((t) => !usedTypes.has(t))

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Tools
          {tools && tools.length > 0 && (
            <span className="ml-2 rounded-full bg-surface-100 px-2 py-0.5 text-[11px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              {tools.length}
            </span>
          )}
        </h3>

        {availableTypes.length > 0 && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 transition-colors"
          >
            {showAddForm ? <X size={14} /> : <Plus size={14} />}
            {showAddForm ? 'Cancel' : 'Add Tool'}
          </button>
        )}
      </div>

      {/* ── Add tool form ──────────────────────────────────────────────────── */}
      {showAddForm && (
        <AddToolForm
          availableTypes={availableTypes}
          onAdd={async (data) => {
            await onAddTool(data)
            setShowAddForm(false)
          }}
          onCancel={() => setShowAddForm(false)}
          isAdding={isAdding}
        />
      )}

      {/* ── Empty state ────────────────────────────────────────────────────── */}
      {(!tools || tools.length === 0) && !showAddForm && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300 p-6 dark:border-surface-700">
          <Wrench size={28} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm font-medium text-surface-500 dark:text-surface-400">
            No tools configured
          </p>
          <p className="text-xs text-surface-400 dark:text-surface-500 text-center max-w-sm">
            Add tools to give this agent capabilities like searching the
            knowledge base, reading documents, or managing tasks.
          </p>
          {availableTypes.length > 0 && (
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 transition-colors"
            >
              <Plus size={14} />
              Add your first tool
            </button>
          )}
        </div>
      )}

      {/* ── Tool list ──────────────────────────────────────────────────────── */}
      {tools && tools.length > 0 && (
        <div className="space-y-2">
          {tools.map((tool) => (
            <ToolRow
              key={tool.id}
              tool={tool}
              onRemove={onRemoveTool}
              onToggle={onToggleTool}
              isRemoving={isRemoving}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tool row ───────────────────────────────────────────────────────────────

interface ToolRowProps {
  tool: AgentToolResponse
  onRemove: (toolId: string) => Promise<void>
  onToggle: (toolId: string, enabled: boolean) => Promise<void>
  isRemoving: boolean
}

function ToolRow({ tool, onRemove, onToggle, isRemoving }: ToolRowProps) {
  const cfg = getToolConfig(tool.tool_type)
  const Icon = cfg.icon
  const [removing, setRemoving] = useState(false)

  const handleRemove = async () => {
    setRemoving(true)
    try {
      await onRemove(tool.id)
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border bg-white p-3 dark:bg-surface-950',
        tool.enabled
          ? 'border-surface-200 dark:border-surface-800'
          : 'border-surface-200/60 dark:border-surface-800/60 opacity-60',
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
          tool.enabled
            ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
            : 'bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500',
        )}
      >
        <Icon size={16} />
      </div>

      {/* Details */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-medium text-surface-900 dark:text-white">
            {tool.name || cfg.label}
          </h4>
          <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            {cfg.label}
          </span>
        </div>

        {(tool.description || cfg.description) && (
          <p className="mt-0.5 text-xs text-surface-500 dark:text-surface-400 line-clamp-1">
            {tool.description || cfg.description}
          </p>
        )}

        {/* Config summary */}
        {tool.config && Object.keys(tool.config).length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {Object.entries(tool.config).map(([key, value]) => (
              <span
                key={key}
                className="rounded bg-surface-100 px-1.5 py-0.5 text-[10px] text-surface-500 dark:bg-surface-800 dark:text-surface-400"
              >
                {key}: {typeof value === 'string' ? value : JSON.stringify(value)}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1">
        {/* Enable/Disable toggle */}
        <button
          onClick={() => onToggle(tool.id, !tool.enabled)}
          disabled={removing || isRemoving}
          className={cn(
            'rounded-lg p-1.5 transition-colors',
            tool.enabled
              ? 'text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/10'
              : 'text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800',
          )}
          title={tool.enabled ? 'Disable tool' : 'Enable tool'}
        >
          {tool.enabled ? <Power size={14} /> : <PowerOff size={14} />}
        </button>

        {/* Remove */}
        <button
          onClick={handleRemove}
          disabled={removing || isRemoving}
          className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 dark:hover:bg-red-900/10 disabled:opacity-50 transition-colors"
          title="Remove tool"
        >
          {removing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Trash2 size={14} />
          )}
        </button>
      </div>
    </div>
  )
}

// ── Add tool form ──────────────────────────────────────────────────────────

interface AddToolFormProps {
  availableTypes: readonly string[]
  onAdd: (data: AgentToolCreate) => Promise<void>
  onCancel: () => void
  isAdding: boolean
}

function AddToolForm({ availableTypes, onAdd, onCancel, isAdding }: AddToolFormProps) {
  const [selectedType, setSelectedType] = useState(availableTypes[0] ?? '')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!selectedType) {
      setError('Please select a tool type.')
      return
    }

    const cfg = getToolConfig(selectedType)
    const toolName = name.trim() || cfg.label

    try {
      await onAdd({
        tool_type: selectedType,
        name: toolName,
        description: description.trim() || null,
        enabled: true,
      })
    } catch (err) {
      setError((err as Error)?.message ?? 'Failed to add tool.')
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-primary-200 bg-primary-50/50 p-4 dark:border-primary-900/30 dark:bg-primary-950/10 space-y-3"
    >
      <h4 className="text-sm font-medium text-surface-900 dark:text-white">
        Add New Tool
      </h4>

      {/* Tool type select */}
      <div>
        <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-400">
          Tool Type
        </label>
        <select
          value={selectedType}
          onChange={(e) => {
            setSelectedType(e.target.value)
            const cfg = getToolConfig(e.target.value)
            if (!name.trim()) setName(cfg.label)
          }}
          className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
        >
          {availableTypes.map((t) => {
            const cfg = getToolConfig(t)
            return (
              <option key={t} value={t}>
                {cfg.label}
              </option>
            )
          })}
        </select>
      </div>

      {/* Name */}
      <div>
        <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-400">
          Name <span className="text-surface-400">(optional)</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Custom Knowledge Search"
          className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
        />
      </div>

      {/* Description */}
      <div>
        <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-400">
          Description <span className="text-surface-400">(optional)</span>
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what this tool does..."
          rows={2}
          className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
        />
      </div>

      {/* Error */}
      {error && <p className="text-xs text-red-500">{error}</p>}

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isAdding}
          className="rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isAdding || !selectedType}
          className="flex items-center gap-1 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        >
          {isAdding && <Loader2 size={12} className="animate-spin" />}
          Add Tool
        </button>
      </div>
    </form>
  )
}
