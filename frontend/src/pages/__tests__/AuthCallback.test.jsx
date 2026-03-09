import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AuthCallback from '../AuthCallback'

const mockLogin = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    loading: false,
    logout: vi.fn(),
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import apiClient from '../../api/client'

describe('AuthCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows error when no token in URL', () => {
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <AuthCallback />
      </MemoryRouter>
    )

    expect(
      screen.getByText('No authentication token received.')
    ).toBeInTheDocument()
    expect(screen.getByText('Back to login')).toBeInTheDocument()
  })

  it('fetches user info and redirects on success', async () => {
    const userInfo = { id: '123', email: 'test@test.com' }
    apiClient.get.mockResolvedValue({ data: userInfo })

    render(
      <MemoryRouter initialEntries={['/auth/callback?token=jwt-token-123']}>
        <AuthCallback />
      </MemoryRouter>
    )

    expect(screen.getByText('Completing sign in...')).toBeInTheDocument()

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/auth/me')
    })

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('jwt-token-123', userInfo)
    })

    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })

  it('shows error on failed auth/me call', async () => {
    apiClient.get.mockRejectedValue({ response: { status: 401 } })

    render(
      <MemoryRouter initialEntries={['/auth/callback?token=bad-token']}>
        <AuthCallback />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByText('Authentication failed. Please try again.')
      ).toBeInTheDocument()
    })

    expect(localStorage.getItem('authToken')).toBeNull()
  })

  it('stores token in localStorage before calling /auth/me', async () => {
    apiClient.get.mockImplementation(() => {
      // At this point, token should be in localStorage
      expect(localStorage.getItem('authToken')).toBe('my-token')
      return Promise.resolve({ data: { id: '1', email: 'x@x.com' } })
    })

    render(
      <MemoryRouter initialEntries={['/auth/callback?token=my-token']}>
        <AuthCallback />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalled()
    })
  })
})
