/** Forgot-password page — email input only.

Always shows a success message to prevent user enumeration.
*/

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { MessageSquare } from 'lucide-react'

export default function ForgotPasswordPage() {
  const forgotPassword = useAuthStore((s) => s.forgotPassword)
  const isLoading = useAuthStore((s) => s.isLoading)

  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [fieldError, setFieldError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email.trim()) {
      setFieldError('Email is required')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setFieldError('Invalid email format')
      return
    }

    setFieldError('')
    try {
      await forgotPassword(email.trim())
      setSent(true)
    } catch {
      // Always show success to prevent enumeration
      setSent(true)
    }
  }

  if (sent) {
    return (
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
          <MessageSquare className="h-6 w-6 text-green-600 dark:text-green-400" />
        </div>
        <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
          Check your email
        </h1>
        <p className="mb-2 text-sm text-gray-500">
          If an account with <strong>{email}</strong> exists, we&apos;ve sent a
          password-reset link.
        </p>
        <p className="mb-8 text-xs text-gray-400">
          It may take a few minutes to arrive. Check your spam folder too.
        </p>
        <Link
          to="/auth/login"
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Back to sign in
        </Link>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
        Forgot password
      </h1>
      <p className="mb-8 text-sm text-gray-500">
        Enter your email and we&apos;ll send you a reset link.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor="email"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
              fieldError
                ? 'border-red-300 dark:border-red-700'
                : 'border-gray-300 dark:border-gray-700'
            }`}
            placeholder="you@example.com"
          />
          {fieldError && (
            <p className="mt-1 text-xs text-red-600">{fieldError}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : null}
          {isLoading ? 'Sending…' : 'Send reset link'}
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
