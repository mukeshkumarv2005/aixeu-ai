/** QuickExecuteWidget — inline agent execution from the dashboard. */

import { useState } from 'react'
import {
  Bot,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Terminal,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useAgents, useExecuteAgent } from '@/api/agents'
import { WidgetCard } from '@/components/dashboard/WidgetCard'

export function QuickExecuteWidget() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [input, setInput] = useState('')

  const { data: agentsData, isLoading: agentsLoading } = useAgents({ limit: 50 })
  const executeMutation = useExecuteAgent()

  const agents = agentsData?.items?.filter((a) => a.enabled) ?? []
  const selectedAgent = agents.find((a) => a.id === selectedAgentId)
  const result = executeMutation.data
  const error = executeMutation.error

  const handleExecute = async () => {
    if (!selectedAgentId || !input.trim()) return
    try {
      await executeMutation.mutateAsync({
        agentId: selectedAgentId,
        body: { input_text: input.trim() },
      })
    } catch {
      // error is captured via executeMutation.error
    }
  }

  const handleClear = () => {
    executeMutation.reset()
    setInput('')
  }

  return (
    <WidgetCard
      title="Quick Execute"
      headerRight={
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="rounded p-0.5 text-surface-400 hover:text-surface-600 transition-colors"
        >
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      }
    >
      {/* Collapsed: show compact form */}
      {!isExpanded ? (
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <select
              value={selectedAgentId}
              onChange={(e) => {
                setSelectedAgentId(e.target.value)
                executeMutation.reset()
              }}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            >
              <option value="">Select agent…</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            {agentsLoading && (
              <Loader2
                size={14}
                className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-surface-400"
              />
            )}
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleExecute()
              }
            }}
            placeholder="Type a message…"
            disabled={!selectedAgentId}
            className="flex-1 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
          />
          <button
            onClick={handleExecute}
            disabled={
              !selectedAgentId || !input.trim() || executeMutation.isPending
            }
            className="flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            {executeMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            <span className="hidden sm:inline">Send</span>
          </button>
        </div>
      ) : (
        /* Expanded: full textarea + result display */
        <div className="space-y-3">
          {/* Agent selector */}
          <div>
            <label className="mb-1 block text-xs font-medium text-surface-500">
              Agent
            </label>
            <select
              value={selectedAgentId}
              onChange={(e) => {
                setSelectedAgentId(e.target.value)
                executeMutation.reset()
              }}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white"
            >
              <option value="">Select an agent…</option>
              {agentsLoading && <option disabled>Loading…</option>}
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Input */}
          <div>
            <label className="mb-1 block text-xs font-medium text-surface-500">
              Input
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                selectedAgent
                  ? `Send a message to ${selectedAgent.name}…`
                  : 'Select an agent first…'
              }
              rows={3}
              disabled={!selectedAgentId}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
            />
          </div>

          {/* Execute button */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleExecute}
              disabled={
                !selectedAgentId || !input.trim() || executeMutation.isPending
              }
              className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {executeMutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Terminal size={14} />
              )}
              Execute
            </button>
            <button
              onClick={handleClear}
              disabled={!input && !result && !error}
              className="rounded-lg border border-surface-300 px-3 py-2 text-sm font-medium text-surface-600 hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-600 dark:text-surface-400 dark:hover:bg-surface-800 transition-colors"
            >
              Clear
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-900/30 dark:bg-green-900/10">
              <div className="mb-1 flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-green-500" />
                <span className="text-xs font-medium text-green-700 dark:text-green-400">
                  Result
                </span>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-green-800 dark:text-green-300">
                {result.result ?? JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-900/30 dark:bg-red-900/10">
              <div className="mb-1 flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-red-500" />
                <span className="text-xs font-medium text-red-700 dark:text-red-400">
                  Execution failed
                </span>
              </div>
              <p className="text-sm text-red-600 dark:text-red-300">
                {error instanceof Error
                  ? error.message
                  : 'An unexpected error occurred.'}
              </p>
            </div>
          )}

          {/* Empty state when expanded */}
          {!result && !error && !executeMutation.isPending && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <Bot size={20} className="text-surface-300 dark:text-surface-600" />
              <p className="text-xs text-surface-400">
                {selectedAgent
                  ? 'Type a message and click Execute to run the agent.'
                  : 'Select an agent and type a message to execute.'}
              </p>
            </div>
          )}
        </div>
      )}
    </WidgetCard>
  )
}
