/** Application top bar — hamburger menu, page title, theme toggle,
 * notification button, and user avatar dropdown.
 */

import { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Menu,
  Sun,
  Moon,
  Bell,
  LogOut,
  User,
  ChevronDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

// ---------------------------------------------------------------------------
// Route → page title mapping
// ---------------------------------------------------------------------------

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/chat': 'Chat',
  '/storage': 'File Storage',
  '/profile': 'Profile',
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TopbarProps {
  onMenuToggle: () => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Topbar({ onMenuToggle }: TopbarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { theme, setTheme } = useThemeStore()

  const [profileOpen, setProfileOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close the dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const pageTitle = ROUTE_TITLES[location.pathname] ?? 'Aevix'

  const handleLogout = async () => {
    setProfileOpen(false)
    await logout()
    navigate('/auth/login', { replace: true })
  }

  const nextTheme = theme === 'light' ? 'dark' : 'light'
  const ThemeIcon = theme === 'light' ? Moon : Sun

  const initials = (user?.display_name || user?.username || '?')
    .split(' ')
    .map((s) => s[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <header className="flex h-16 items-center justify-between border-b border-surface-200 bg-white px-4 dark:border-surface-800 dark:bg-surface-950">
      {/* ── Left: hamburger + title ─────────────────────────── */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300"
          title="Toggle sidebar"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-lg font-semibold text-surface-900 dark:text-white">
          {pageTitle}
        </h1>
      </div>

      {/* ── Right: actions ──────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={() => setTheme(nextTheme)}
          className="rounded-lg p-2 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300"
          title={`Switch to ${nextTheme} mode`}
        >
          <ThemeIcon size={18} />
        </button>

        {/* Notifications */}
        <button
          className="rounded-lg p-2 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300"
          title="Notifications"
        >
          <Bell size={18} />
        </button>

        {/* ── Profile dropdown ──────────────────────────── */}
        <div ref={menuRef} className="relative">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2 rounded-lg p-1.5 text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt=""
                className="h-8 w-8 rounded-full object-cover"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary-500 to-accent-600 text-xs font-bold text-white">
                {initials}
              </span>
            )}
            <ChevronDown size={14} className="text-surface-400" />
          </button>

          {/* Dropdown */}
          {profileOpen && (
            <div className="absolute right-0 top-full mt-1 w-56 overflow-hidden rounded-xl border border-surface-200 bg-white shadow-lg dark:border-surface-800 dark:bg-surface-950">
              {/* User info */}
              <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
                <p className="truncate text-sm font-medium text-surface-900 dark:text-white">
                  {user?.display_name || user?.username}
                </p>
                <p className="truncate text-xs text-surface-500">
                  {user?.email}
                </p>
              </div>

              {/* Actions */}
              <div className="p-1">
                <button
                  onClick={() => {
                    setProfileOpen(false)
                    navigate('/profile')
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  <User size={15} />
                  Profile
                </button>
                <button
                  onClick={() => setTheme(nextTheme)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  <ThemeIcon size={15} />
                  {nextTheme === 'dark' ? 'Dark mode' : 'Light mode'}
                </button>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <LogOut size={15} />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
