/** WidgetCard — shared card wrapper for dashboard widgets. */

interface WidgetCardProps {
  title: string
  children: React.ReactNode
  headerRight?: React.ReactNode
}

export function WidgetCard({ title, children, headerRight }: WidgetCardProps) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          {title}
        </h3>
        {headerRight && (
          <div className="flex items-center gap-2">{headerRight}</div>
        )}
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}
