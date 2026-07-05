import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../stores/auth'
import { apiClient } from '../lib/api'

vi.mock('../lib/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
  },
}))

describe('Auth Store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset state to initial defaults manually
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isLoading: false,
      error: null,
    })
  })

  it('sets access token', () => {
    useAuthStore.getState().setAccessToken('new-token')
    expect(useAuthStore.getState().accessToken).toBe('new-token')
  })

  it('clears authentication state', () => {
    useAuthStore.setState({
      accessToken: 'token',
      user: { id: '1', email: 'test@example.com' } as any,
      error: 'some error',
    })
    useAuthStore.getState().clearAuth()
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('logs in successfully and sets user and token', async () => {
    const mockUser = { id: '1', email: 'test@example.com', username: 'testuser' }
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      access_token: 'login-token',
      user: mockUser,
    })

    await useAuthStore.getState().login('test@example.com', 'password')

    expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
      login: 'test@example.com',
      password: 'password',
    })
    expect(useAuthStore.getState().accessToken).toBe('login-token')
    expect(useAuthStore.getState().user).toEqual(mockUser)
    expect(useAuthStore.getState().error).toBeNull()
  })

  it('handles login failure and sets error state', async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Invalid credentials'))

    await expect(
      useAuthStore.getState().login('test@example.com', 'wrong')
    ).rejects.toThrow()

    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().error).toBe('Invalid credentials')
  })

  it('registers successfully', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({})

    await useAuthStore.getState().register('test@example.com', 'testuser', 'password', 'Display Name')

    expect(apiClient.post).toHaveBeenCalledWith('/auth/register', {
      email: 'test@example.com',
      username: 'testuser',
      password: 'password',
      display_name: 'Display Name',
    })
  })

  it('logs out and clears store', async () => {
    useAuthStore.setState({
      accessToken: 'token',
      user: { id: '1' } as any,
    })
    vi.mocked(apiClient.post).mockResolvedValueOnce({})

    await useAuthStore.getState().logout()

    expect(apiClient.post).toHaveBeenCalledWith('/auth/logout')
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('fetches current user profile', async () => {
    const mockUser = { id: '1', email: 'test@example.com' }
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockUser)

    await useAuthStore.getState().fetchProfile()

    expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
    expect(useAuthStore.getState().user).toEqual(mockUser)
  })

  it('initializes by refreshing token', async () => {
    const mockUser = { id: '1', email: 'test@example.com' }
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'refreshed-token' }),
    })
    vi.stubGlobal('fetch', mockFetch)
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockUser) // For /auth/me

    await useAuthStore.getState().initialize()

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    })
    expect(useAuthStore.getState().accessToken).toBe('refreshed-token')
    expect(useAuthStore.getState().user).toEqual(mockUser)
    expect(useAuthStore.getState().isLoading).toBe(false)
  })
})
