import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for 401 handling.
// Dispatches a custom event so AuthContext can trigger a React Router
// redirect instead of a full page reload.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(error)
  }
)

export default apiClient
