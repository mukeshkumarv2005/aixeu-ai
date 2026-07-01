/** App shell layout — responsive sidebar + topbar + routed content.
 *
 * This is the main authenticated application frame. All protected pages
 * render inside this layout as child routes via <Outlet />.
 */

import { useState, useCallback, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // Close the mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  // On small screens, start with the sidebar closed
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      setSidebarOpen(!e.matches)
    }
    handler(mq)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const handleToggle = useCallback(() => {
    const isMobile = window.innerWidth < 768
    if (isMobile) {
      setMobileOpen((prev) => !prev)
    } else {
      setSidebarOpen((prev) => !prev)
    }
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-surface-50 dark:bg-surface-950">
      {/* ── Desktop sidebar ───────────────────────────────── */}
      <div className="hidden md:flex">
        <Sidebar open={sidebarOpen} onToggle={handleToggle} />
      </div>

      {/* ── Mobile drawer overlay ─────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 transition-transform duration-200 md:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <Sidebar open={true} onToggle={handleToggle} />
      </div>

      {/* ── Main content area ─────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar onMenuToggle={handleToggle} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
