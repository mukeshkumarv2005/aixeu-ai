/** Dashboard main page — aggregate stats, recent activity, widgets. */

import {
  MessageSquare,
  MessagesSquare,
  FileText,
  HardDrive,
  BrainCircuit,
  Sparkles,
  RefreshCw,
  AlertCircle,
  LayoutDashboard,
} from 'lucide-react'
import { useDashboard, useUsage } from '@/api/dashboard'
import { StatCard } from './StatCard'
import { RecentChats } from './RecentChats'
import { RecentDocuments } from './RecentDocuments'
import { ActivityFeed } from './ActivityFeed'
import { UsageWidget } from './UsageWidget'
import { QuickActions } from './QuickActions'

export default function DashboardPage() {
  const {
    data: dashData,
    isLoading: dashLoading,
    error: dashError,
    refetch: refetchDash,
  } = useDashboard()
  const {
    data: usageData,
    isLoading: usageLoading,
    error: usageError,
    refetch: refetchUsage,
  } = useUsage()

  const hasError = !!dashError || !!usageError
  const isLoading = dashLoading || usageLoading
  const isEmpty =
    !isLoading &&
    !hasError &&
    dashData &&
    dashData.stats.total_conversations === 0 &&
    dashData.stats.total_messages === 0 &&
    dashData.stats.total_files === 0

  const handleRetry = () => {
    refetchDash()
    refetchUsage()
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6">
      {/* ── Page heading ────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-surface-500">
            Welcome back! Here’s an overview of your workspace.
          </p>
        </div>
        {hasError && (
          <button
            onClick={handleRetry}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm font-medium text-surface-700 transition-colors hover:bg-surface-50 dark:border-surface-800 dark:bg-surface-950 dark:text-surface-300 dark:hover:bg-surface-900"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        )}
      </div>

      {/* ── Full-page error ─────────────────────────────────────── */}
      {hasError && !isLoading && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center dark:border-red-900/30 dark:bg-red-900/10">
          <AlertCircle size={32} className="text-red-400" />
          <div>
            <p className="text-base font-medium text-red-700 dark:text-red-300">
              Failed to load dashboard
            </p>
            <p className="mt-1 text-sm text-red-500">
              {dashError instanceof Error
                ? dashError.message
                : usageError instanceof Error
                  ? usageError.message
                  : 'An unexpected error occurred. Please try again.'}
            </p>
          </div>
          <button
            onClick={handleRetry}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
          >
            <RefreshCw size={14} className="mr-1.5 inline" />
            Try again
          </button>
        </div>
      )}

      {/* ── Stat cards grid ─────────────────────────────────────── */}
      <section>
        <h2 className="sr-only">Statistics</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <StatCard
            icon={MessageSquare}
            label="Conversations"
            value={dashData?.stats.total_conversations ?? '-'}
            color="primary"
            loading={isLoading}
          />
          <StatCard
            icon={MessagesSquare}
            label="Messages"
            value={dashData?.stats.total_messages ?? '-'}
            color="green"
            loading={isLoading}
          />
          <StatCard
            icon={FileText}
            label="Files"
            value={dashData?.stats.total_files ?? '-'}
            color="accent"
            loading={isLoading}
          />
          <StatCard
            icon={HardDrive}
            label="Storage"
            value={
              dashData?.stats.total_storage_bytes != null
                ? formatBytes(dashData.stats.total_storage_bytes)
                : '-'
            }
            color="amber"
            loading={isLoading}
          />
          <StatCard
            icon={BrainCircuit}
            label="Input tokens"
            value={
              dashData?.stats.total_input_tokens != null
                ? formatTokens(dashData.stats.total_input_tokens)
                : '-'
            }
            color="primary"
            loading={isLoading}
          />
          <StatCard
            icon={Sparkles}
            label="Output tokens"
            value={
              dashData?.stats.total_output_tokens != null
                ? formatTokens(dashData.stats.total_output_tokens)
                : '-'
            }
            color="accent"
            loading={isLoading}
          />
        </div>
      </section>

      {/* ── Empty state — new user ──────────────────────────────── */}
      {isEmpty && (
        <div className="col-span-full flex flex-col items-center gap-4 rounded-xl border border-dashed border-surface-300 bg-surface-50 px-6 py-12 text-center dark:border-surface-700 dark:bg-surface-900/50">
          <LayoutDashboard
            size={40}
            className="text-surface-300 dark:text-surface-600"
          />
          <div>
            <p className="text-base font-medium text-surface-700 dark:text-surface-300">
              Welcome to Aevix!
            </p>
            <p className="mt-1 text-sm text-surface-500">
              Start a conversation or upload a file to see your activity here.
            </p>
          </div>
          <QuickActions />
        </div>
      )}

      {/* ── Loaded content ──────────────────────────────────────── */}
      {!hasError && !isEmpty && (
        <div className="space-y-6">
          {/* Quick actions */}
          <QuickActions />

          {/* Two-column: recent chats + recent docs */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <RecentChats
              chats={dashData?.recent_chats ?? []}
              loading={dashLoading}
              error={
                dashError instanceof Error ? dashError.message : null
              }
            />
            <RecentDocuments
              files={dashData?.recent_files ?? []}
              loading={dashLoading}
              error={
                dashError instanceof Error ? dashError.message : null
              }
            />
          </div>

          {/* Two-column: activity + usage */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ActivityFeed
              items={dashData?.recent_activity ?? []}
              loading={dashLoading}
              error={
                dashError instanceof Error ? dashError.message : null
              }
            />
            <UsageWidget
              totalInputTokens={usageData?.total_input_tokens ?? 0}
              totalOutputTokens={usageData?.total_output_tokens ?? 0}
              totalMessages={usageData?.total_messages ?? 0}
              totalConversations={usageData?.total_conversations ?? 0}
              storageTotalBytes={usageData?.storage_total_bytes ?? 0}
              storageTotalFiles={usageData?.storage_total_files ?? 0}
              dailyUsage={usageData?.daily_usage ?? []}
              loading={usageLoading}
              error={
                usageError instanceof Error ? usageError.message : null
              }
            />
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}
