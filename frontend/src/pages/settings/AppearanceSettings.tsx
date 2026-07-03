/** Appearance settings — theme, accent, density, animations, font scale. */

import { useEffect, useState } from 'react'
import { useThemeStore, ACCENT_COLORS, DENSITY_OPTIONS } from '@/stores/theme'
import type { AccentColor, DensityOption } from '@/stores/theme'
import { useSettings, useUpdateSettings } from '@/api/settings'
import { cn } from '@/lib/utils'
import { Sun, Moon, Monitor, Check, Loader2 } from 'lucide-react'

const THEMES = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const

type Theme = 'light' | 'dark' | 'system'

export default function AppearanceSettings() {
  const store = useThemeStore()
  const { data: serverSettings, isLoading: loadingSettings } = useSettings()
  const updateSettings = useUpdateSettings()

  // Local buffer for font scale slider (persisted immediately on mouseup)
  const [fontScaleBuffer, setFontScaleBuffer] = useState(store.fontScale)

  // Initialise from server on first load (only if store still has defaults)
  useEffect(() => {
    if (serverSettings) {
      store.initializeFromServer(serverSettings)
    }
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Theme ────────────────────────────────────────────────────────────────

  function handleThemeChange(theme: Theme) {
    store.setTheme(theme)
    updateSettings.mutate({ theme })
  }

  // ── Accent color ─────────────────────────────────────────────────────────

  function handleAccentChange(color: AccentColor) {
    store.setAccentColor(color)
    updateSettings.mutate({ accent_color: color })
  }

  // ── Density ──────────────────────────────────────────────────────────────

  function handleDensityChange(density: DensityOption) {
    store.setDensity(density)
    updateSettings.mutate({ density })
  }

  // ── Animations ───────────────────────────────────────────────────────────

  function handleAnimationsToggle() {
    const next = !store.animationsEnabled
    store.setAnimationsEnabled(next)
    updateSettings.mutate({ animations_enabled: next })
  }

  // ── Font scale ───────────────────────────────────────────────────────────

  function handleFontScaleCommit() {
    store.setFontScale(fontScaleBuffer)
    updateSettings.mutate({ font_scale: fontScaleBuffer })
  }

  // ── Sidebar default open ─────────────────────────────────────────────────

  function handleSidebarToggle() {
    const next = !store.sidebarDefaultOpen
    store.setSidebarDefaultOpen(next)
    updateSettings.mutate({ sidebar_default_open: next })
  }

  const saving = updateSettings.isPending

  if (loadingSettings) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">Appearance</h2>
        <p className="text-sm text-muted-foreground">
          Customise how Aevix looks and feels.
        </p>
      </div>

      {/* Theme */}
      <Section title="Theme" saving={saving}>
        <div className="flex flex-wrap gap-3">
          {THEMES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleThemeChange(value)}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors',
                store.theme === value
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
              {store.theme === value && <Check className="ml-1 h-3.5 w-3.5" />}
            </button>
          ))}
        </div>
      </Section>

      {/* Accent colour */}
      <Section title="Accent Color" saving={saving}>
        <div className="flex flex-wrap gap-3">
          {ACCENT_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              title={color}
              onClick={() => handleAccentChange(color as AccentColor)}
              className={cn(
                'h-9 w-9 rounded-full border-2 transition-all',
                store.accentColor === color
                  ? 'border-foreground scale-110'
                  : 'border-transparent hover:scale-105',
              )}
              style={{ backgroundColor: colorSwatch(color) }}
            >
              {store.accentColor === color && (
                <Check className="mx-auto h-4 w-4 text-white drop-shadow" />
              )}
            </button>
          ))}
        </div>
      </Section>

      {/* Density */}
      <Section title="Density" saving={saving}>
        <div className="flex flex-wrap gap-3">
          {DENSITY_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => handleDensityChange(d as DensityOption)}
              className={cn(
                'rounded-lg border px-4 py-2 text-sm font-medium capitalize transition-colors',
                store.density === d
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border hover:bg-accent hover:text-accent-foreground',
              )}
            >
              {d}
              {store.density === d && <Check className="ml-1.5 inline h-3.5 w-3.5" />}
            </button>
          ))}
        </div>
      </Section>

      {/* Sidebar default open */}
      <Section title="Sidebar" saving={saving}>
        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={store.sidebarDefaultOpen}
            onChange={handleSidebarToggle}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
          />
          Keep sidebar open by default
        </label>
      </Section>

      {/* Animations */}
      <Section title="Animations" saving={saving}>
        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={store.animationsEnabled}
            onChange={handleAnimationsToggle}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
          />
          Enable animations & transitions
        </label>
      </Section>

      {/* Font scale */}
      <Section title="Font Scale" saving={saving}>
        <div className="flex items-center gap-4">
          <span className="text-xs text-muted-foreground">75%</span>
          <input
            type="range"
            min={75}
            max={150}
            step={5}
            value={fontScaleBuffer}
            onChange={(e) => setFontScaleBuffer(Number(e.target.value))}
            onMouseUp={handleFontScaleCommit}
            onKeyUp={(e) => {
              if (e.key === 'Enter' || e.key === ' ') handleFontScaleCommit()
            }}
            className="flex-1 accent-primary"
            aria-label="Font scale"
          />
          <span className="text-xs text-muted-foreground">150%</span>
          <span className="w-10 text-right text-sm font-medium">{fontScaleBuffer}%</span>
        </div>
      </Section>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function colorSwatch(color: string): string {
  const swatches: Record<string, string> = {
    indigo: '#4f46e5',
    emerald: '#10b981',
    amber: '#f59e0b',
    rose: '#e11d48',
    violet: '#8b5cf6',
    sky: '#0ea5e9',
  }
  return swatches[color] ?? '#4f46e5'
}

function Section({
  title,
  children,
  saving,
}: {
  title: string
  children: React.ReactNode
  saving: boolean
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>
      {children}
    </section>
  )
}
