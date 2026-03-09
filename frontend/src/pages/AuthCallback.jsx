import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import apiClient from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState(null)

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setError('No authentication token received.')
      return
    }

    // Store the token, then fetch user info
    localStorage.setItem('authToken', token)
    apiClient
      .get('/auth/me')
      .then((res) => {
        login(token, res.data)
        navigate('/', { replace: true })
      })
      .catch(() => {
        localStorage.removeItem('authToken')
        setError('Authentication failed. Please try again.')
      })
  }, [searchParams, login, navigate])

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="bg-white rounded-lg shadow p-6 max-w-md text-center">
          <div className="text-red-600 mb-4">{error}</div>
          <a
            href="/login"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            Back to login
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-gray-500">Completing sign in...</div>
    </div>
  )
}
