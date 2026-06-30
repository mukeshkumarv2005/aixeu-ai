/** Route guard that redirects to login if unauthenticated.

Wraps child routes with auth and loading checks. Supports optional
``requiredRole`` prop for RBAC.
*/

import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'

interface Props {
  requiredRole?: string
}

export function ProtectedRoute({ requiredRole }: Props) {
  const { accessToken, user, isLoading } = useAuthStore()
  const location = useLocation()

  // ── Loading state ────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-gray-500">Loading…</p>
        </div>
      </div>
    )
  }

  // ── Unauthenticated ──────────────────────────────────
  if (!accessToken || !user) {
    const redirect = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/auth/login?redirect=${redirect}`} replace />
  }

  // ── Role check ───────────────────────────────────────
  if (requiredRole) {
    const roleHierarchy: Record<string, number> = { user: 1, admin: 9 }
    const userLevel = roleHierarchy[user.role] ?? 0
    const requiredLevel = roleHierarchy[requiredRole] ?? 0
    if (userLevel < requiredLevel) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-800">403</h1>
            <p className="mt-2 text-gray-500">
              You don&apos;t have permission to access this page.
            </p>
            <a href="/" className="mt-4 inline-block text-indigo-600 hover:underline">
              Go home
            </a>
          </div>
        </div>
      )
    }
  }

  return <Outlet />
}
