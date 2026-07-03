/** Notification preferences — email and browser notification toggles. */

import { useSettings, useUpdateSettings } from '@/api/settings'
import { Loader2 } from 'lucide-react'

interface ToggleGroup {
  title: string
  toggles: {
    key: string
    label: string
    description: string
    defaultValue: boolean
  }[]
}

const GROUPS: ToggleGroup[] = [
  {
    title: 'Tasks',
    toggles: [
      {
        key: 'notify_email_task_reminders',
        label: 'Email — task reminders',
        description: 'Receive email notifications for upcoming task due dates.',
        defaultValue: true,
      },
      {
        key: 'notify_browser_task_reminders',
        label: 'Browser — task reminders',
        description: 'Receive in-app notifications for upcoming tasks.',
        defaultValue: true,
      },
    ],
  },
  {
    title: 'AI Agents',
    toggles: [
      {
        key: 'notify_email_agent_completion',
        label: 'Email — agent completion',
        description: 'Get an email when an AI agent finishes its run.',
        defaultValue: true,
      },
      {
        key: 'notify_browser_agent_completion',
        label: 'Browser — agent completion',
        description: 'Get an in-app notification when an AI agent finishes.',
        defaultValue: true,
      },
    ],
  },
  {
    title: 'Documents',
    toggles: [
      {
        key: 'notify_email_document_processing',
        label: 'Email — document processing',
        description: 'Get an email when document processing completes.',
        defaultValue: true,
      },
    ],
  },
  {
    title: 'Knowledge',
    toggles: [
      {
        key: 'notify_email_knowledge_indexing',
        label: 'Email — knowledge indexing',
        description: 'Get an email when knowledge base indexing completes.',
        defaultValue: false,
      },
    ],
  },
]

export default function NotificationSettings() {
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
        Failed to load notification settings.
      </div>
    )
  }

  const saving = updateSettings.isPending

  function handleToggle(key: string, currentValue: boolean) {
    updateSettings.mutate({ [key]: !currentValue })
  }

  // ── Browser notification permission ──────────────────────────────────────

  function handleRequestBrowserPermission() {
    if (!('Notification' in window)) return
    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">Notifications</h2>
        <p className="text-sm text-muted-foreground">
          Control which notifications you receive and how they are delivered.
        </p>
      </div>

      {GROUPS.map((group) => (
        <section key={group.title} className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">{group.title}</h3>
          <div className="space-y-2">
            {group.toggles.map((t) => {
              const value =
                (settings as unknown as Record<string, unknown>)[t.key] ?? t.defaultValue
              return (
                <label
                  key={t.key}
                  className="flex cursor-pointer items-center justify-between rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:bg-accent/50"
                >
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium">{t.label}</p>
                    <p className="text-xs text-muted-foreground">{t.description}</p>
                  </div>
                  <div className="relative ml-4 shrink-0">
                    <input
                      type="checkbox"
                      checked={Boolean(value)}
                      onChange={() => handleToggle(t.key, Boolean(value))}
                      className="peer sr-only"
                    />
                    <div className="h-5 w-9 rounded-full bg-muted-foreground/30 transition-colors peer-checked:bg-primary after:absolute after:left-0.5 after:top-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-4" />
                  </div>
                </label>
              )
            })}
          </div>
        </section>
      ))}

      {/* Browser permission notice */}
      <section className="space-y-2">
        <h3 className="text-sm font-medium text-muted-foreground">Browser Notifications</h3>
        <p className="text-xs text-muted-foreground">
          Browser notifications require your permission. If you toggled a browser
          notification above but don&apos;t see them, you may need to{' '}
          <button
            type="button"
            onClick={handleRequestBrowserPermission}
            className="underline hover:text-foreground transition-colors"
          >
            grant permission
          </button>
          .
        </p>
        {typeof Notification !== 'undefined' && Notification.permission === 'denied' && (
          <p className="text-xs text-destructive">
            Browser notifications are blocked. Update your browser settings to
            enable them.
          </p>
        )}
      </section>

      {saving && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Saving...
        </div>
      )}
    </div>
  )
}
