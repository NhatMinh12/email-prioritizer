import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../contexts/AuthContext'
import { useAuth } from '../useAuth'

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

import apiClient from '../../api/client'

function wrapper({ children }) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  )
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('throws when used outside AuthProvider', () => {
    // Suppress console.error for this test
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() =>
      renderHook(() => useAuth(), { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> })
    ).toThrow('useAuth must be used within an AuthProvider')
    spy.mockRestore()
  })

  it('starts with loading=true when token exists', () => {
    localStorage.setItem('authToken', 'test-token')
    apiClient.get.mockReturnValue(new Promise(() => {})) // never resolves

    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.loading).toBe(true)
    expect(result.current.user).toBeNull()
  })

  it('sets loading=false immediately when no token', async () => {
    apiClient.get.mockRejectedValue(new Error('no token'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.user).toBeNull()
  })

  it('fetches user info on mount when token exists', async () => {
    localStorage.setItem('authToken', 'valid-token')
    const userInfo = { id: '123', email: 'test@example.com' }
    apiClient.get.mockResolvedValue({ data: userInfo })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.user).toEqual(userInfo)
    expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
  })

  it('clears user on failed /auth/me call', async () => {
    localStorage.setItem('authToken', 'bad-token')
    apiClient.get.mockRejectedValue({ response: { status: 401 } })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('authToken')).toBeNull()
  })

  it('login stores token and sets user', async () => {
    apiClient.get.mockRejectedValue(new Error('no token'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const userInfo = { id: '456', email: 'user@test.com' }
    act(() => {
      result.current.login('new-token', userInfo)
    })

    expect(localStorage.getItem('authToken')).toBe('new-token')
    expect(result.current.user).toEqual(userInfo)
  })

  it('logout clears token and user', async () => {
    localStorage.setItem('authToken', 'valid-token')
    const userInfo = { id: '123', email: 'test@example.com' }
    apiClient.get.mockResolvedValue({ data: userInfo })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(userInfo)
    })

    act(() => {
      result.current.logout()
    })

    expect(localStorage.getItem('authToken')).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('listens for auth:logout event', async () => {
    localStorage.setItem('authToken', 'valid-token')
    const userInfo = { id: '123', email: 'test@example.com' }
    apiClient.get.mockResolvedValue({ data: userInfo })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(userInfo)
    })

    act(() => {
      window.dispatchEvent(new Event('auth:logout'))
    })

    expect(result.current.user).toBeNull()
  })
})
