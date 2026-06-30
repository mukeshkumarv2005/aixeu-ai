import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'

async function fetchHealth(): Promise<{ status: string; app: string; version: string }> {
  const res = await fetch('/api/v1/health')
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export function HomePage() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="text-center">
        {/* Logo / Brand */}
        <h1 className="text-6xl font-bold tracking-tight text-surface-900 dark:text-white">
          Aevix
        </h1>
        <p className="mt-3 text-lg text-surface-500 dark:text-surface-400">
          Your Intelligent AI Workspace
        </p>

        {/* Wait animation while the backend status loads */}
        {isLoading && (
          <p className="mt-6 text-sm text-surface-400 animate-pulse">
            Connecting to backend…
          </p>
        )}

        {/* Backend health status */}
        {health && (
          <div
            className={cn(
              'mx-auto mt-8 inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm',
              health.status === 'ok'
                ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400',
            )}
          >
            <span
              className={cn(
                'inline-block h-2 w-2 rounded-full',
                health.status === 'ok' ? 'bg-green-500' : 'bg-red-500',
              )}
            />
            {health.status === 'ok'
              ? `${health.app} v${health.version} — connected`
              : 'Backend unavailable'}
          </div>
        )}

        {/* Status bar at bottom */}
        <div className="fixed bottom-4 text-center text-xs text-surface-400">
          <span>Built with React + FastAPI</span>
        </div>
      </div>
    </div>
  )
}
