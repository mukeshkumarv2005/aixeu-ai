/** TaskCreate page — wraps TaskForm with AI-powered generation and create mutation. */

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Sparkles, Loader2, Check, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useCreateTask } from '@/api/tasks'
import { useAITaskGenerate } from '@/api/task-ai'
import { TaskForm } from '@/components/tasks/TaskForm'
import type { TaskCreate, TaskUpdate } from '@/types/task'
import type { AITaskDraft } from '@/types/task-ai'

export default function TaskCreatePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const createMutation = useCreateTask()
  const generateMutation = useAITaskGenerate()

  // ── Incoming draft from chat/document conversion ─────────────────────────
  const locationState = location.state as { draftFromConvert?: AITaskDraft } | null
  const [convertedDraft] = useState<AITaskDraft | undefined>(
    locationState?.draftFromConvert,
  )

  // ── AI generation state ──────────────────────────────────────────────────
  const [aiInput, setAiInput] = useState('')
  const [drafts, setDrafts] = useState<AITaskDraft[] | null>(null)
  const [selectedDraftIdx, setSelectedDraftIdx] = useState<number | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [pickingDraft, setPickingDraft] = useState(false)

  const handleGenerate = async () => {
    const text = aiInput.trim()
    if (!text) return

    setAiError(null)
    setDrafts(null)
    setSelectedDraftIdx(null)
    try {
      const res = await generateMutation.mutateAsync({ text })
      setDrafts(res.tasks)
      if (res.tasks.length > 0) {
        setPickingDraft(true)
      }
    } catch (err: any) {
      setAiError(err?.message ?? 'Failed to generate tasks.')
    }
  }

  const handleSelectDraft = (idx: number) => {
    setSelectedDraftIdx(idx)
    setPickingDraft(false)
  }

  const handleClearDraft = () => {
    setDrafts(null)
    setSelectedDraftIdx(null)
    setPickingDraft(false)
    setAiInput('')
  }

  // ── Create handler ───────────────────────────────────────────────────────
  const handleSubmit = async (data: TaskCreate | TaskUpdate) => {
    const task = await createMutation.mutateAsync(data as TaskCreate)
    navigate(`/tasks/${task.id}`)
  }

  // If a draft was selected (AI gen) or came from conversion, merge into form defaults
  let prefilledDefaults: Partial<TaskCreate> | undefined
  if (selectedDraftIdx !== null && drafts && drafts[selectedDraftIdx]) {
    const d = drafts[selectedDraftIdx]
    prefilledDefaults = {
      title: d.title,
      description: d.description,
      priority: d.priority,
      estimated_minutes: d.estimated_minutes,
      due_date: d.due_date,
    }
  } else if (convertedDraft) {
    prefilledDefaults = {
      title: convertedDraft.title,
      description: convertedDraft.description ?? null,
      priority: convertedDraft.priority,
      estimated_minutes: convertedDraft.estimated_minutes,
      due_date: convertedDraft.due_date,
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      {/* ── Back link ──────────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/tasks')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
      >
        <ArrowLeft size={14} />
        Back to Tasks
      </button>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
          New Task
        </h1>
        <p className="mt-1 text-sm text-surface-500">
          Describe what you need and let AI draft it, or fill in the form manually.
        </p>
      </div>

      {/* ── Draft-from-conversion banner ────────────────────────────── */}
      {convertedDraft && (
        <div className="mb-6 rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-900/30 dark:bg-green-900/10">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={18} className="text-green-600 dark:text-green-400" />
            <p className="text-sm font-medium text-green-700 dark:text-green-400">
              Task draft created from conversion — review and save below.
            </p>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* AI Generation Panel                                            */}
      {/* ════════════════════════════════════════════════════════════════ */}
      {!convertedDraft && (
      <div className="mb-6 rounded-xl border border-primary-200 bg-white p-5 dark:border-primary-900/30 dark:bg-surface-950">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles size={18} className="text-primary-500" />
          <h2 className="text-sm font-semibold text-surface-900 dark:text-white">
            Generate with AI
          </h2>
        </div>

        <textarea
          value={aiInput}
          onChange={(e) => setAiInput(e.target.value)}
          placeholder="Describe the task(s) in natural language…&#10;&#10;Example: &#34;Set up CI/CD pipeline with GitHub Actions, write API docs for the auth module, and fix the login timeout bug&#34;"
          rows={3}
          className="mb-3 w-full resize-none rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-surface-600 dark:bg-surface-900 dark:text-white dark:placeholder-surface-500"
        />

        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={!aiInput.trim() || generateMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            {generateMutation.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {generateMutation.isPending ? 'Generating…' : 'Generate'}
          </button>

          {pickingDraft && (
            <button
              onClick={handleClearDraft}
              className="text-xs text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
            >
              Clear suggestions
            </button>
          )}
        </div>

        {/* AI Error */}
        {aiError && (
          <p className="mt-2 text-sm text-red-500">{aiError}</p>
        )}

        {/* AI-empty state: generated but no tasks */}
        {drafts && drafts.length === 0 && !generateMutation.isPending && (
          <p className="mt-2 text-sm text-surface-500">
            No tasks could be generated from that description. Try being more specific.
          </p>
        )}

        {/* Draft picker */}
        {drafts && drafts.length > 0 && !pickingDraft && selectedDraftIdx === null && (
          <p className="mt-2 text-xs text-surface-400">
            {drafts.length} task{drafts.length > 1 ? 's' : ''} generated. Select one below or dismiss.
          </p>
        )}

        {drafts && drafts.length > 0 && (
          <div className="mt-3 space-y-2">
            {drafts.map((draft, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectDraft(idx)}
                className={cn(
                  'flex w-full items-start gap-3 rounded-lg border p-3 text-left text-sm transition-colors',
                  selectedDraftIdx === idx
                    ? 'border-primary-400 bg-primary-50 dark:border-primary-500 dark:bg-primary-900/20'
                    : 'border-surface-200 bg-surface-50 hover:bg-surface-100 dark:border-surface-700 dark:bg-surface-900 dark:hover:bg-surface-800',
                )}
              >
                <div
                  className={cn(
                    'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                    selectedDraftIdx === idx
                      ? 'border-primary-500 bg-primary-500 text-white'
                      : 'border-surface-300',
                  )}
                >
                  {selectedDraftIdx === idx ? (
                    <Check size={12} />
                  ) : (
                    <span className="text-xs text-surface-500">{idx + 1}</span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-surface-900 dark:text-white">
                    {draft.title}
                  </p>
                  {draft.description && (
                    <p className="mt-0.5 text-xs text-surface-500 line-clamp-2">
                      {draft.description}
                    </p>
                  )}
                  <div className="mt-1 flex items-center gap-3 text-xs text-surface-400">
                    <span className="capitalize">{draft.priority}</span>
                    {draft.estimated_minutes && (
                      <span>{draft.estimated_minutes} min</span>
                    )}
                    {draft.due_date && (
                      <span>Due {new Date(draft.due_date).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      )}

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* Manual Form                                                    */}
      {/* ════════════════════════════════════════════════════════════════ */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-950">
        <TaskForm
          key={selectedDraftIdx} /* Force re-mount when draft changes */
          draftDefaults={prefilledDefaults}
          onSubmit={handleSubmit}
          isPending={createMutation.isPending}
          onCancel={() => navigate('/tasks')}
        />
      </div>
    </div>
  )
}
