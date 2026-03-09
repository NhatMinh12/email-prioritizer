import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Must mock axios before importing client
vi.mock('axios', () => {
  const interceptors = {
    request: { use: vi.fn(), handlers: [] },
    response: { use: vi.fn(), handlers: [] },
  }

  // Capture interceptor callbacks when use() is called
  interceptors.request.use.mockImplementation((onFulfilled, onRejected) => {
    interceptors.request.handlers.push({ onFulfilled, onRejected })
  })
  interceptors.response.use.mockImplementation((onFulfilled, onRejected) => {
    interceptors.response.handlers.push({ onFulfilled, onRejected })
  })

  const instance = {
    interceptors,
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  }

  return {
    default: {
      create: vi.fn(() => instance),
    },
  }
})

describe('API Client', () => {
  let axios
  let requestHandler
  let responseErrorHandler

  beforeEach(async () => {
    vi.resetModules()
    axios = (await import('axios')).default
    // Re-import to trigger interceptor registration
    await import('../../api/client')
    const instance = axios.create()
    requestHandler = instance.interceptors.request.handlers[0]
    responseErrorHandler = instance.interceptors.response.handlers[0]
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  describe('instance config', () => {
    it('creates axios instance with baseURL /', () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({ baseURL: '/' })
      )
    })

    it('sets Content-Type to application/json', () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      )
    })
  })

  describe('request interceptor', () => {
    it('adds Authorization header when token exists', () => {
      localStorage.setItem('authToken', 'test-jwt-token')
      const config = { headers: {} }
      const result = requestHandler.onFulfilled(config)
      expect(result.headers.Authorization).toBe('Bearer test-jwt-token')
    })

    it('does not add Authorization header when no token', () => {
      const config = { headers: {} }
      const result = requestHandler.onFulfilled(config)
      expect(result.headers.Authorization).toBeUndefined()
    })
  })

  describe('response interceptor', () => {
    it('dispatches auth:logout event on 401', () => {
      localStorage.setItem('authToken', 'some-token')
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')

      const error = { response: { status: 401 } }
      expect(responseErrorHandler.onRejected(error)).rejects.toEqual(error)

      expect(localStorage.getItem('authToken')).toBeNull()
      expect(dispatchSpy).toHaveBeenCalledWith(expect.any(Event))
      expect(dispatchSpy.mock.calls[0][0].type).toBe('auth:logout')
    })

    it('does not dispatch on non-401 errors', () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')

      const error = { response: { status: 500 } }
      expect(responseErrorHandler.onRejected(error)).rejects.toEqual(error)

      expect(dispatchSpy).not.toHaveBeenCalled()
    })
  })
})
