import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'

const mockUseAuth = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import apiClient from '../../api/client'

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  it('renders sign in button', () => {
    renderLogin()
    expect(screen.getByText('Sign in with Google')).toBeInTheDocument()
  })

  it('renders nothing while loading', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: true,
      login: vi.fn(),
      logout: vi.fn(),
    })
    const { container } = renderLogin()
    expect(container.firstChild).toBeNull()
  })

  it('redirects when already logged in', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderLogin()
    // Navigate renders nothing visible
    expect(screen.queryByText('Sign in with Google')).not.toBeInTheDocument()
  })

  it('calls /auth/login on button click', async () => {
    apiClient.get.mockResolvedValue({
      data: { authorization_url: 'https://accounts.google.com/auth' },
    })

    // Mock window.location
    delete window.location
    window.location = { href: '' }

    renderLogin()
    fireEvent.click(screen.getByText('Sign in with Google'))

    expect(screen.getByText('Redirecting...')).toBeInTheDocument()

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/auth/login')
    })
  })

  it('shows error on login failure', async () => {
    apiClient.get.mockRejectedValue(new Error('Network error'))

    renderLogin()
    fireEvent.click(screen.getByText('Sign in with Google'))

    await waitFor(() => {
      expect(
        screen.getByText('Failed to start login. Please try again.')
      ).toBeInTheDocument()
    })
  })
})
