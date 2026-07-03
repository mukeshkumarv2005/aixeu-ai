/** Security settings — active sessions, 2FA placeholder, link to profile for password. */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessions, useRevokeSession, useRevokeAllOtherSessions } from '@/api/settings'
import { Loader2, Smartphone, Monitor, Shield, KeyRound, LogOut } from 'lucide-react'

export default function SecuritySettings() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useSessions()
  const revokeSession = useRevokeSession()
  const revokeAll = useRevokeAllOtherSessions()

  const [revokingId, setRevokingId] = useState<string | null>(null)

  // ── Revoke single session ────────────────────────────────────────────────

  async function handleRevoke(sessionId: string) {
    setRevokingId(sessionId)
    try {
      await revokeSession.mutateAsync(sessionId)
    } catch {
      // handled by react-query
    } finally {
      setRevokingId(null)
    }
  }

  // ── Revoke all other sessions ────────────────────────────────────────────

  const [revokingAll, setRevokingAll] = useState(false)

  async function handleRevokeAll() {
    setRevokingAll(true)
    try {
      await revokeAll.mutateAsync()
    } catch {
      // handled by react-query
    } finally {
      setRevokingAll(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        Failed to load sessions.
      </div>
    )
  }

  const sessions = data?.items ?? []

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">Security</h2>
        <p className="text-sm text-muted-foreground">
          Manage your account security and active sessions.
        </p>
      </div>

      {/* ── Password ──────────────────────────────────────────────────────── */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">Password</h3>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <KeyRound className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Change Password</p>
                <p className="text-xs text-muted-foreground">
                  Update your account password.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-accent transition-colors"
            >
              Go to Profile
            </button>
          </div>
        </div>
      </section>

      {/* ── Two-Factor Authentication ─────────────────────────────────────── */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          Two-Factor Authentication
        </h3>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Two-Factor Authentication</p>
                <p className="text-xs text-muted-foreground">
                  Add an extra layer of security to your account.
                </p>
              </div>
            </div>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Coming soon
            </span>
          </div>
        </div>
      </section>

      {/* ── Sessions ──────────────────────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-muted-foreground">
            Active Sessions
          </h3>
          {sessions.length > 1 && (
            <button
              type="button"
              onClick={handleRevokeAll}
              disabled={revokingAll}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-destructive hover:text-destructive/80 transition-colors disabled:opacity-50"
            >
              {revokingAll ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <LogOut className="h-3 w-3" />
              )}
              Revoke all other
            </button>
          )}
        </div>

        {sessions.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
            <Monitor className="h-8 w-8" />
            <p className="text-sm">No active sessions found.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {s.is_current ? (
                    <Monitor className="h-5 w-5 shrink-0 text-primary" />
                  ) : (
                    <Smartphone className="h-5 w-5 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {s.device_name || 'Unknown device'}
                      </span>
                      {s.is_current && (
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-muted-foreground">
                      {s.ip_address || 'Unknown IP'} &middot;{' '}
                      {s.created_at
                        ? new Date(s.created_at).toLocaleDateString()
                        : 'Unknown'}
                    </p>
                  </div>
                </div>

                {!s.is_current && (
                  <button
                    type="button"
                    onClick={() => handleRevoke(s.id)}
                    disabled={revokingId === s.id}
                    className="shrink-0 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                  >
                    {revokingId === s.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      'Revoke'
                    )}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
