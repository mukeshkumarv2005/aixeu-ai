/** AgentDetailPage — view, edit, execute, and manage a single agent. */

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Bot,
  Power,
  PowerOff,
  Play,
  Send,
  Trash2,
  Save,
  X,
  Edit3,
  Zap,
  Clock,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useAgent,
  useUpdateAgent,
  useDeleteAgent,
  useExecuteAgent,
  useAgentRuns,
  useCancelRun,
  useAgentTools,
  useAddTool,
  useRemoveTool,
  useUpdateTool,
} from '@/api/agents'
import { AgentRunList } from '@/components/agents/AgentRunView'
import { ToolConfig } from '@/components/agents/ToolConfig'
import { ConfirmDeleteDialog } from '@/components/shared/ConfirmDeleteDialog'
import type { AgentToolCreate } from '@/types/agent'

// ── Tab config ───────────────────────────────────────────────────────────────

type TabId = 'overview' | 'runs' | 'tools' | 'settings'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'runs', label: 'Runs' },
  { id: 'tools', label: 'Tools' },
  { id: 'settings', label: 'Settings' },
]

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

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Queries
  const {
    data: agent,
    isLoading,
    isError,
    error,
    refetch,
  } = useAgent(agentId || undefined)

  const {
    data: runs,
    isLoading: runsLoading,
    isError: runsError,
    error: runsErr,
    refetch: refetchRuns,
  } = useAgentRuns(agentId || undefined, { limit: 20 })

  const {
    data: tools,
    isLoading: toolsLoading,
    isError: toolsError,
    error: toolsErr,
    refetch: refetchTools,
  } = useAgentTools(agentId || undefined)

  // Mutations
  const updateAgent = useUpdateAgent()
  const deleteAgent = useDeleteAgent()
  const executeAgent = useExecuteAgent()
  const cancelRun = useCancelRun()
  const addTool = useAddTool()
  const removeTool = useRemoveTool()
  const updateTool = useUpdateTool()

  // Edit form state
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editSystemPrompt, setEditSystemPrompt] = useState('')
  const [editModel, setEditModel] = useState('')
  const [editTemperature, setEditTemperature] = useState(0.7)
  const [editMaxTokens, setEditMaxTokens] = useState(4096)
  const [editEnabled, setEditEnabled] = useState(true)
  const [editError, setEditError] = useState<string | null>(null)

  // Execute state
  const [executeInput, setExecuteInput] = useState('')
  const [executeResult, setExecuteResult] = useState<string | null>(null)
  const [executeError, setExecuteError] = useState<string | null>(null)

  // Sync edit form when agent loads
  useEffect(() => {
    if (agent) {
      setEditName(agent.name)
      setEditDescription(agent.description ?? '')
      setEditSystemPrompt(agent.system_prompt ?? '')
      setEditModel(agent.model)
      setEditTemperature(agent.temperature ?? 0.7)
      setEditMaxTokens(agent.max_tokens ?? 4096)
      setEditEnabled(agent.enabled)
    }
  }, [agent])

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-surface-400" />
      </div>
    )
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (isError || !agent) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20">
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-950/20">
          <AlertCircle size={32} className="text-red-400" />
          <div>
            <p className="text-base font-medium text-red-700 dark:text-red-300">
              {isError ? 'Failed to load agent' : 'Agent not found'}
            </p>
            <p className="mt-1 text-sm text-red-500">
              {isError
                ? (error as Error)?.message ?? 'An unexpected error occurred.'
                : 'The agent you are looking for does not exist or has been deleted.'}
            </p>
          </div>
          <div className="flex gap-3">
            {isError && (
              <button
                onClick={() => refetch()}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            )}
            <button
              onClick={() => navigate('/agents')}
              className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-300 transition-colors"
            >
              Back to agents
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleSave = async () => {
    setEditError(null)
    if (!editName.trim()) {
      setEditError('Agent name is required.')
      return
    }
    try {
      await updateAgent.mutateAsync({
        agentId: agent.id,
        body: {
          name: editName.trim(),
          description: editDescription.trim() || null,
          system_prompt: editSystemPrompt.trim() || null,
          model: editModel,
          temperature: editTemperature,
          max_tokens: editMaxTokens,
          enabled: editEnabled,
        },
      })
      setIsEditing(false)
    } catch (err) {
      setEditError((err as Error)?.message ?? 'Failed to update agent.')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteAgent.mutateAsync(agent.id)
      navigate('/agents')
    } catch {
      // Error handled by mutation
    }
  }

  const handleExecute = async () => {
    setExecuteResult(null)
    setExecuteError(null)
    if (!executeInput.trim()) return

    try {
      const response = await executeAgent.mutateAsync({
        agentId: agent.id,
        body: { input_text: executeInput.trim() },
      })
      setExecuteResult(response.result || null)
    } catch (err) {
      setExecuteError((err as Error)?.message ?? 'Execution failed.')
    }
  }

  const handleCancelRun = async (runId: string) => {
    try {
      await cancelRun.mutateAsync(runId)
      refetchRuns()
    } catch {
      // Error handled by mutation
    }
  }

  const handleAddTool = async (data: AgentToolCreate) => {
    await addTool.mutateAsync({ agentId: agent.id, body: data })
    refetchTools()
  }

  const handleRemoveTool = async (toolId: string) => {
    await removeTool.mutateAsync({ toolId, agentId: agent.id })
    refetchTools()
  }

  const handleToggleTool = async (toolId: string, enabled: boolean) => {
    await updateTool.mutateAsync({ toolId, agentId: agent.id, body: { enabled } })
    refetchTools()
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6">
      {/* ── Back nav ────────────────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/agents')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300 transition-colors"
      >
        <ArrowLeft size={14} />
        Back to agents
      </button>

      {/* ── Agent header ────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
              agent.enabled
                ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                : 'bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500',
            )}
          >
            <Bot size={20} />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold text-surface-900 dark:text-white">
              {agent.name}
            </h1>
            {agent.description && (
              <p className="mt-0.5 truncate text-sm text-surface-500 dark:text-surface-400">
                {agent.description}
              </p>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {agent.enabled ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-[11px] font-medium text-green-700 dark:bg-green-900/20 dark:text-green-400">
              <Power size={11} />
              Active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-1 text-[11px] font-medium text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              <PowerOff size={11} />
              Disabled
            </span>
          )}

          <button
            onClick={() => navigate('/agents')}
            className="rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────────── */}
      <div className="mb-6 border-b border-surface-200 dark:border-surface-800">
        <div className="flex gap-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-surface-500 hover:text-surface-700 dark:hover:text-surface-300',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab content ─────────────────────────────────────────────────── */}
      <div>
        {/* ═══ OVERVIEW ═══════════════════════════════════════════════════ */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Execute section */}
            {agent.enabled && (
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-surface-900 dark:text-white">
                  <Play size={14} className="text-primary-500" />
                  Execute Agent
                </h3>

                <textarea
                  value={executeInput}
                  onChange={(e) => setExecuteInput(e.target.value)}
                  placeholder="Enter input for the agent..."
                  rows={3}
                  className="mb-3 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      handleExecute()
                    }
                  }}
                />

                <button
                  onClick={handleExecute}
                  disabled={executeAgent.isPending || !executeInput.trim()}
                  className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                >
                  {executeAgent.isPending ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  Execute
                </button>

                {/* Execute result */}
                {executeResult && (
                  <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900/30 dark:bg-green-950/20">
                    <h4 className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wider">
                      <CheckCircle2 size={12} />
                      Result
                    </h4>
                    <pre className="whitespace-pre-wrap text-sm text-green-800 dark:text-green-300 font-sans">
                      {executeResult}
                    </pre>
                  </div>
                )}

                {/* Execute error */}
                {executeError && (
                  <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/30 dark:bg-red-950/20">
                    <h4 className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider">
                      <AlertTriangle size={12} />
                      Error
                    </h4>
                    <pre className="whitespace-pre-wrap text-sm text-red-700 dark:text-red-400 font-sans">
                      {executeError}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Agent info cards */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <InfoCard
                label="Model"
                value={MODEL_OPTIONS.find((m) => m.value === agent.model)?.label ?? agent.model}
                icon={Zap}
              />
              <InfoCard
                label="Temperature"
                value={agent.temperature?.toFixed(1) ?? '—'}
                icon={Clock}
              />
              <InfoCard
                label="Max Tokens"
                value={agent.max_tokens?.toLocaleString() ?? '—'}
                icon={Bot}
              />
              <InfoCard
                label="Status"
                value={agent.enabled ? 'Enabled' : 'Disabled'}
                icon={agent.enabled ? CheckCircle2 : PowerOff}
                valueColor={agent.enabled ? 'text-green-600 dark:text-green-400' : 'text-surface-500'}
              />
            </div>

            {/* System prompt */}
            {agent.system_prompt && (
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <h3 className="mb-2 text-sm font-semibold text-surface-900 dark:text-white">
                  System Prompt
                </h3>
                <pre className="whitespace-pre-wrap rounded-lg bg-surface-50 p-4 text-xs text-surface-700 dark:bg-surface-900 dark:text-surface-300 font-mono">
                  {agent.system_prompt}
                </pre>
              </div>
            )}

            {/* Tools summary */}
            {tools && tools.length > 0 && (
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <h3 className="mb-3 text-sm font-semibold text-surface-900 dark:text-white">
                  Tools ({tools.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {tools.map((tool) => (
                    <span
                      key={tool.id}
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium',
                        tool.enabled
                          ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/10 dark:text-primary-400'
                          : 'bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400',
                      )}
                    >
                      {tool.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Quick runs preview */}
            <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
                  Recent Runs
                </h3>
                <button
                  onClick={() => setActiveTab('runs')}
                  className="text-xs font-medium text-primary-500 hover:text-primary-600"
                >
                  View all
                </button>
              </div>
              <AgentRunList
                data={runs}
                isLoading={runsLoading}
                isError={runsError}
                error={runsErr as Error | null}
                onRefetch={refetchRuns}
                onCancelRun={handleCancelRun}
                isCancelling={cancelRun.isPending}
              />
            </div>
          </div>
        )}

        {/* ═══ RUNS ════════════════════════════════════════════════════════ */}
        {activeTab === 'runs' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                Run History
              </h2>
              <button
                onClick={() => refetchRuns()}
                className="rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 transition-colors"
                disabled={runsLoading}
              >
                Refresh
              </button>
            </div>
            <AgentRunList
              data={runs}
              isLoading={runsLoading}
              isError={runsError}
              error={runsErr as Error | null}
              onRefetch={refetchRuns}
              onCancelRun={handleCancelRun}
              isCancelling={cancelRun.isPending}
            />
          </div>
        )}

        {/* ═══ TOOLS ═══════════════════════════════════════════════════════ */}
        {activeTab === 'tools' && (
          <div>
            <ToolConfig
              tools={tools}
              isLoading={toolsLoading}
              isError={toolsError}
              error={toolsErr as Error | null}
              onRefetch={refetchTools}
              onAddTool={handleAddTool}
              onRemoveTool={handleRemoveTool}
              onToggleTool={handleToggleTool}
              isAdding={addTool.isPending}
              isRemoving={removeTool.isPending}
            />
          </div>
        )}

        {/* ═══ SETTINGS ════════════════════════════════════════════════════ */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            {/* Edit form */}
            <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-950">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                  Agent Settings
                </h2>
                {!isEditing && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 transition-colors"
                  >
                    <Edit3 size={12} />
                    Edit
                  </button>
                )}
              </div>

              {isEditing ? (
                <div className="space-y-4">
                  {/* Name */}
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                      Agent Name <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                      Description
                    </label>
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      rows={2}
                      className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                    />
                  </div>

                  {/* System Prompt */}
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                      System Prompt
                    </label>
                    <textarea
                      value={editSystemPrompt}
                      onChange={(e) => setEditSystemPrompt(e.target.value)}
                      rows={5}
                      className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                    />
                  </div>

                  {/* Model + Temperature + Max Tokens */}
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                        Model
                      </label>
                      <select
                        value={editModel}
                        onChange={(e) => setEditModel(e.target.value)}
                        className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                      >
                        {MODEL_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                        Temperature: {editTemperature.toFixed(1)}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={editTemperature}
                        onChange={(e) => setEditTemperature(parseFloat(e.target.value))}
                        className="w-full accent-primary-500"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-300">
                        Max Tokens
                      </label>
                      <input
                        type="number"
                        value={editMaxTokens}
                        onChange={(e) => setEditMaxTokens(parseInt(e.target.value, 10) || 0)}
                        min={256}
                        max={128000}
                        step={256}
                        className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
                      />
                    </div>
                  </div>

                  {/* Enabled toggle */}
                  <div>
                    <button
                      type="button"
                      onClick={() => setEditEnabled(!editEnabled)}
                      className={cn(
                        'flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors',
                        editEnabled
                          ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-900/10 dark:text-green-400'
                          : 'border-surface-300 bg-white text-surface-600 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-400',
                      )}
                    >
                      {editEnabled ? (
                        <><Power size={14} /> Enabled</>
                      ) : (
                        <><PowerOff size={14} /> Disabled</>
                      )}
                    </button>
                  </div>

                  {/* Edit error */}
                  {editError && (
                    <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900/30 dark:bg-red-950/20">
                      <AlertCircle size={14} className="text-red-400 shrink-0" />
                      <p className="text-sm text-red-600 dark:text-red-400">{editError}</p>
                    </div>
                  )}

                  {/* Edit actions */}
                  <div className="flex items-center justify-end gap-3 border-t border-surface-200 pt-4 dark:border-surface-800">
                    <button
                      onClick={() => {
                        setIsEditing(false)
                        setEditError(null)
                        // Reset to original
                        setEditName(agent.name)
                        setEditDescription(agent.description ?? '')
                        setEditSystemPrompt(agent.system_prompt ?? '')
                        setEditModel(agent.model)
                        setEditTemperature(agent.temperature ?? 0.7)
                        setEditMaxTokens(agent.max_tokens ?? 4096)
                        setEditEnabled(agent.enabled)
                      }}
                      className="rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={updateAgent.isPending || !editName.trim()}
                      className="flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600 disabled:opacity-50 transition-colors"
                    >
                      {updateAgent.isPending ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Save size={12} />
                      )}
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                /* Read-only display */
                <div className="space-y-4">
                  <div>
                    <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                      Name
                    </span>
                    <p className="text-sm text-surface-900 dark:text-white">
                      {agent.name}
                    </p>
                  </div>

                  {agent.description && (
                    <div>
                      <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                        Description
                      </span>
                      <p className="text-sm text-surface-700 dark:text-surface-300">
                        {agent.description}
                      </p>
                    </div>
                  )}

                  {agent.system_prompt && (
                    <div>
                      <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                        System Prompt
                      </span>
                      <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-surface-50 p-3 text-xs text-surface-700 dark:bg-surface-900 dark:text-surface-300 font-mono">
                        {agent.system_prompt}
                      </pre>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                        Model
                      </span>
                      <p className="text-sm text-surface-900 dark:text-white">
                        {MODEL_OPTIONS.find((m) => m.value === agent.model)?.label ?? agent.model}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                        Temperature
                      </span>
                      <p className="text-sm text-surface-900 dark:text-white">
                        {agent.temperature?.toFixed(1) ?? '—'}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs font-medium text-surface-400 dark:text-surface-500 uppercase tracking-wider">
                        Max Tokens
                      </span>
                      <p className="text-sm text-surface-900 dark:text-white">
                        {agent.max_tokens?.toLocaleString() ?? '—'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Danger zone */}
            <div className="rounded-xl border border-red-200 bg-white p-6 dark:border-red-900/30 dark:bg-surface-950">
              <h2 className="mb-1 text-lg font-semibold text-red-600 dark:text-red-400">
                Danger Zone
              </h2>
              <p className="mb-4 text-sm text-surface-500 dark:text-surface-400">
                Once you delete an agent, there is no going back. All runs and
                configurations will be permanently removed.
              </p>
              <button
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteAgent.isPending}
                className="flex items-center gap-2 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-700 dark:bg-surface-900 dark:text-red-400 dark:hover:bg-red-950/20 disabled:opacity-50 transition-colors"
              >
                {deleteAgent.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
                Delete Agent
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Delete confirmation dialog ──────────────────────────────────── */}
      {showDeleteDialog && (
        <ConfirmDeleteDialog
          title="Delete Agent"
          message={`Are you sure you want to delete "${agent.name}"? This action cannot be undone. All runs, tools, and configurations associated with this agent will be permanently removed.`}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteDialog(false)}
          isLoading={deleteAgent.isPending}
        />
      )}
    </div>
  )
}

// ── Info card sub-component ──────────────────────────────────────────────────

interface InfoCardProps {
  label: string
  value: string
  icon: React.ElementType
  valueColor?: string
}

function InfoCard({ label, value, icon: Icon, valueColor }: InfoCardProps) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950">
      <div className="flex items-center gap-2 text-surface-400 dark:text-surface-500 mb-1">
        <Icon size={14} />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className={cn('text-sm font-semibold text-surface-900 dark:text-white', valueColor)}>
        {value}
      </p>
    </div>
  )
}
