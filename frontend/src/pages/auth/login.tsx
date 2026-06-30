/** Login page — email/username + password form.

Redirects to home (or returnUrl) on success.
Shows inline field validation and a general error banner.
*/

import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff, LogIn } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirect = searchParams.get('redirect') || '/'

  const login = useAuthStore((s) => s.login)
  const isLoading = useAuthStore((s) => s.isLoading)
  const error = useAuthStore((s) => s.error)

  const [loginValue, setLoginValue] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validate = (): boolean => {
    const errors: Record<string, string> = {}
    if (!loginValue.trim()) errors.login = 'Email or username is required'
    if (!password) errors.password = 'Password is required'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    try {
      await login(loginValue.trim(), password)
      navigate(redirect, { replace: true })
    } catch {
      // error is set in the store
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
        Sign in
      </h1>
      <p className="mb-8 text-sm text-gray-500">
        Welcome back — enter your credentials
      </p>

      {/* General error */}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email / Username */}
        <div>
          <label
            htmlFor="login"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Email or username
          </label>
          <input
            id="login"
            type="text"
            autoComplete="username"
            value={loginValue}
            onChange={(e) => setLoginValue(e.target.value)}
            className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
              fieldErrors.login
                ? 'border-red-300 dark:border-red-700'
                : 'border-gray-300 dark:border-gray-700'
            }`}
            placeholder="you@example.com"
          />
          {fieldErrors.login && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.login}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="password"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 pr-10 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
                fieldErrors.password
                  ? 'border-red-300 dark:border-red-700'
                  : 'border-gray-300 dark:border-gray-700'
              }`}
              placeholder="••••••••"
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

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <LogIn size={16} />
          )}
          {isLoading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      {/* Links */}
      <div className="mt-6 flex items-center justify-between text-sm">
        <Link
          to="/auth/forgot-password"
          className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          Forgot password?
        </Link>
        <span className="text-gray-500">
          No account?{' '}
          <Link
            to="/auth/register"
            className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
          >
            Sign up
          </Link>
        </span>
      </div>
    </div>
  )
}
