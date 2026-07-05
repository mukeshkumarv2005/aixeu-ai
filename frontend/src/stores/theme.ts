import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

// Allowed values for appearance fields
export const ACCENT_COLORS = ['indigo', 'emerald', 'amber', 'rose', 'violet', 'sky'] as const
export type AccentColor = (typeof ACCENT_COLORS)[number]

export const DENSITY_OPTIONS = ['comfortable', 'compact'] as const
export type DensityOption = (typeof DENSITY_OPTIONS)[number]

const MIN_FONT_SCALE = 75
const MAX_FONT_SCALE = 150

interface ThemeState {
  theme: Theme
  accentColor: AccentColor
  density: DensityOption
  animationsEnabled: boolean
  fontScale: number
  sidebarDefaultOpen: boolean

  setTheme: (theme: Theme) => void
  setAccentColor: (color: AccentColor) => void
  setDensity: (density: DensityOption) => void
  setAnimationsEnabled: (enabled: boolean) => void
  setFontScale: (scale: number) => void
  setSidebarDefaultOpen: (open: boolean) => void
  resolvedTheme: () => 'light' | 'dark'

  /** Merge server-side appearance fields into the store without overwriting local changes on first load. */
  initializeFromServer: (server: {
    theme?: string
    accent_color?: string
    density?: string
    animations_enabled?: boolean
    font_scale?: number
    sidebar_default_open?: boolean
  }) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      accentColor: 'amber',
      density: 'comfortable',
      animationsEnabled: true,
      fontScale: 100,
      sidebarDefaultOpen: true,

      setTheme: (theme: Theme) => {
        set({ theme })
        applyTheme(theme)
      },
      setAccentColor: (color: AccentColor) => {
        set({ accentColor: color })
        applyAccentColor(color)
      },
      setDensity: (density: DensityOption) => {
        set({ density })
        applyDensity(density)
      },
      setAnimationsEnabled: (enabled: boolean) => {
        set({ animationsEnabled: enabled })
        applyAnimations(enabled)
      },
      setFontScale: (scale: number) => {
        const clamped = Math.min(MAX_FONT_SCALE, Math.max(MIN_FONT_SCALE, scale))
        set({ fontScale: clamped })
        applyFontScale(clamped)
      },
      setSidebarDefaultOpen: (open: boolean) => set({ sidebarDefaultOpen: open }),
      resolvedTheme: () => {
        const { theme } = get()
        if (theme === 'system') {
          return window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light'
        }
        return theme
      },

      initializeFromServer: (server) => {
        // Only set fields that are still at initial defaults — never overwrite
        // user's persisted local changes.
        const state = get()
        const patches: Partial<ThemeState> = {}

        if (state.theme === 'dark' && server.theme) {
          const t = server.theme as Theme
          if (['light', 'dark', 'system'].includes(t)) {
            patches.theme = t
          }
        }
        if (state.accentColor === 'indigo' && server.accent_color) {
          const c = server.accent_color as AccentColor
          if ((ACCENT_COLORS as readonly string[]).includes(c)) {
            patches.accentColor = c
          }
        }
        if (state.density === 'comfortable' && server.density) {
          const d = server.density as DensityOption
          if ((DENSITY_OPTIONS as readonly string[]).includes(d)) {
            patches.density = d
          }
        }
        if (state.animationsEnabled && !server.animations_enabled) {
          patches.animationsEnabled = false
        }
        if (state.fontScale === 100 && server.font_scale != null) {
          patches.fontScale = Math.min(
            MAX_FONT_SCALE,
            Math.max(MIN_FONT_SCALE, server.font_scale),
          )
        }
        if (state.sidebarDefaultOpen && !server.sidebar_default_open) {
          patches.sidebarDefaultOpen = false
        }

        if (Object.keys(patches).length > 0) {
          set(patches)
        }

        // Apply all visual effects from whatever state we end up with
        applyEffects(get())
      },
    }),
    { name: 'aevix-theme' },
  ),
)

// ── DOM effect helpers ───────────────────────────────────────────────────────

function applyTheme(theme: Theme) {
  const root = document.documentElement
  const isDark =
    theme === 'dark' ||
    (theme === 'system' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches)

  root.classList.toggle('dark', isDark)
}

function applyAccentColor(color: AccentColor) {
  const root = document.documentElement
  // Map logical accent names to Tailwind v3 color values
  const colorMap: Record<AccentColor, string> = {
    indigo: '#d97706',  // Map to Warm Gold/Amber
    emerald: '#10b981',
    amber: '#f59e0b',
    rose: '#e11d48',
    violet: '#7c2d12',  // Warm Rust
    sky: '#fbbf24',     // Champagne Gold
  }
  root.style.setProperty('--color-accent', colorMap[color] ?? colorMap.indigo)
  root.style.setProperty('--color-accent-hover', adjustBrightness(colorMap[color] ?? colorMap.indigo, -15))
  root.style.setProperty('--color-accent-light', colorMap[color] ?? colorMap.indigo)
}

function applyDensity(density: DensityOption) {
  document.documentElement.setAttribute('data-density', density)
}

function applyAnimations(enabled: boolean) {
  document.documentElement.classList.toggle('reduce-animations', !enabled)
}

function applyFontScale(scale: number) {
  document.documentElement.style.setProperty('--font-scale', `${scale / 100}`)
}

function applyEffects(state: ThemeState) {
  applyTheme(state.theme)
  applyAccentColor(state.accentColor)
  applyDensity(state.density)
  applyAnimations(state.animationsEnabled)
  applyFontScale(state.fontScale)
}

/** Darken/lighten a hex color by `percent` (-100..100). */
function adjustBrightness(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = Math.min(255, Math.max(0, (num >> 16) + Math.round((percent / 100) * 255)))
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + Math.round((percent / 100) * 255)))
  const b = Math.min(255, Math.max(0, (num & 0xff) + Math.round((percent / 100) * 255)))
  return `rgb(${r}, ${g}, ${b})`
}

// ── Apply on load and listen for system changes ──────────────────────────────

const initialState = useThemeStore.getState()
applyEffects(initialState)

window
  .matchMedia('(prefers-color-scheme: dark)')
  .addEventListener('change', () => {
    const state = useThemeStore.getState()
    if (state.theme === 'system') {
      applyTheme('system')
    }
  })
