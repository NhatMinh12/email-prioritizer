import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { usePreferences } from '../usePreferences'

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

import apiClient from '../../api/client'

const mockPreferences = {
  user_id: 'u1',
  important_senders: ['boss@co.com'],
  important_keywords: ['urgent'],
  response_rate: 0.75,
  updated_at: '2026-03-01T00:00:00Z',
}

describe('usePreferences', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClient.get.mockResolvedValue({ data: mockPreferences })
  })

  it('fetches preferences on mount', async () => {
    const { result } = renderHook(() => usePreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(apiClient.get).toHaveBeenCalledWith('/api/preferences')
    expect(result.current.preferences).toEqual(mockPreferences)
  })

  it('sets error on fetch failure', async () => {
    apiClient.get.mockRejectedValue({
      response: { data: { detail: 'Not found' } },
    })

    const { result } = renderHook(() => usePreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Not found')
  })

  it('sets fallback error message', async () => {
    apiClient.get.mockRejectedValue(new Error('network'))

    const { result } = renderHook(() => usePreferences())

    await waitFor(() => {
      expect(result.current.error).toBe('Failed to load preferences')
    })
  })

  it('updates preferences successfully', async () => {
    const updated = { ...mockPreferences, important_keywords: ['urgent', 'deadline'] }
    apiClient.put.mockResolvedValue({ data: updated })

    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.loading).toBe(false))

    let success
    await act(async () => {
      success = await result.current.updatePreferences({
        important_keywords: ['urgent', 'deadline'],
      })
    })

    expect(success).toBe(true)
    expect(apiClient.put).toHaveBeenCalledWith('/api/preferences', {
      important_keywords: ['urgent', 'deadline'],
    })
    expect(result.current.preferences).toEqual(updated)
    expect(result.current.saving).toBe(false)
  })

  it('handles update failure', async () => {
    apiClient.put.mockRejectedValue({
      response: { data: { detail: 'Validation error' } },
    })

    const { result } = renderHook(() => usePreferences())
    await waitFor(() => expect(result.current.loading).toBe(false))

    let success
    await act(async () => {
      success = await result.current.updatePreferences({
        important_senders: [],
      })
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Validation error')
  })
})
