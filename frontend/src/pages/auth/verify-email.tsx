/** Email verification page — two variants:

1. ``/auth/verify-email?token=...`` — auto-calls verify on mount.
2. ``/auth/verify-email-notice`` — post-registration "check your email" notice
   with a resend button.
*/

import { useEffect, useState } from 'react'
import { useSearchParams, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { CheckCircle, XCircle, Mail, Loader2 } from 'lucide-react'

// ── Token verification variant ───────────────────────────────────────────

function VerifyWithToken() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const verifyEmail = useAuthStore((s) => s.verifyEmail)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Missing verification token.')
      return
    }

    verifyEmail(token)
      .then(() => {
        setStatus('success')
        setMessage('Your email has been verified successfully!')
      })
      .catch((err: unknown) => {
        setStatus('error')
        setMessage(
          err instanceof Error ? err.message : 'Verification failed. The link may be invalid or expired.',
        )
      })
    // run only once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center gap-4 py-8 text-center">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-600" />
        <p className="text-sm text-gray-500">Verifying your email…</p>
      </div>
    )
  }

  return (
    <div className="text-center">
      <div
        className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full ${
          status === 'success'
            ? 'bg-green-100 dark:bg-green-900/30'
            : 'bg-red-100 dark:bg-red-900/30'
        }`}
      >
        {status === 'success' ? (
          <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
        ) : (
          <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
        )}
      </div>
      <h1
        className={`mb-1 text-2xl font-bold ${
          status === 'success'
            ? 'text-gray-900 dark:text-white'
            : 'text-red-700 dark:text-red-400'
        }`}
      >
        {status === 'success' ? 'Verified!' : 'Verification failed'}
      </h1>
      <p className="mb-8 text-sm text-gray-500">{message}</p>

      {status === 'success' ? (
        <Link
          to="/auth/login"
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Sign in to your account
        </Link>
      ) : (
        <Link
          to="/auth/verify-email-notice"
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Request a new verification email
        </Link>
      )}
    </div>
  )
}

// ── Post-registration notice variant ─────────────────────────────────────

function VerifyNotice() {
  const resendVerification = useAuthStore((s) => s.resendVerification)
  const isLoading = useAuthStore((s) => s.isLoading)
  const isAuthenticated = useAuthStore((s) => s.accessToken !== null)
  const [resent, setResent] = useState(false)

  const handleResend = async () => {
    try {
      await resendVerification()
      setResent(true)
    } catch {
      // Silently ignore — the API logs the error
    }
  }

  return (
    <div className="text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/30">
        <Mail className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
      </div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
        Check your email
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        We&apos;ve sent a verification link to your email address. Click the
        link to activate your account.
      </p>

      <p className="mb-8 text-xs text-gray-400">
        It may take a few minutes to arrive. Check your spam folder.
      </p>

      <button
        onClick={handleResend}
        disabled={isLoading || resent}
        className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {resent
          ? 'Verification email sent!'
          : isLoading
            ? 'Sending…'
            : 'Resend verification email'}
      </button>

      {isAuthenticated && (
        <div className="mt-4">
          <Link
            to="/"
            className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
          >
            Skip — go to home
          </Link>
        </div>
      )}
    </div>
  )
}

// ── Router entry — chooses variant by path ───────────────────────────────

export default function VerifyEmailPage() {
  const location = useLocation()
  const hasToken = new URLSearchParams(location.search).has('token')

  if (hasToken) return <VerifyWithToken />
  return <VerifyNotice />
}
