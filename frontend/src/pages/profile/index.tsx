/** Profile page — view and edit account details.

Sections:
- User info card (avatar, role, member since, verified badge)
- Edit profile form (display_name, avatar_url)
- Change password form
- Danger zone (account status)
*/

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import {
  User,
  Mail,
  Shield,
  Calendar,
  BadgeCheck,
  AlertTriangle,
  LogOut,
  Save,
  Eye,
  EyeOff,
} from 'lucide-react'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, updateProfile, changePassword, logout, isLoading, error } =
    useAuthStore()

  // ── Edit profile state ────────────────────────────────
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '')
  const [profileSuccess, setProfileSuccess] = useState(false)

  // ── Change password state ─────────────────────────────
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileSuccess(false)
    try {
      await updateProfile({
        display_name: displayName || undefined,
        avatar_url: avatarUrl || undefined,
      })
      setProfileSuccess(true)
    } catch {
      // store error is displayed below
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordSuccess(false)
    setPasswordError('')

    if (newPassword !== confirmNewPassword) {
      setPasswordError('Passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }

    try {
      await changePassword(currentPassword, newPassword)
      setPasswordSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (err: unknown) {
      setPasswordError(
        err instanceof Error ? err.message : 'Failed to change password',
      )
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login', { replace: true })
  }

  if (!user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-gray-500">Loading profile…</p>
      </div>
    )
  }

  const initials = (user.display_name || user.username)
    .split(' ')
    .map((s) => s[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <div className="mx-auto max-w-2xl space-y-8 px-4 py-10">
      {/* ── Header ────────────────────────────────────── */}
      <div className="flex items-center gap-5">
        {/* Avatar */}
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt="Avatar"
            className="h-16 w-16 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 text-lg font-bold text-white">
            {initials}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {user.display_name || user.username}
            </h1>
            {user.is_verified && (
              <BadgeCheck className="h-5 w-5 text-blue-500" />
            )}
          </div>
          <p className="text-sm text-gray-500">@{user.username}</p>
        </div>
      </div>

      {/* ── Info card ─────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Account info
        </h2>
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <Mail size={15} className="text-gray-400" />
            {user.email}
          </div>
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <User size={15} className="text-gray-400" />
            {user.username}
          </div>
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <Shield size={15} className="text-gray-400" />
            Role: <span className="font-medium capitalize">{user.role}</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            <Calendar size={15} className="text-gray-400" />
            Joined {new Date(user.created_at).toLocaleDateString()}
          </div>
          <div className="flex items-center gap-2">
            {user.is_verified ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                <BadgeCheck size={12} /> Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                Unverified
              </span>
            )}
            {!user.is_active && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
                <AlertTriangle size={12} /> Inactive
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Edit profile ──────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Edit profile
        </h2>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}
        {profileSuccess && (
          <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-400">
            Profile updated successfully.
          </div>
        )}

        <form onSubmit={handleProfileSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Display name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              placeholder="Your display name"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Avatar URL
            </label>
            <input
              type="url"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              placeholder="https://example.com/avatar.jpg"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Save size={15} />
            )}
            Save changes
          </button>
        </form>
      </div>

      {/* ── Change password ───────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Change password
        </h2>

        {passwordSuccess && (
          <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-400">
            Password updated successfully.
          </div>
        )}
        {passwordError && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {passwordError}
          </div>
        )}

        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Current password
            </label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              required
            />
          </div>
          <div className="relative">
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
              New password
            </label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Confirm new password
            </label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              required
            />
          </div>
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : null}
              Update password
            </button>
            <button
              type="button"
              onClick={() => setShowPasswords(!showPasswords)}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
            >
              {showPasswords ? <EyeOff size={15} /> : <Eye size={15} />}
              {showPasswords ? 'Hide' : 'Show'}
            </button>
          </div>
        </form>
      </div>

      {/* ── Danger zone ───────────────────────────────── */}
      <div className="rounded-xl border border-red-200 bg-white p-5 dark:border-red-900/30 dark:bg-gray-950">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-red-500">
          Danger zone
        </h2>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
        >
          <LogOut size={15} />
          Sign out from all devices
        </button>
      </div>
    </div>
  )
}
