/** AgentCreatePage — create a new agent from scratch or from a template. */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Loader2,
  Save,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Power,
  PowerOff,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useTemplates,
  useCreateAgent,
  useCreateAgentFromTemplate,
} from '@/api/agents'
import { TemplateBrowser } from '@/components/agents/TemplateBrowser'

// ── Model options ────────────────────────────────────────────────────────────

const MODEL_OPTIONS = [
  { value: 'claude-opus-4', label: 'Claude Opus 4' },
  { value: 'claude-sonnet-5', label: 'Claude Sonnet 5' },
  { value: 'claude-haiku-4.5', label: 'Claude Haiku 4.5' },
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5' },
]

// ── Component ────────────────────────────────────────────────────────────────

export default function AgentCreatePage() {
  const navigate = useNavigate()

  const createAgent = useCreateAgent()
  const createFromTemplate = useCreateAgentFromTemplate()

  // Template explorer state
  const {
    data: templateData,
    isLoading: templatesLoading,
    isError: templatesError,
    error: templatesErr,
    refetch: refetchTemplates,
  } = useTemplates({ limit: 100 })

  const [showTemplates, setShowTemplates] = useState(false)
  const [templateSearch, setTemplateSearch] = useState('')
  const [isCreatingFromTemplate, setIsCreatingFromTemplate] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [model, setModel] = useState('claude-opus-4')
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(4096)
  const [enabled, setEnabled] = useState(true)
  const [formError, setFormError] = useState<string | null>(null)

  // ── Handle create from template ──────────────────────────────────────────
  const handleCreateFromTemplate = async (templateId: string, name?: string) => {
    setIsCreatingFromTemplate(true)
    setFormError(null)
    try {
      const agent = await createFromTemplate.mutateAsync({ templateId, name })
      navigate(`/agents/${agent.id}`)
    } catch (err) {
      throw err
    } finally {
      setIsCreatingFromTemplate(false)
    }
  }

  // ── Handle manual create ────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setFormError('Agent name is required.')
      return
    }

    try {
      const agent = await createAgent.mutateAsync({
        name: trimmedName,
        description: description.trim() || null,
        system_prompt: systemPrompt.trim() || null,
        model,
        temperature,
        max_tokens: maxTokens,
        enabled,
      })
      navigate(`/agents/${agent.id}`)
    } catch (err) {
      setFormError((err as Error)?.message ?? 'Failed to create agent.')
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      {/* ── Back nav ────────────────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/agents')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300 transition-colors"
      >
        <ArrowLeft size={14} />
        Back to agents
      </button>

      <h1 className="mb-6 text-2xl font-bold text-surface-900 dark:text-white">
        Create New Agent
      </h1>

      {/* ── Template section (collapsible) ───────────────────────────────── */}
      <div className="mb-8 rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className="flex w-full items-center justify-between px-5 py-4 text-left"
        >
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-primary-500" />
            <span className="text-sm font-semibold text-surface-900 dark:text-white">
              Start from a template
            </span>
            <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              {templateData?.items.length ?? 0} available
            </span>
          </div>
          {showTemplates ? (
            <ChevronUp size={16} className="text-surface-400" />
          ) : (
            <ChevronDown size={16} className="text-surface-400" />
          )}
        </button>

        {showTemplates && (
          <div className="border-t border-surface-200 px-5 pb-5 pt-4 dark:border-surface-800">
            <p className="mb-4 text-xs text-surface-500 dark:text-surface-400">
              Pick a pre-configured template to get started quickly. You can
              customize the agent after creation.
            </p>
            <TemplateBrowser
              data={templateData}
              isLoading={templatesLoading}
              isError={templatesError}
              error={templatesErr as Error | null}
              onRefetch={refetchTemplates}
              onCreateAgent={handleCreateFromTemplate}
              isCreating={isCreatingFromTemplate}
              searchQuery={templateSearch}
              onSearchChange={setTemplateSearch}
            />
          </div>
        )}
      </div>

      {/* ── Divider ─────────────────────────────────────────────────────── */}
      <div className="relative mb-8">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-surface-200 dark:border-surface-800" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-3 text-xs text-surface-400 dark:bg-surface-950">
            or create from scratch
          </span>
        </div>
      </div>

      {/* ── Manual create form ──────────────────────────────────────────── */}
      <form
        onSubmit={handleSubmit}
        className="space-y-6 rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-950"
      >
        {/* Name */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Agent Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Research Assistant"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
            autoFocus
          />
        </div>

        {/* Description */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            Description <span className="text-surface-400">(optional)</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this agent do?"
            rows={2}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
          />
        </div>

        {/* System Prompt */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
            System Prompt <span className="text-surface-400">(optional)</span>
          </label>
          <div className="relative">
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant that..."
              rows={5}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500 font-mono"
            />
            {systemPrompt && (
              <p className="mt-1 text-right text-[10px] text-surface-400">
                {systemPrompt.length} characters
              </p>
            )}
          </div>
        </div>

        {/* Model + Temperature + Max Tokens row */}
        <div className="grid gap-4 sm:grid-cols-3">
          {/* Model */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
              Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            >
              {MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Temperature */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
              Temperature: {temperature.toFixed(1)}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
            <div className="flex justify-between text-[10px] text-surface-400">
              <span>Precise (0)</span>
              <span>Creative (2)</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
              Max Tokens
            </label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value, 10) || 0)}
              min={256}
              max={128000}
              step={256}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            />
          </div>
        </div>

        {/* Enabled toggle */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setEnabled(!enabled)}
            className={cn(
              'flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors',
              enabled
                ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-900/10 dark:text-green-400'
                : 'border-surface-300 bg-white text-surface-600 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-400',
            )}
          >
            {enabled ? (
              <>
                <Power size={14} />
                Enabled
              </>
            ) : (
              <>
                <PowerOff size={14} />
                Disabled
              </>
            )}
          </button>
          <span className="text-xs text-surface-500 dark:text-surface-400">
            {enabled
              ? 'Agent is active and can be executed.'
              : 'Agent is disabled and will not respond to execution requests.'}
          </span>
        </div>

        {/* Form error */}
        {formError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900/30 dark:bg-red-950/20">
            <AlertCircle size={14} className="text-red-400 shrink-0" />
            <p className="text-sm text-red-600 dark:text-red-400">{formError}</p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center justify-end gap-3 border-t border-surface-200 pt-5 dark:border-surface-800">
          <button
            type="button"
            onClick={() => navigate('/agents')}
            className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createAgent.isPending || !name.trim()}
            className="flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            {createAgent.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Save size={16} />
            )}
            Create Agent
          </button>
        </div>
      </form>
    </div>
  )
}
