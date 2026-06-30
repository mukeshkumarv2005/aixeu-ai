/** In-memory auth store using Zustand (no persist — never touches localStorage).

Access tokens are stored only in memory and lost on refresh; the token
is a plain string rather than a React-ref object to allow reads from
the API client outside React components via ``getState()``.
*/

import { create } from 'zustand'
import { apiClient } from '@/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string
  email: string
  username: string
  display_name: string | null
  avatar_url: string | null
  role: string
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export interface AuthState {
  accessToken: string | null
  user: UserResponse | null
  isLoading: boolean
  error: string | null
}

export interface AuthActions {
  /** Persist an access token (called after successful refresh). */
  setAccessToken: (token: string) => void

  /** Clear the store and redirect to login. */
  clearAuth: () => void

  /** Attempt to log in with email/username + password. */
  login: (login: string, password: string) => Promise<void>

  /** Register a new account. */
  register: (
    email: string,
    username: string,
    password: string,
    displayName?: string,
  ) => Promise<void>

  /** Log out — calls API then clears state. */
  logout: () => Promise<void>

  /** Fetch current user profile (GET /auth/me). */
  fetchProfile: () => Promise<void>

  /** Update profile (display_name, avatar_url). */
  updateProfile: (data: {
    display_name?: string
    avatar_url?: string
  }) => Promise<void>

  /** Change password. */
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<void>

  /** Send forgot-password email. */
  forgotPassword: (email: string) => Promise<void>

  /** Reset password with token. */
  resetPassword: (token: string, newPassword: string) => Promise<void>

  /** Verify email with token. */
  verifyEmail: (token: string) => Promise<void>

  /** Resend verification email. */
  resendVerification: () => Promise<void>

  /** Attempt a silent refresh on app boot. */
  initialize: () => Promise<void>
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const initialState: AuthState = {
  accessToken: null,
  user: null,
  isLoading: true,
  error: null,
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  ...initialState,

  setAccessToken: (token: string) => set({ accessToken: token }),

  clearAuth: () =>
    set({
      accessToken: null,
      user: null,
      isLoading: false,
      error: null,
    }),

  login: async (login: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.post<{
        access_token: string
        user: UserResponse
      }>('/auth/login', { login, password })
      set({
        accessToken: res.access_token,
        user: res.user,
        isLoading: false,
      })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Login failed'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  register: async (
    email: string,
    username: string,
    password: string,
    displayName?: string,
  ) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.post<{
        access_token: string
        user: UserResponse
      }>('/auth/register', {
        email,
        username,
        password,
        display_name: displayName ?? null,
      })
      set({
        accessToken: res.access_token,
        user: res.user,
        isLoading: false,
      })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Registration failed'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // Even if the API call fails, clear local state
    } finally {
      set({ accessToken: null, user: null })
    }
  },

  fetchProfile: async () => {
    try {
      const user = await apiClient.get<UserResponse>('/auth/me')
      set({ user })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to fetch profile'
      set({ error: message })
      throw err
    }
  },

  updateProfile: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const user = await apiClient.put<UserResponse>('/auth/me', data)
      set({ user, isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to update profile'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  changePassword: async (
    currentPassword: string,
    newPassword: string,
  ) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.put('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      set({ isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to change password'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  forgotPassword: async (email: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post('/auth/forgot-password', { email })
      set({ isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to send reset email'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  resetPassword: async (token: string, newPassword: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post('/auth/reset-password', {
        token,
        new_password: newPassword,
      })
      set({ isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to reset password'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  verifyEmail: async (token: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post('/auth/verify-email', { token })
      // Re-fetch profile to reflect verified status
      const user = await apiClient.get<UserResponse>('/auth/me')
      set({ user, isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to verify email'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  resendVerification: async () => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post('/auth/resend-verification')
      set({ isLoading: false })
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to resend verification'
      set({ isLoading: false, error: message })
      throw err
    }
  },

  initialize: async () => {
    set({ isLoading: true })
    try {
      const refreshRes = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      })
      if (refreshRes.ok) {
        const { access_token } = await refreshRes.json()
        set({ accessToken: access_token })
        // Fetch user profile
        try {
          const user = await apiClient.get<UserResponse>('/auth/me')
          set({ user, isLoading: false })
        } catch {
          set({ isLoading: false })
        }
      } else {
        // No valid session — that's fine
        set({ isLoading: false })
      }
    } catch {
      // Network error or similar — just show the unauthenticated UI
      set({ isLoading: false })
    }
  },
}))

/** Convenience selector for boolean auth check. */
export const useIsAuthenticated = () =>
  useAuthStore((s) => s.accessToken !== null)
