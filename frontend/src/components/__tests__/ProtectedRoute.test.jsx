import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '../ProtectedRoute'

const mockUseAuth = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderWithRoute() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  it('shows loading state', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true })
    renderWithRoute()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('redirects to /login when not authenticated', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false })
    renderWithRoute()
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'test@test.com' },
      loading: false,
    })
    renderWithRoute()
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })
})
