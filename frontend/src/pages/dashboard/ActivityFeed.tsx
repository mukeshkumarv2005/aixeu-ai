/** Recent activity feed widget — shows combined chat + upload activity. */

import { useNavigate } from 'react-router-dom'
import { MessageSquare, Upload, ArrowRight, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RecentActivityItem } from '@/types/dashboard'

interface ActivityFeedProps {
  items: RecentActivityItem[]
  loading?: boolean
  error?: string | null
}

function formatRelative(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  if (diffMin < 1) return 'Just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHrs = Math.floor(diffMin / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const TYPE_ICONS = {
  chat: { icon: MessageSquare, color: 'text-primary-500' },
  upload: { icon: Upload, color: 'text-accent-500' },
  message: { icon: MessageSquare, color: 'text-green-500' },
} as const

export function ActivityFeed({ items, loading, error }: ActivityFeedProps) {
  const navigate = useNavigate()

  // ── Loading skeleton ────────────────────────────────────────────────
  if (loading) {
    return (
      <WidgetCard title="Recent Activity">
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-3/4 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-2.5 w-1/4 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
              </div>
            </div>
          ))}
        </div>
      </WidgetCard>
    )
  }

  // ── Error state ────────────────────────────────────────────────────
  if (error) {
    return (
      <WidgetCard title="Recent Activity">
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-sm text-red-500">{error}</p>
        </div>
      </WidgetCard>
    )
  }

  // ── Empty state ────────────────────────────────────────────────────
  if (items.length === 0) {
    return (
      <WidgetCard title="Recent Activity">
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <MessageSquare size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500">No activity yet</p>
          <p className="text-xs text-surface-400">
            Start a chat or upload a file to see activity here.
          </p>
        </div>
      </WidgetCard>
    )
  }

  // ── Data ───────────────────────────────────────────────────────────
  return (
    <WidgetCard title="Recent Activity">
      <div className="space-y-1">
        {items.map((item) => {
          const meta = TYPE_ICONS[item.type] ?? TYPE_ICONS.chat
          const Icon = meta.icon
          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.type === 'chat' || item.type === 'message') {
                  navigate(`/chat`)
                } else if (item.type === 'upload') {
                  navigate('/storage')
                }
              }}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
            >
              <div className={cn('rounded-lg p-1.5', meta.color, 'bg-surface-100 dark:bg-surface-800')}>
                <Icon size={14} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-surface-700 dark:text-surface-300">
                  {item.description}
                </p>
                <p className="text-xs text-surface-400">
                  {formatRelative(item.created_at)}
                </p>
              </div>
              <ArrowRight size={14} className="shrink-0 text-surface-300 dark:text-surface-600" />
            </button>
          )
        })}
      </div>
    </WidgetCard>
  )
}

// -----------------------------------------------------------------------
// Internal widget card wrapper
// -----------------------------------------------------------------------

function WidgetCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          {title}
        </h3>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}
