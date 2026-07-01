/** Recent conversations widget — shows the 10 most recent chats. */

import { useNavigate } from 'react-router-dom'
import { MessageSquare, ArrowRight, AlertCircle } from 'lucide-react'
import type { RecentChatItem } from '@/types/dashboard'

interface RecentChatsProps {
  chats: RecentChatItem[]
  loading?: boolean
  error?: string | null
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

export function RecentChats({ chats, loading, error }: RecentChatsProps) {
  const navigate = useNavigate()

  return (
    <WidgetCard title="Recent Chats">
      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-2/3 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
                <div className="h-2.5 w-1/4 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <AlertCircle size={24} className="text-red-400" />
          <p className="text-sm text-red-500">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && chats.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <MessageSquare size={24} className="text-surface-300 dark:text-surface-600" />
          <p className="text-sm text-surface-500">No conversations yet</p>
          <p className="text-xs text-surface-400">
            Start chatting to see your recent conversations here.
          </p>
        </div>
      )}

      {/* Data */}
      {!loading && !error && chats.length > 0 && (
        <div className="space-y-1">
          {chats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => navigate('/chat')}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900"
            >
              <div className="rounded-lg bg-primary-50 p-1.5 text-primary-500 dark:bg-primary-900/20 dark:text-primary-400">
                <MessageSquare size={14} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-surface-700 dark:text-surface-300">
                  {chat.title || 'New Chat'}
                </p>
                <p className="text-xs text-surface-400">
                  {chat.message_count} msg · {formatDate(chat.updated_at)}
                </p>
              </div>
              <ArrowRight size={14} className="shrink-0 text-surface-300 dark:text-surface-600" />
            </button>
          ))}
        </div>
      )}
    </WidgetCard>
  )
}

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
