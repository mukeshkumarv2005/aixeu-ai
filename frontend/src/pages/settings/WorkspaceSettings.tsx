/** Workspace settings — default model, timezone, language, default agent. */

import { useState, useEffect } from 'react'
import { useSettings, useUpdateSettings } from '@/api/settings'
import type { UserSettingsResponse } from '@/types/settings'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/i18n'

// Common timezone list — abbreviated for UX clarity
const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Asia/Seoul',
  'Australia/Sydney',
  'Pacific/Auckland',
]

const MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 5' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
]

export default function WorkspaceSettings() {
  const { data: settings, isLoading, error } = useSettings()
  const updateSettings = useUpdateSettings()
  const { t } = useTranslation()

  // Local state for instant select rendering
  const [localModel, setLocalModel] = useState('gpt-4o')
  const [localTimezone, setLocalTimezone] = useState('UTC')
  const [localLanguage, setLocalLanguage] = useState('en')

  // Sync with server when settings fetch completes
  useEffect(() => {
    if (settings) {
      setLocalModel(settings.default_model)
      setLocalTimezone(settings.timezone)
      setLocalLanguage(settings.language)
    }
  }, [settings])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !settings) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        {t('Failed to load settings.')}
      </div>
    )
  }

  const saving = updateSettings.isPending

  function handleChange<K extends keyof UserSettingsResponse>(
    field: K,
    value: UserSettingsResponse[K],
  ) {
    updateSettings.mutate({ [field]: value } as Record<string, unknown>)
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">{t('Workspace')}</h2>
        <p className="text-sm text-muted-foreground">
          {t('Configure your default workspace preferences.')}
        </p>
      </div>

      {/* Default model */}
      <Section title={t('Default Model')} saving={saving}>
        <select
          value={localModel}
          onChange={(e) => {
            const val = e.target.value
            setLocalModel(val)
            handleChange('default_model', val)
          }}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary sm:w-72"
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted-foreground">
          {t('Used as the default when creating new chats and tasks.')}
        </p>
      </Section>

      {/* Timezone */}
      <Section title={t('Timezone')} saving={saving}>
        <select
          value={localTimezone}
          onChange={(e) => {
            const val = e.target.value
            setLocalTimezone(val)
            handleChange('timezone', val)
          }}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary sm:w-72"
        >
          {COMMON_TIMEZONES.map((tz) => (
            <option key={tz} value={tz}>
              {tz.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </Section>

      {/* Language */}
      <Section title={t('Language')} saving={saving}>
        <select
          value={localLanguage}
          onChange={(e) => {
            const val = e.target.value
            setLocalLanguage(val)
            handleChange('language', val)
          }}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary sm:w-72"
        >
          <option value="en">English</option>
          <option value="es">Español</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="ja">日本語</option>
          <option value="zh">中文</option>
        </select>
        <p className="mt-1 text-xs text-muted-foreground">
          {t('UI language. Some areas may remain in English.')}
        </p>
      </Section>

      {/* Default agent */}
      <Section title={t('Default Agent')} saving={saving}>
        <p className="text-sm text-muted-foreground">
          {t('Coming soon — select a default AI agent for new conversations.')}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {t('Stored as')} <code className="rounded bg-muted px-1 py-0.5">default_agent_id</code>.
        </p>
      </Section>
    </div>
  )
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
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>
      {children}
    </section>
  )
}
