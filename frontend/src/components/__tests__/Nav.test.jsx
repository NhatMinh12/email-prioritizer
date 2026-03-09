import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Nav } from '../Nav'

const mockUseAuth = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderNav(initialEntries = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Nav />
    </MemoryRouter>
  )
}

describe('Nav', () => {
  it('renders app title', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      logout: vi.fn(),
    })
    renderNav()
    expect(screen.getByText('Email Prioritizer')).toBeInTheDocument()
  })

  it('does not show nav links when not logged in', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      logout: vi.fn(),
    })
    renderNav()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
  })

  it('shows nav links when logged in', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout: vi.fn(),
    })
    renderNav()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('shows user email', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout: vi.fn(),
    })
    renderNav()
    expect(screen.getByText('user@test.com')).toBeInTheDocument()
  })

  it('shows sign out button', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout: vi.fn(),
    })
    renderNav()
    expect(screen.getByText('Sign out')).toBeInTheDocument()
  })

  it('calls logout on sign out click', () => {
    const logout = vi.fn()
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout,
    })
    renderNav()
    fireEvent.click(screen.getByText('Sign out'))
    expect(logout).toHaveBeenCalled()
  })

  it('highlights active Dashboard link', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout: vi.fn(),
    })
    renderNav(['/'])
    const dashLink = screen.getByText('Dashboard')
    expect(dashLink.className).toContain('text-blue-600')
  })

  it('highlights active Settings link', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@test.com' },
      logout: vi.fn(),
    })
    renderNav(['/settings'])
    const settingsLink = screen.getByText('Settings')
    expect(settingsLink.className).toContain('text-blue-600')
  })
})
