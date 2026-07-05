/** Profile page — view and edit account details.
 */

import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import {
  User,
  Mail,
  Shield,
  Calendar,
  BadgeCheck,
  LogOut,
  Save,
  Eye,
  EyeOff,
  Camera,
  Trash2,
  Loader2,
} from 'lucide-react'
import { apiClient } from '@/lib/api'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, updateProfile, changePassword, logout, isLoading, error } =
    useAuthStore()

  // ── Avatar refs & upload states ───────────────────────
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarError, setAvatarError] = useState<string | null>(null)

  // ── Edit profile state ────────────────────────────────
  const [displayName, setDisplayName] = useState(user?.display_name || '')
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
      })
      setProfileSuccess(true)
    } catch {
      // store error is displayed below
    }
  }

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setAvatarUploading(true)
    setAvatarError(null)
    setProfileSuccess(false)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiClient.upload<{ id: string }>('/storage/upload', formData)
      const newAvatarUrl = `/api/v1/storage/public/${res.id}`
      await updateProfile({ avatar_url: newAvatarUrl })
      setProfileSuccess(true)
    } catch (err: unknown) {
      setAvatarError(err instanceof Error ? err.message : 'Failed to upload photo')
    } finally {
      setAvatarUploading(false)
    }
  }

  const handleRemoveAvatar = async () => {
    setAvatarUploading(true)
    setAvatarError(null)
    setProfileSuccess(false)
    try {
      await updateProfile({ avatar_url: '' })
      setProfileSuccess(true)
    } catch (err: unknown) {
      setAvatarError(err instanceof Error ? err.message : 'Failed to remove photo')
    } finally {
      setAvatarUploading(false)
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
        <p className="text-surface-500">Loading profile…</p>
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
    <div className="w-full px-4 py-8 sm:px-6 lg:px-8">
      {/* ── Two-Column Grid ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Left Column: User Card & Stats ── */}
        <div className="space-y-6 lg:col-span-1">
          {/* User Hero Card */}
          <div className="relative overflow-hidden rounded-xl border border-surface-200 bg-white shadow-sm dark:border-surface-850 dark:bg-surface-950">
            {/* Ambient Background Glow */}
            <div className="h-24 bg-linear-to-br from-primary-500/20 to-accent-600/30 dark:from-primary-950/40 dark:to-accent-950/20" />
            
            <div className="relative -mt-12 flex flex-col items-center px-4 pb-6 text-center">
              {/* Interactive Avatar Widget */}
              <div className="group relative flex h-24 w-24 shrink-0 cursor-pointer items-center justify-center rounded-full border-4 border-white bg-surface-100 shadow-md dark:border-surface-950 dark:bg-surface-900">
                {avatarUploading ? (
                  <div className="flex h-full w-full items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-xs">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt="Avatar"
                    className="h-full w-full rounded-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center rounded-full bg-linear-to-br from-primary-500 to-accent-600 text-2xl font-bold text-white">
                    {initials}
                  </div>
                )}
                
                {/* Upload Hover Overlay */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute inset-0 flex flex-col items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity hover:opacity-100 dark:bg-black/75"
                >
                  <Camera size={18} />
                  <span className="mt-1 text-[10px] font-medium">Upload</span>
                </div>
              </div>

              {/* Invisible File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleAvatarChange}
                accept="image/*"
                className="hidden"
                disabled={avatarUploading}
              />

              {/* Display Name & Handle */}
              <h2 className="mt-4 text-lg font-bold text-surface-900 dark:text-white">
                {user.display_name || user.username}
              </h2>
              <p className="text-xs text-surface-400">@{user.username}</p>

              {/* Verified Badge */}
              <div className="mt-2 flex items-center gap-1.5">
                {user.is_verified ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-400">
                    <BadgeCheck size={12} /> Verified Account
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-400">
                    Unverified Account
                  </span>
                )}
              </div>

              {/* Remove Photo Action */}
              {user.avatar_url && (
                <button
                  onClick={handleRemoveAvatar}
                  disabled={avatarUploading}
                  className="mt-4 flex items-center gap-1 text-[11px] font-semibold text-red-500 hover:text-red-650 transition-colors cursor-pointer"
                >
                  <Trash2 size={12} />
                  Remove Photo
                </button>
              )}
            </div>
          </div>

          {/* Account Details / Stats Card */}
          <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-850 dark:bg-surface-950">
            <h3 className="mb-4 text-xs font-bold uppercase tracking-wider text-surface-400">
              Account Attributes
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between border-b border-surface-50 pb-2.5 dark:border-surface-900">
                <span className="flex items-center gap-2 text-surface-500">
                  <Mail size={14} className="text-surface-400" />
                  Email
                </span>
                <span className="font-medium text-surface-900 dark:text-white truncate max-w-[150px]">
                  {user.email}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-surface-50 pb-2.5 dark:border-surface-900">
                <span className="flex items-center gap-2 text-surface-500">
                  <User size={14} className="text-surface-400" />
                  Username
                </span>
                <span className="font-medium text-surface-900 dark:text-white">
                  {user.username}
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-surface-50 pb-2.5 dark:border-surface-900">
                <span className="flex items-center gap-2 text-surface-500">
                  <Shield size={14} className="text-surface-400" />
                  Role
                </span>
                <span className="rounded bg-primary-100 px-1.5 py-0.5 text-xs font-semibold capitalize text-primary-750 dark:bg-primary-950/30 dark:text-primary-300">
                  {user.role}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-surface-500">
                  <Calendar size={14} className="text-surface-400" />
                  Joined Date
                </span>
                <span className="font-medium text-surface-900 dark:text-white">
                  {new Date(user.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right Column: Edit Forms ── */}
        <div className="space-y-6 lg:col-span-2">
          {/* Edit Profile Form */}
          <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-850 dark:bg-surface-950">
            <h3 className="mb-4 text-base font-bold text-surface-900 dark:text-white">
              Profile Configurations
            </h3>
            
            {avatarError && (
              <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-750 dark:bg-red-950/20 dark:text-red-400">
                {avatarError}
              </div>
            )}
            {error && (
              <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-750 dark:bg-red-950/20 dark:text-red-400">
                {error}
              </div>
            )}
            {profileSuccess && (
              <div className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400">
                Profile changes saved successfully.
              </div>
            )}

            <form onSubmit={handleProfileSubmit} className="space-y-5">
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-surface-700 dark:text-surface-300">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-xl border border-surface-250 bg-surface-50 px-4 py-2.5 text-sm outline-none transition-all focus:border-primary-400 focus:ring-2 focus:ring-primary-100 dark:border-surface-800 dark:bg-surface-900 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900/25"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || avatarUploading}
                className="flex items-center gap-2 rounded-xl bg-primary-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save size={15} />
                )}
                Save changes
              </button>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-850 dark:bg-surface-950">
            <h3 className="mb-4 text-base font-bold text-surface-900 dark:text-white">
              Update Password
            </h3>

            {passwordSuccess && (
              <div className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400">
                Password updated successfully.
              </div>
            )}
            {passwordError && (
              <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-755 dark:bg-red-950/20 dark:text-red-400">
                {passwordError}
              </div>
            )}

            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-surface-700 dark:text-surface-300">
                  Current Password
                </label>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full rounded-xl border border-surface-250 bg-surface-50 px-4 py-2.5 text-sm outline-none transition-all focus:border-primary-400 focus:ring-2 focus:ring-primary-100 dark:border-surface-800 dark:bg-surface-900 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900/25"
                  placeholder="••••••••"
                  required
                />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-surface-700 dark:text-surface-300">
                    New Password
                  </label>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-surface-250 bg-surface-50 px-4 py-2.5 text-sm outline-none transition-all focus:border-primary-400 focus:ring-2 focus:ring-primary-100 dark:border-surface-800 dark:bg-surface-900 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900/25"
                    placeholder="••••••••"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-surface-700 dark:text-surface-300">
                    Confirm New Password
                  </label>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-surface-250 bg-surface-50 px-4 py-2.5 text-sm outline-none transition-all focus:border-primary-400 focus:ring-2 focus:ring-primary-100 dark:border-surface-800 dark:bg-surface-900 dark:text-white dark:focus:border-primary-500 dark:focus:ring-primary-900/25"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>
              <div className="flex items-center gap-4 pt-1">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center gap-2 rounded-xl bg-primary-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
                >
                  {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Update password
                </button>
                <button
                  type="button"
                  onClick={() => setShowPasswords(!showPasswords)}
                  className="flex items-center gap-1.5 text-sm text-surface-500 hover:text-surface-700 dark:hover:text-surface-300 font-medium transition-colors cursor-pointer"
                >
                  {showPasswords ? <EyeOff size={15} /> : <Eye size={15} />}
                  {showPasswords ? 'Hide passwords' : 'Show passwords'}
                </button>
              </div>
            </form>
          </div>

          {/* Danger / Log Out Card */}
          <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-850 dark:bg-surface-950">
            <h3 className="mb-2 text-base font-bold text-amber-600 dark:text-amber-500">
              Log Out
            </h3>
            <p className="mb-4 text-xs text-surface-500">
              Sign out from this and all other active browser sessions.
            </p>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 rounded-xl border border-surface-250 px-4 py-2 text-sm font-semibold text-surface-700 hover:bg-surface-50 transition-colors dark:border-surface-800 dark:text-surface-300 dark:hover:bg-surface-900 cursor-pointer"
            >
              <LogOut size={15} />
              Sign out from all devices
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
