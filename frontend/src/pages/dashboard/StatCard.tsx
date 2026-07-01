/** Single stat card with icon, label, value, and optional trend. */

import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  /** Optional secondary description shown below the value. */
  subtext?: string
  /** Color variant for the icon background. */
  color?: 'primary' | 'accent' | 'green' | 'amber'
  /** Loading state — shows a skeleton placeholder. */
  loading?: boolean
}

const COLOR_CLASSES = {
  primary:
    'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400',
  accent:
    'bg-accent-50 text-accent-600 dark:bg-accent-900/20 dark:text-accent-400',
  green:
    'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400',
  amber:
    'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
} as const

export function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
  color = 'primary',
  loading = false,
}: StatCardProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-950">
        <div className="flex items-start gap-4">
          <div className="h-10 w-10 animate-pulse rounded-lg bg-surface-200 dark:bg-surface-800" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-20 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
            <div className="h-6 w-16 animate-pulse rounded bg-surface-200 dark:bg-surface-800" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-5 transition-colors hover:border-surface-300 dark:border-surface-800 dark:bg-surface-950 dark:hover:border-surface-700">
      <div className="flex items-start gap-4">
        <div className={cn('rounded-lg p-2.5', COLOR_CLASSES[color])}>
          <Icon size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-surface-500">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold text-surface-900 dark:text-white">
            {value}
          </p>
          {subtext && (
            <p className="mt-0.5 text-xs text-surface-400">{subtext}</p>
          )}
        </div>
      </div>
    </div>
  )
}
