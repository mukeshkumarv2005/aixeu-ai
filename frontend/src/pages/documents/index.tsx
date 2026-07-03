/** Document details page — metadata, analysis, and chunks for a processed document. */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  FileText,
  Loader2,
  AlertCircle,
  RefreshCw,
  BookOpen,
  BrainCircuit,
  ListChecks,
  ListTodo,
  Hash,
  Languages,
  User,
  Type,
  FileCode,
  Calendar,
  Clock,
  Eye,
  Zap,
  BarChart3,
  Tag,
  Layers,
  Lightbulb,
  MessageSquareText,
  Play,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import {
  useDocumentStatus,
  useDocumentMetadata,
  useDocumentChunks,
  useDocumentAnalysis,
  useProcessDocument,
} from '@/api/documents'
import { useAIConvertDocument } from '@/api/task-ai'
import { cn } from '@/lib/utils'
import { RelatedTasksWidget } from '@/components/tasks/RelatedTasksWidget'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export default function DocumentDetailsPage() {
  const { fileId } = useParams<{ fileId: string }>()
  const navigate = useNavigate()

  // ── Data ──────────────────────────────────────────────────────────────
  const {
    data: status,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
  } = useDocumentStatus(fileId ?? '')

  const {
    data: metadata,
    isLoading: metadataLoading,
  } = useDocumentMetadata(fileId ?? '')

  const {
    data: analysis,
    isLoading: analysisLoading,
  } = useDocumentAnalysis(fileId ?? '')

  const [chunkOffset, setChunkOffset] = useState(0)
  const CHUNK_LIMIT = 20
  const {
    data: chunks,
    isLoading: chunksLoading,
  } = useDocumentChunks(fileId ?? '', chunkOffset, CHUNK_LIMIT)

  const processMutation = useProcessDocument(fileId ?? '')
  const convertMutation = useAIConvertDocument()
  const [convertError, setConvertError] = useState<string | null>(null)

  // ── Derived ────────────────────────────────────────────────────────────
  const isLoading = statusLoading || metadataLoading || analysisLoading || chunksLoading
  const isProcessing = status?.processing_status === 'processing'
  const isCompleted = status?.processing_status === 'completed'
  const isFailed = status?.processing_status === 'failed'
  const hasData = metadata || analysis || (chunks && chunks.total > 0)

  // ── Convert-to-task handler ────────────────────────────────────────────
  const handleConvertToTask = async () => {
    setConvertError(null)
    try {
      const res = await convertMutation.mutateAsync({ document_id: fileId ?? '' })
      navigate('/tasks/create', { state: { draftFromConvert: res.task } })
    } catch (err: any) {
      setConvertError(err?.message ?? 'Failed to convert to task.')
    }
  }

  // ── Error state ───────────────────────────────────────────────────────
  if (statusError && !statusLoading) {
    return (
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <button
          onClick={() => navigate('/storage')}
          className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
        >
          <ArrowLeft size={16} />
          Back to Storage
        </button>
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
          <AlertCircle size={32} className="text-red-400" />
          <div>
            <p className="text-base font-medium text-red-700 dark:text-red-300">
              Failed to load document
            </p>
            <p className="mt-1 text-sm text-red-500">
              {statusError instanceof Error ? statusError.message : 'An unexpected error occurred.'}
            </p>
          </div>
          <button
            onClick={() => refetchStatus()}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
          >
            <RefreshCw size={14} className="mr-1.5 inline" />
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      {/* ── Back button ──────────────────────────────────────────── */}
      <button
        onClick={() => navigate('/storage')}
        className="mb-4 flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
      >
        <ArrowLeft size={16} />
        Back to Storage
      </button>

      {/* ── Page header ──────────────────────────────────────────── */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-accent-50 p-2.5 text-accent-600 dark:bg-accent-900/20 dark:text-accent-400">
              <FileText size={24} />
            </div>
            <div>
              <h1 className="truncate text-xl font-bold text-surface-900 dark:text-white">
                {status?.filename ?? 'Document'}
              </h1>
              <p className="mt-0.5 text-sm text-surface-500">
                Document Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Status badge */}
        {isLoading && !isProcessing ? (
          <div className="flex items-center gap-2 rounded-lg bg-surface-100 px-3 py-1.5 text-sm text-surface-500 dark:bg-surface-800">
            <Loader2 size={14} className="animate-spin" />
            Loading...
          </div>
        ) : isCompleted ? (
          <div className="flex items-center gap-1.5 rounded-lg bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/20 dark:text-green-400">
            <CheckCircle2 size={16} />
            Processed
          </div>
        ) : isProcessing ? (
          <div className="flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
            <Loader2 size={14} className="animate-spin" />
            Processing...
          </div>
        ) : isFailed ? (
          <div className="flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 dark:bg-red-900/20 dark:text-red-400">
            <XCircle size={16} />
            Failed
          </div>
        ) : (
          <div className="flex items-center gap-1.5 rounded-lg bg-surface-100 px-3 py-1.5 text-sm font-medium text-surface-600 dark:bg-surface-800 dark:text-surface-400">
            Not Processed
          </div>
        )}

        {/* Convert to Task */}
        <button
          onClick={handleConvertToTask}
          disabled={convertMutation.isPending}
          className="flex items-center gap-2 rounded-lg border border-primary-200 bg-primary-50 px-3 py-2 text-sm font-medium text-primary-700 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-primary-900/30 dark:bg-primary-900/20 dark:text-primary-400 dark:hover:bg-primary-900/30 transition-colors"
        >
          {convertMutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ListTodo size={14} />
          )}
          {convertMutation.isPending ? 'Converting…' : 'Convert to Task'}
        </button>
      </div>

      {/* Convert error */}
      {convertError && (
        <div className="mb-4 flex items-center gap-2 text-sm text-red-500">
          <AlertCircle size={14} />
          {convertError}
        </div>
      )}

      {/* ── Processing status & actions ──────────────────────────── */}
      <div className="mb-6 rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Processing Status
              </p>
              <p className="mt-0.5 text-sm text-surface-500">
                {isCompleted
                  ? 'Document has been fully processed and is ready for review.'
                  : isProcessing
                    ? 'Document is currently being processed. This may take a moment.'
                    : isFailed
                      ? `Processing failed: ${status?.processing_error ?? 'Unknown error'}`
                      : 'Document has not been processed yet. Click Process to start.'}
              </p>
            </div>
          </div>

          <button
            onClick={() => processMutation.mutate({ force_reprocess: isCompleted })}
            disabled={isProcessing || processMutation.isPending}
            className={cn(
              'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
              isCompleted
                ? 'border border-surface-200 bg-white text-surface-700 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800'
                : 'bg-primary-600 text-white hover:bg-primary-700',
              (isProcessing || processMutation.isPending) && 'cursor-not-allowed opacity-50',
            )}
          >
            {processMutation.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Play size={16} />
            )}
            {processMutation.isPending
              ? 'Processing...'
              : isCompleted
                ? 'Reprocess'
                : 'Process Document'}
          </button>
        </div>
        {processMutation.isError && (
          <p className="mt-3 text-sm text-red-500">
            {processMutation.error instanceof Error
              ? processMutation.error.message
              : 'Failed to start processing.'}
          </p>
        )}
      </div>

      {/* ── Empty (not yet processed) ────────────────────────────── */}
      {!isLoading && !hasData && !isCompleted && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-12 text-center dark:border-surface-700 dark:bg-surface-900/50">
          <BookOpen size={40} className="text-surface-300 dark:text-surface-600" />
          <div>
            <p className="text-base font-medium text-surface-700 dark:text-surface-300">
              No document data yet
            </p>
            <p className="mt-1 text-sm text-surface-500">
              Click "Process Document" above to extract text, chunks, and AI analysis.
            </p>
          </div>
        </div>
      )}

      {/* ── Loading skeleton ─────────────────────────────────────── */}
      {isLoading && !hasData && !isProcessing && (
        <div className="space-y-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950"
            >
              <div className="mb-3 h-4 w-32 rounded bg-surface-200 dark:bg-surface-800" />
              <div className="space-y-2">
                <div className="h-3 w-full rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-3 w-3/4 rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-3 w-1/2 rounded bg-surface-200 dark:bg-surface-800" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Metadata card ────────────────────────────────────────── */}
      {metadata && (
        <section className="mb-6">
          <div className="mb-3 flex items-center gap-2">
            <ListChecks size={18} className="text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
              Metadata
            </h2>
          </div>
          <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              <MetadataField icon={Type} label="Title" value={metadata.title ?? '-'} />
              <MetadataField icon={User} label="Author" value={metadata.author ?? '-'} />
              <MetadataField icon={Languages} label="Language" value={metadata.language ?? '-'} />
              <MetadataField icon={FileCode} label="Type" value={metadata.document_type ?? '-'} />
              <MetadataField icon={Hash} label="Words" value={metadata.word_count != null ? formatNumber(metadata.word_count) : '-'} />
              <MetadataField icon={MessageSquareText} label="Characters" value={metadata.character_count != null ? formatNumber(metadata.character_count) : '-'} />
              <MetadataField icon={BarChart3} label="Pages" value={metadata.page_count != null ? String(metadata.page_count) : '-'} />
              <MetadataField icon={Calendar} label="Created" value={metadata.created_date ? formatDate(metadata.created_date) : '-'} />
            </div>
            {metadata.ocr_used && (
              <div className="mt-4 flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                <Eye size={14} />
                OCR was used during text extraction
              </div>
            )}
            {metadata.processing_time_ms != null && (
              <div className="mt-3 flex items-center gap-1.5 text-xs text-surface-400">
                <Clock size={12} />
                Extracted in {metadata.processing_time_ms}ms
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Analysis card ────────────────────────────────────────── */}
      {analysis && (
        <section className="mb-6">
          <div className="mb-3 flex items-center gap-2">
            <BrainCircuit size={18} className="text-accent-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
              AI Analysis
            </h2>
          </div>
          <div className="space-y-4">
            {/* Summary */}
            <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300">
                <MessageSquareText size={16} />
                Summary
              </div>
              <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-400">
                {analysis.summary || 'No summary available.'}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {/* Keywords */}
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300">
                  <Tag size={16} />
                  Keywords
                </div>
                {analysis.keywords.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700 dark:bg-primary-900/20 dark:text-primary-400"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-surface-400">None</p>
                )}
              </div>

              {/* Topics */}
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300">
                  <Lightbulb size={16} />
                  Topics
                </div>
                {analysis.topics.length > 0 ? (
                  <ul className="space-y-1">
                    {analysis.topics.map((topic) => (
                      <li
                        key={topic}
                        className="flex items-center gap-2 text-sm text-surface-600 dark:text-surface-400"
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-accent-400" />
                        {topic}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-surface-400">None</p>
                )}
              </div>

              {/* Category */}
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300">
                  <Layers size={16} />
                  Category
                </div>
                {analysis.category ? (
                  <span className="inline-block rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    {analysis.category}
                  </span>
                ) : (
                  <p className="text-sm text-surface-400">Uncategorized</p>
                )}

                {analysis.model_used && (
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-surface-400">
                    <Zap size={12} />
                    Model: {analysis.model_used}
                  </div>
                )}
                {analysis.analysis_completed_at && (
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-surface-400">
                    <Clock size={12} />
                    {formatDate(analysis.analysis_completed_at)}
                  </div>
                )}
              </div>
            </div>

            {/* Entities */}
            {analysis.entities.length > 0 && (
              <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-surface-700 dark:text-surface-300">
                  <Eye size={16} />
                  Entities
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-200 text-left text-xs uppercase text-surface-500 dark:border-surface-700">
                        <th className="pb-2 pr-4 font-medium">Name</th>
                        <th className="pb-2 font-medium">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.entities.map((entity, i) => (
                        <tr
                          key={i}
                          className="border-b border-surface-100 last:border-0 dark:border-surface-800"
                        >
                          <td className="py-2 pr-4 text-surface-700 dark:text-surface-300">
                            {String(entity.name ?? '-')}
                          </td>
                          <td className="py-2 text-surface-500">
                            <span className="rounded bg-surface-100 px-2 py-0.5 text-xs dark:bg-surface-800">
                              {String(entity.type ?? 'Unknown')}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Related Tasks Widget ──────────────────────────────────── */}
      {fileId && (
        <section className="mb-6">
          <RelatedTasksWidget uploadedDocumentId={fileId} />
        </section>
      )}

      {/* ── Chunks section ────────────────────────────────────────── */}
      {chunks && chunks.total > 0 && (
        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers size={18} className="text-green-500" />
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                Chunks
              </h2>
              <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs text-surface-500 dark:bg-surface-800">
                {chunks.total} total
              </span>
              <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs text-surface-500 dark:bg-surface-800">
                {chunks.chunk_type}
              </span>
              <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs text-surface-500 dark:bg-surface-800">
                {formatNumber(chunks.total_tokens)} tokens
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {chunks.chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-950"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-surface-400">
                    Chunk #{chunk.chunk_index + 1}
                  </span>
                  <span className="text-xs text-surface-400">
                    {chunk.token_count != null
                      ? `${chunk.token_count} tokens`
                      : `${formatNumber(chunk.char_count)} chars`}
                  </span>
                </div>
                <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap break-words rounded-lg bg-surface-50 p-3 text-xs leading-relaxed text-surface-700 dark:bg-surface-900 dark:text-surface-300">
                  {chunk.content}
                </pre>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {chunks.total > CHUNK_LIMIT && (
            <div className="mt-4 flex items-center justify-center gap-3">
              <button
                onClick={() => setChunkOffset(Math.max(0, chunkOffset - CHUNK_LIMIT))}
                disabled={chunkOffset === 0}
                className="rounded-lg border border-surface-200 px-3 py-1.5 text-sm text-surface-600 transition-colors hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-surface-700 dark:text-surface-400 dark:hover:bg-surface-800"
              >
                Previous
              </button>
              <span className="text-sm text-surface-500">
                {chunkOffset + 1}–{Math.min(chunkOffset + CHUNK_LIMIT, chunks.total)} of {chunks.total}
              </span>
              <button
                onClick={() => setChunkOffset(chunkOffset + CHUNK_LIMIT)}
                disabled={chunkOffset + CHUNK_LIMIT >= chunks.total}
                className="rounded-lg border border-surface-200 px-3 py-1.5 text-sm text-surface-600 transition-colors hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-surface-700 dark:text-surface-400 dark:hover:bg-surface-800"
              >
                Next
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Metadata field sub-component
// ---------------------------------------------------------------------------

function MetadataField({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Type
  label: string
  value: string
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-surface-400">
        <Icon size={12} />
        {label}
      </div>
      <p className="mt-0.5 truncate text-sm font-medium text-surface-900 dark:text-white">
        {value}
      </p>
    </div>
  )
}
