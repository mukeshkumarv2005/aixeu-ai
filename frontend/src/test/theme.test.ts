import { describe, it, expect, beforeEach } from 'vitest'
import { useThemeStore } from '../stores/theme'

describe('Theme Store', () => {
  beforeEach(() => {
    // Reset state to default values
    useThemeStore.setState({
      theme: 'dark',
      accentColor: 'indigo',
      density: 'comfortable',
      animationsEnabled: true,
      fontScale: 100,
      sidebarDefaultOpen: true,
    })
  })

  it('sets theme', () => {
    useThemeStore.getState().setTheme('light')
    expect(useThemeStore.getState().theme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('sets accent color', () => {
    useThemeStore.getState().setAccentColor('emerald')
    expect(useThemeStore.getState().accentColor).toBe('emerald')
    expect(document.documentElement.style.getPropertyValue('--color-accent')).toBe('#10b981')
  })

  it('sets density', () => {
    useThemeStore.getState().setDensity('compact')
    expect(useThemeStore.getState().density).toBe('compact')
    expect(document.documentElement.getAttribute('data-density')).toBe('compact')
  })

  it('sets animations enabled/disabled', () => {
    useThemeStore.getState().setAnimationsEnabled(false)
    expect(useThemeStore.getState().animationsEnabled).toBe(false)
    expect(document.documentElement.classList.contains('reduce-animations')).toBe(true)
  })

  it('sets font scale with clamping', () => {
    useThemeStore.getState().setFontScale(120)
    expect(useThemeStore.getState().fontScale).toBe(120)
    expect(document.documentElement.style.getPropertyValue('--font-scale')).toBe('1.2')

    // Clamp low
    useThemeStore.getState().setFontScale(50)
    expect(useThemeStore.getState().fontScale).toBe(75)

    // Clamp high
    useThemeStore.getState().setFontScale(200)
    expect(useThemeStore.getState().fontScale).toBe(150)
  })

  it('resolves system theme', () => {
    // Our setup.ts mocks prefers-color-scheme: dark to false, so it should resolve system theme to light.
    useThemeStore.getState().setTheme('system')
    expect(useThemeStore.getState().resolvedTheme()).toBe('light')
  })

  it('initializes from server settings', () => {
    useThemeStore.getState().initializeFromServer({
      theme: 'light',
      accent_color: 'amber',
      density: 'compact',
      animations_enabled: false,
      font_scale: 110,
      sidebar_default_open: false,
    })

    expect(useThemeStore.getState().theme).toBe('light')
    expect(useThemeStore.getState().accentColor).toBe('amber')
    expect(useThemeStore.getState().density).toBe('compact')
    expect(useThemeStore.getState().animationsEnabled).toBe(false)
    expect(useThemeStore.getState().fontScale).toBe(110)
    expect(useThemeStore.getState().sidebarDefaultOpen).toBe(false)
  })
})
