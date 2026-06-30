/** Registration page.

Validates input client-side, submits to the API, and redirects
to the verification-notice page on success.
*/

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Eye, EyeOff, UserPlus } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()

  const register = useAuthStore((s) => s.register)
  const isLoading = useAuthStore((s) => s.isLoading)
  const error = useAuthStore((s) => s.error)

  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    displayName: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    if (!form.email.trim()) errors.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errors.email = 'Invalid email format'

    if (!form.username.trim()) errors.username = 'Username is required'
    else if (form.username.trim().length < 3)
      errors.username = 'Username must be at least 3 characters'
    else if (form.username.trim().length > 50)
      errors.username = 'Username must be 50 characters or less'

    if (!form.password) errors.password = 'Password is required'
    else if (form.password.length < 8)
      errors.password = 'Password must be at least 8 characters'

    if (form.password !== form.confirmPassword)
      errors.confirmPassword = 'Passwords do not match'

    if (form.displayName && form.displayName.length > 100)
      errors.displayName = 'Display name must be 100 characters or less'

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    try {
      await register(
        form.email.trim(),
        form.username.trim(),
        form.password,
        form.displayName.trim() || undefined,
      )
      navigate('/auth/verify-email-notice', { replace: true })
    } catch {
      // error is set in the store
    }
  }

  const inputClass = (field: string) =>
    `w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-indigo-500 dark:bg-gray-900 dark:text-white ${
      fieldErrors[field]
        ? 'border-red-300 dark:border-red-700'
        : 'border-gray-300 dark:border-gray-700'
    }`

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
        Create account
      </h1>
      <p className="mb-8 text-sm text-gray-500">
        Get started with Aevix
      </p>

      {/* General error */}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={update('email')}
            className={inputClass('email')}
            placeholder="you@example.com"
          />
          {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
        </div>

        {/* Username */}
        <div>
          <label htmlFor="username" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Username
          </label>
          <input
            id="username"
            type="text"
            autoComplete="username"
            value={form.username}
            onChange={update('username')}
            className={inputClass('username')}
            placeholder="johndoe"
          />
          {fieldErrors.username && <p className="mt-1 text-xs text-red-600">{fieldErrors.username}</p>}
        </div>

        {/* Display name */}
        <div>
          <label htmlFor="displayName" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Display name <span className="text-gray-400">(optional)</span>
          </label>
          <input
            id="displayName"
            type="text"
            value={form.displayName}
            onChange={update('displayName')}
            className={inputClass('displayName')}
            placeholder="John Doe"
          />
          {fieldErrors.displayName && <p className="mt-1 text-xs text-red-600">{fieldErrors.displayName}</p>}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.password}
              onChange={update('password')}
              className={`${inputClass('password')} pr-10`}
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
          {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
        </div>

        {/* Confirm password */}
        <div>
          <label htmlFor="confirmPassword" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Confirm password
          </label>
          <input
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={form.confirmPassword}
            onChange={update('confirmPassword')}
            className={inputClass('confirmPassword')}
            placeholder="Repeat password"
          />
          {fieldErrors.confirmPassword && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.confirmPassword}</p>
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
            <UserPlus size={16} />
          )}
          {isLoading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <div className="mt-6 text-center text-sm text-gray-500">
        Already have an account?{' '}
        <Link to="/auth/login" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
          Sign in
        </Link>
      </div>
    </div>
  )
}
