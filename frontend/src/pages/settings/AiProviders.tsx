/** AI Provider configuration — list, add, validate, delete API providers. */

import { useState } from 'react'
import {
  useProviders,
  useAddProvider,
  useDeleteProvider,
  useValidateProvider,
} from '@/api/settings'
import type { ApiProviderCreate } from '@/types/settings'
import { AI_PROVIDERS } from '@/types/settings'
import { Loader2, Plus, Trash2, CheckCircle2, XCircle, Eye, EyeOff, Key } from 'lucide-react'

export default function AiProviders() {
  const { data, isLoading, error } = useProviders()
  const addProvider = useAddProvider()
  const deleteProvider = useDeleteProvider()
  const validateProvider = useValidateProvider()

  const [showForm, setShowForm] = useState(false)
  const [validatingId, setValidatingId] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<{
    id: string
    valid: boolean
    error?: string
  } | null>(null)

  // ── Add form state ───────────────────────────────────────────────────────
  const [provider, setProvider] = useState<string>('openai')
  const [displayName, setDisplayName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [configStr, setConfigStr] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  function resetForm() {
    setProvider('openai')
    setDisplayName('')
    setApiKey('')
    setShowKey(false)
    setConfigStr('')
    setFormError(null)
    setShowForm(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)

    if (!apiKey.trim()) {
      setFormError('API key is required.')
      return
    }

    let config: Record<string, unknown> | undefined
    if (configStr.trim()) {
      try {
        config = JSON.parse(configStr)
      } catch {
        setFormError('Config must be valid JSON or empty.')
        return
      }
    }

    const body: ApiProviderCreate = {
      provider,
      display_name: displayName.trim() || null,
      api_key: apiKey.trim(),
      config,
    }

    try {
      await addProvider.mutateAsync(body)
      resetForm()
    } catch (err) {
      const detail =
        err instanceof Error
          ? err.message
          : 'Failed to add provider. It may already exist.'
      setFormError(detail)
    }
  }

  // ── Validate ─────────────────────────────────────────────────────────────

  async function handleValidate(id: string) {
    setValidatingId(id)
    setValidationResult(null)
    try {
      const result = await validateProvider.mutateAsync(id)
      setValidationResult({ id, valid: result.valid, error: result.error })
    } catch {
      setValidationResult({ id, valid: false, error: 'Validation request failed.' })
    } finally {
      setValidatingId(null)
    }
  }

  // ── Delete with confirmation ─────────────────────────────────────────────

  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  async function handleDelete(id: string) {
    try {
      await deleteProvider.mutateAsync(id)
      setDeleteConfirm(null)
    } catch {
      // handled by react-query
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        Failed to load API providers.
      </div>
    )
  }

  const providers = data?.items ?? []
  const isDeleting = deleteProvider.isPending

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">AI Providers</h2>
          <p className="text-sm text-muted-foreground">
            Manage your AI API provider keys and configurations.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Provider
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form
          onSubmit={handleAdd}
          className="rounded-lg border border-border bg-card p-4 space-y-4"
        >
          <h3 className="text-sm font-medium">New Provider</h3>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Provider type */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Provider <span className="text-destructive">*</span>
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {AI_PROVIDERS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            {/* Display name */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="My OpenAI"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* API key */}
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs font-medium text-muted-foreground">
                API Key <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Config JSON */}
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs font-medium text-muted-foreground">
                Config (JSON, optional)
              </label>
              <textarea
                value={configStr}
                onChange={(e) => setConfigStr(e.target.value)}
                placeholder='{"base_url": "http://localhost:11434"}'
                rows={2}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={addProvider.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {addProvider.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              Save
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-accent transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Empty state */}
      {providers.length === 0 && !showForm && (
        <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
          <Key className="h-10 w-10" />
          <p className="text-sm font-medium">No providers configured</p>
          <p className="text-xs">Add an API provider to get started.</p>
        </div>
      )}

      {/* Provider list */}
      {providers.length > 0 && (
        <div className="space-y-2">
          {providers.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="h-8 w-8 shrink-0 rounded-full bg-primary/10 flex items-center justify-center">
                  <Key className="h-4 w-4 text-primary" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      {p.display_name || p.provider}
                    </span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                      {p.provider}
                    </span>
                  </div>
                  <p className="truncate text-xs text-muted-foreground font-mono">
                    {p.api_key_encrypted}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {/* Validate */}
                <button
                  type="button"
                  onClick={() => handleValidate(p.id)}
                  disabled={validatingId === p.id}
                  className="rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-accent transition-colors disabled:opacity-50"
                  title="Validate API key"
                >
                  {validatingId === p.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    'Validate'
                  )}
                </button>

                {/* Validation result badge */}
                {validationResult?.id === p.id && (
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-medium ${
                      validationResult.valid
                        ? 'text-emerald-600'
                        : 'text-destructive'
                    }`}
                  >
                    {validationResult.valid ? (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5" /> Valid
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3.5 w-3.5" />{' '}
                        {validationResult.error || 'Invalid'}
                      </>
                    )}
                  </span>
                )}

                {/* Delete */}
                {deleteConfirm === p.id ? (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleDelete(p.id)}
                      disabled={isDeleting}
                      className="rounded bg-destructive px-2 py-1 text-xs font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
                    >
                      {isDeleting ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        'Confirm'
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(null)}
                      className="rounded border border-border px-2 py-1 text-xs font-medium hover:bg-accent transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setDeleteConfirm(p.id)}
                    className="rounded-lg p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                    title="Delete provider"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
