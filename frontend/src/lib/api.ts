/** HTTP API client with automatic access-token injection and silent refresh.

On a 401 response the client attempts a silent token refresh via the
HTTP-only cookie (sent automatically with ``credentials: "include"``).
If refresh succeeds the original request is retried; otherwise the auth
store is cleared and the user is redirected to the login page.

Concurrent 401s are coalesced so only a single refresh call is issued.
*/

import { useAuthStore } from '@/stores/auth'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// ---------------------------------------------------------------------------
// Refresh-queue
// ---------------------------------------------------------------------------

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string | null) => void
  reject: (err: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null): void {
  for (const { resolve, reject } of failedQueue) {
    if (error) reject(error)
    else resolve(token)
  }
  failedQueue = []
}

// ---------------------------------------------------------------------------
// Core request helper
// ---------------------------------------------------------------------------

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  /** If true, body is sent as multipart/form-data (no JSON.stringify). */
  isFormData?: boolean,
): Promise<T> {
  const baseUrl = '' // Vite proxy handles /api/v1 routing
  const url = `${baseUrl}/api/v1${path}`

  // Build headers
  const headers: Record<string, string> = {}
  if (body !== undefined && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  const token = useAuthStore.getState().accessToken
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Initial fetch
  const requestBody =
    body !== undefined
      ? isFormData
        ? (body as BodyInit)
        : JSON.stringify(body)
      : undefined
  let response = await fetch(url, {
    method,
    headers,
    body: requestBody,
    credentials: 'include', // sends refresh-token cookie
  })

  // ── Silent refresh on 401 ──────────────────────────────────────
  if (response.status === 401 && token) {
    if (!isRefreshing) {
      isRefreshing = true

      try {
        const refreshRes = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          credentials: 'include',
        })

        if (refreshRes.ok) {
          const { access_token } = await refreshRes.json()
          useAuthStore.getState().setAccessToken(access_token)
          processQueue(null, access_token)
          headers['Authorization'] = `Bearer ${access_token}`

          // Retry original request
          const retryBody =
            body !== undefined
              ? isFormData
                ? (body as BodyInit)
                : JSON.stringify(body)
              : undefined
          response = await fetch(url, {
            method,
            headers,
            body: retryBody,
            credentials: 'include',
          })
        } else {
          // Refresh failed — terminate
          processQueue(new Error('Refresh failed'), null)
          useAuthStore.getState().clearAuth()
          window.location.href = '/auth/login'
          throw new ApiError(401, 'Session expired — please log in again')
        }
      } catch (err) {
        processQueue(err, null)
        useAuthStore.getState().clearAuth()
        window.location.href = '/auth/login'
        throw err
      } finally {
        isRefreshing = false
      }
    } else {
      // Another refresh is in flight — wait for it
      const newToken = await new Promise<string | null>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`
        const queueBody =
          body !== undefined
            ? isFormData
              ? (body as BodyInit)
              : JSON.stringify(body)
            : undefined
        response = await fetch(url, {
          method,
          headers,
          body: queueBody,
          credentials: 'include',
        })
      } else {
        throw new ApiError(401, 'Session expired')
      }
    }
  }

  // ── Error handling ─────────────────────────────────────────────
  if (!response.ok) {
    let detail = response.statusText
    try {
      const errBody = await response.json()
      detail = errBody.detail ?? detail
    } catch {
      // ignore parse failures
    }
    throw new ApiError(response.status, detail)
  }

  // Handle 204 No Content
  if (response.status === 204) return undefined as T

  return response.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const apiClient = {
  get<T>(path: string): Promise<T> {
    return request<T>('GET', path)
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>('POST', path, body)
  },
  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>('PUT', path, body)
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>('PATCH', path, body)
  },
  delete<T>(path: string): Promise<T> {
    return request<T>('DELETE', path)
  },
  /** Upload a file as multipart/form-data. */
  upload<T>(path: string, formData: FormData): Promise<T> {
    return request<T>('POST', path, formData, true)
  },
}
