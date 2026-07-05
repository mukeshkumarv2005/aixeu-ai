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
  Settings,
  ChevronDown,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { SearchBar } from '@/components/search/SearchBar'
import { useTranslation } from '@/lib/i18n'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Route → page title mapping
// ---------------------------------------------------------------------------

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/search': 'Search',
  '/chat': 'Chat',
  '/storage': 'File Storage',
  '/knowledge': 'Knowledge Base',
  '/tasks': 'Tasks',
  '/profile': 'Profile',
  '/settings': 'Settings',
  '/settings/appearance': 'Appearance',
  '/settings/workspace': 'Workspace',
  '/settings/providers': 'AI Providers',
  '/settings/notifications': 'Notifications',
  '/settings/security': 'Security',
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
  const { t } = useTranslation()

  const [profileOpen, setProfileOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const notificationRef = useRef<HTMLDivElement>(null)
  const [notifications, setNotifications] = useState([
    {
      id: '1',
      title: 'Welcome to Aevix',
      description: 'Explore the dashboard, chat with AI, and manage your tasks.',
      time: 'Just now',
      read: false,
    },
    {
      id: '2',
      title: 'AI model updated',
      description: 'Your default AI assistant is configured and ready.',
      time: '10m ago',
      read: false,
    },
  ])

  // Close the dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
      if (notificationRef.current && !notificationRef.current.contains(e.target as Node)) {
        setNotificationsOpen(false)
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
          className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300 md:hidden"
          title="Toggle sidebar"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-lg font-semibold text-surface-900 dark:text-white">
          {t(pageTitle)}
        </h1>
      </div>

      {/* ── Center: global search (hidden on search page) ────── */}
      {location.pathname !== '/search' && (
        <div className="hidden flex-1 px-4 md:block lg:max-w-md xl:max-w-lg">
          <SearchBar
            navigateOnEnter
            placeholder="Search…"
            onResultSelect={() => {}}
          />
        </div>
      )}

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
        <div ref={notificationRef} className="relative">
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative rounded-lg p-2 text-surface-500 hover:bg-surface-100 hover:text-surface-700 dark:hover:bg-surface-800 dark:hover:text-surface-300"
            title="Notifications"
          >
            <Bell size={18} />
            {notifications.some((n) => !n.read) && (
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary-500" />
            )}
          </button>

          {/* Dropdown */}
          {notificationsOpen && (
            <div className="absolute right-0 mt-1 z-50 w-80 rounded-xl border border-surface-200 bg-white p-2 shadow-lg dark:border-surface-800 dark:bg-surface-950">
              <div className="flex items-center justify-between border-b border-surface-100 px-3 py-2 pb-2 dark:border-surface-800">
                <span className="text-xs font-semibold text-surface-900 dark:text-white">
                  Notifications
                </span>
                {notifications.length > 0 && (
                  <button
                    onClick={() => setNotifications([])}
                    className="text-[10px] font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto py-1">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Bell className="h-8 w-8 text-surface-300 dark:text-surface-600" />
                    <span className="mt-2 text-xs text-surface-500 dark:text-surface-400">
                      No notifications
                    </span>
                  </div>
                ) : (
                  <div className="divide-y divide-surface-100 dark:divide-surface-800">
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        onClick={() => {
                          setNotifications((prev) =>
                            prev.map((item) =>
                              item.id === n.id ? { ...item, read: true } : item,
                            ),
                          )
                        }}
                        className={cn(
                          'p-3 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-900 cursor-pointer rounded-lg',
                          !n.read && 'bg-primary-50/10',
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p
                            className={cn(
                              'text-xs font-semibold text-surface-900 dark:text-white',
                              !n.read && 'text-primary-600 dark:text-primary-400',
                            )}
                          >
                            {n.title}
                          </p>
                          <span className="shrink-0 text-[10px] text-surface-400">
                            {n.time}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-surface-500 dark:text-surface-400 line-clamp-2">
                          {n.description}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

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
                  {t('Profile')}
                </button>
                <button
                  onClick={() => {
                    setProfileOpen(false)
                    navigate('/settings')
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  <Settings size={15} />
                  {t('Settings')}
                </button>
                <button
                  onClick={() => setTheme(nextTheme)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                >
                  <ThemeIcon size={15} />
                  {nextTheme === 'dark' ? t('Dark mode') : t('Light mode')}
                </button>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <LogOut size={15} />
                  {t('Sign out')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
