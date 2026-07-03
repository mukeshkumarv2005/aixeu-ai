/** Settings layout — sidebar nav + <Outlet />. */

import { Outlet, NavLink } from 'react-router-dom'
import {
  Palette,
  Cog,
  Key,
  Bell,
  Shield,
  User,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const navItems: NavItem[] = [
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/settings/appearance', label: 'Appearance', icon: Palette },
  { to: '/settings/workspace', label: 'Workspace', icon: Cog },
  { to: '/settings/providers', label: 'AI Providers', icon: Key },
  { to: '/settings/notifications', label: 'Notifications', icon: Bell },
  { to: '/settings/security', label: 'Security', icon: Shield },
]

export default function SettingsLayout() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 sm:p-6 lg:flex-row">
      {/* Sidebar nav */}
      <nav className="flex shrink-0 flex-col gap-1 lg:w-48" aria-label="Settings navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/profile'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              }`
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Content */}
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}
