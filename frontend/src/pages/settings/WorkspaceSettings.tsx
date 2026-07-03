/** Workspace settings — default model, timezone, language, default agent. */

import { useSettings, useUpdateSettings } from '@/api/settings'
import type { UserSettingsResponse } from '@/types/settings'
import { Loader2 } from 'lucide-react'

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
        Failed to load settings.
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
        <h2 className="text-lg font-semibold">Workspace</h2>
        <p className="text-sm text-muted-foreground">
          Configure your default workspace preferences.
        </p>
      </div>

      {/* Default model */}
      <Section title="Default Model" saving={saving}>
        <select
          value={settings.default_model}
          onChange={(e) => handleChange('default_model', e.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary sm:w-72"
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted-foreground">
          Used as the default when creating new chats and tasks.
        </p>
      </Section>

      {/* Timezone */}
      <Section title="Timezone" saving={saving}>
        <select
          value={settings.timezone}
          onChange={(e) => handleChange('timezone', e.target.value)}
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
      <Section title="Language" saving={saving}>
        <select
          value={settings.language}
          onChange={(e) => handleChange('language', e.target.value)}
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
          UI language. Some areas may remain in English.
        </p>
      </Section>

      {/* Default agent */}
      <Section title="Default Agent" saving={saving}>
        <p className="text-sm text-muted-foreground">
          Coming soon — select a default AI agent for new conversations.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Stored as <code className="rounded bg-muted px-1 py-0.5">default_agent_id</code>.
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
