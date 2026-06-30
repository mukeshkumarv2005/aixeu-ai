/** Reset-password page.

Reads ``token`` from URL search params, shows a new-password form.
On success redirects to login with a success indicator.
*/

import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff, KeyRound } from 'lucide-react'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const resetPassword = useAuthStore((s) => s.resetPassword)
  const isLoading = useAuthStore((s) => s.isLoading)
  const error = useAuthStore((s) => s.error)

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  if (!token) {
    return (
      <div className="text-center">
        <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
          Invalid link
        </h1>
        <p className="mb-8 text-sm text-gray-500">
          This password-reset link is missing the required token.
        </p>
        <Link
          to="/auth/forgot-password"
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Request a new reset link
        </Link>
      </div>
    )
  }

  const validate = (): boolean => {
    const errors: Record<string, string> = {}
    if (!password) errors.password = 'New password is required'
    else if (password.length < 8)
      errors.password = 'Password must be at least 8 characters'

    if (password !== confirmPassword)
      errors.confirmPassword = 'Passwords do not match'

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    try {
      await resetPassword(token, password)
      navigate('/auth/login?reset=success', { replace: true })
    } catch {
      // error is set in the store
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
        Reset password
      </h1>
      <p className="mb-8 text-sm text-gray-500">
        Enter your new password below.
      </p>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* New password */}
        <div>
          <label
            htmlFor="newPassword"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            New password
          </label>
          <div className="relative">
            <input
              id="newPassword"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 pr-10 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
                fieldErrors.password
                  ? 'border-red-300 dark:border-red-700'
                  : 'border-gray-300 dark:border-gray-700'
              }`}
              placeholder="Min. 8 characters"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {fieldErrors.password && (
            <p className="mt-1 text-xs text-red-600">
              {fieldErrors.password}
            </p>
          )}
        </div>

        {/* Confirm password */}
        <div>
          <label
            htmlFor="confirmPassword"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Confirm new password
          </label>
          <input
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
              fieldErrors.confirmPassword
                ? 'border-red-300 dark:border-red-700'
                : 'border-gray-300 dark:border-gray-700'
            }`}
            placeholder="Repeat password"
          />
          {fieldErrors.confirmPassword && (
            <p className="mt-1 text-xs text-red-600">
              {fieldErrors.confirmPassword}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <KeyRound size={16} />
          )}
          {isLoading ? 'Resetting…' : 'Reset password'}
        </button>
      </form>

      <div className="mt-6 text-center text-sm text-gray-500">
        Remember your password?{' '}
        <Link
          to="/auth/login"
          className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Sign in
        </Link>
      </div>
    </div>
  )
}
