import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function Nav() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const isActive = (path) =>
    location.pathname === path
      ? 'text-blue-600 font-medium'
      : 'text-gray-700 hover:text-gray-900'

  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="text-xl font-bold text-gray-900">
            Email Prioritizer
          </Link>

          {user && (
            <div className="flex items-center gap-6">
              <div className="flex gap-4">
                <Link to="/" className={`text-sm ${isActive('/')}`}>
                  Dashboard
                </Link>
                <Link
                  to="/settings"
                  className={`text-sm ${isActive('/settings')}`}
                >
                  Settings
                </Link>
              </div>

              <div className="flex items-center gap-3 pl-6 border-l border-gray-200">
                <span className="text-sm text-gray-500">{user.email}</span>
                <button
                  onClick={logout}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
