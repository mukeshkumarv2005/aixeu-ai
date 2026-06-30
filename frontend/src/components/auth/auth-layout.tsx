/** Centered card layout for all authentication pages.

Renders children inside a narrow card with the Aevix branding,
no sidebar or nav — clean focus on the form.
*/

import { Outlet, Link } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4 dark:from-gray-950 dark:to-gray-900">
      <div className="w-full max-w-md">
        {/* ── Branding ─────────────────────────────── */}
        <div className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-2 text-2xl font-bold text-gray-900 dark:text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-sm font-bold text-white">
              A
            </span>
            Aevix
          </Link>
        </div>

        {/* ── Card ─────────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <Outlet />
        </div>

        {/* ── Footer ───────────────────────────────── */}
        <p className="mt-6 text-center text-xs text-gray-400">
          &copy; {new Date().getFullYear()} Aevix. All rights reserved.
        </p>
      </div>
    </div>
  )
}
