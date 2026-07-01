/** Responsive collapsible sidebar navigation.
 *
 * Shows full labels when open, collapses to icon-only when closed.
 * Highlights the current route as active.
 */

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  Database,
  User,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Navigation items
// ---------------------------------------------------------------------------

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/storage', label: 'Storage', icon: Database },
  { to: '/profile', label: 'Profile', icon: User },
] as const

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SidebarProps {
  open: boolean
  onToggle: () => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Sidebar({ open, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'flex flex-col border-r border-surface-200 bg-white transition-all duration-200 dark:border-surface-800 dark:bg-surface-950',
        open ? 'w-60' : 'w-16',
      )}
    >
      {/* ── Brand ─────────────────────────────────────────── */}
      <div
        className={cn(
          'flex items-center border-b border-surface-200 px-3 dark:border-surface-800',
          open ? 'h-16 justify-between' : 'h-16 justify-center',
        )}
      >
        {open ? (
          <>
            <NavLink to="/dashboard" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-500 to-accent-600 text-sm font-bold text-white">
                A
              </span>
              <span className="text-base font-bold text-surface-900 dark:text-white">
                Aevix
              </span>
            </NavLink>
            <button
              onClick={onToggle}
              className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800 dark:hover:text-surface-300"
              title="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          </>
        ) : (
          <button
            onClick={onToggle}
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-600 dark:hover:bg-surface-800 dark:hover:text-surface-300"
            title="Expand sidebar"
          >
            <ChevronRight size={16} />
          </button>
        )}
      </div>

      {/* ── Navigation ────────────────────────────────────── */}
      <nav className="flex-1 space-y-1 p-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
                  : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800 dark:hover:text-surface-200',
                !open && 'justify-center px-0',
              )
            }
            title={!open ? label : undefined}
          >
            <Icon size={18} className="shrink-0" />
            {open && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* ── Footer ────────────────────────────────────────── */}
      {open && (
        <div className="border-t border-surface-200 px-3 py-3 dark:border-surface-800">
          <p className="text-center text-xs text-surface-400">
            Aevix v1.0
          </p>
        </div>
      )}
    </aside>
  )
}
