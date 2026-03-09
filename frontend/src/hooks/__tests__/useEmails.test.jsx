import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useEmails } from '../useEmails'

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import apiClient from '../../api/client'

const mockEmailList = {
  emails: [
    {
      id: 'e1',
      sender: 'boss@co.com',
      subject: 'Urgent',
      body_preview: 'Need this ASAP',
      received_at: '2026-03-01T10:00:00Z',
      has_attachments: false,
      thread_length: 1,
      classification: {
        priority: 'high',
        urgency: 'urgent',
        needs_response: true,
        reason: 'From boss',
        action_items: ['Reply'],
        feedback: null,
      },
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
}

describe('useEmails', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClient.get.mockResolvedValue({ data: mockEmailList })
  })

  it('fetches emails on mount', async () => {
    const { result } = renderHook(() => useEmails())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(apiClient.get).toHaveBeenCalledWith('/api/emails', {
      params: { page: 1, page_size: 20 },
    })
    expect(result.current.emails).toEqual(mockEmailList.emails)
    expect(result.current.total).toBe(1)
  })

  it('sets error on fetch failure', async () => {
    apiClient.get.mockRejectedValue({
      response: { data: { detail: 'Server error' } },
    })

    const { result } = renderHook(() => useEmails())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Server error')
    expect(result.current.emails).toEqual([])
  })

  it('sets fallback error message', async () => {
    apiClient.get.mockRejectedValue(new Error('network'))

    const { result } = renderHook(() => useEmails())

    await waitFor(() => {
      expect(result.current.error).toBe('Failed to load emails')
    })
  })

  it('passes priority filter to API', async () => {
    const { result } = renderHook(() => useEmails())

    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => {
      result.current.changeFilter('high')
    })

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/emails', {
        params: { page: 1, page_size: 20, priority: 'high' },
      })
    })
  })

  it('resets page to 1 when filter changes', async () => {
    const { result } = renderHook(() => useEmails())

    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => {
      result.current.changePage(3)
    })

    await waitFor(() => expect(result.current.page).toBe(3))

    act(() => {
      result.current.changeFilter('low')
    })

    expect(result.current.page).toBe(1)
  })

  it('syncs inbox and refreshes', async () => {
    apiClient.post.mockResolvedValue({ data: { synced: 5 } })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.syncInbox()
    })

    expect(apiClient.post).toHaveBeenCalledWith('/api/emails/sync')
    expect(result.current.statusMessage).toBe('Synced 5 new emails')
    expect(result.current.syncing).toBe(false)
  })

  it('handles sync error', async () => {
    apiClient.post.mockRejectedValue({
      response: { data: { detail: 'Gmail re-authentication required' } },
    })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.syncInbox()
    })

    expect(result.current.statusMessage).toBe(
      'Gmail re-authentication required'
    )
  })

  it('classifies emails (small batch)', async () => {
    apiClient.post.mockResolvedValue({
      data: { classified: 3, message: 'Successfully classified 3 emails' },
    })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.classifyEmails()
    })

    expect(apiClient.post).toHaveBeenCalledWith('/api/emails/classify')
    expect(result.current.statusMessage).toBe(
      'Successfully classified 3 emails'
    )
  })

  it('classifies emails (background batch)', async () => {
    apiClient.post.mockResolvedValue({
      data: {
        classified: 0,
        message: 'Classification of 15 emails started in background',
        status: 'accepted',
      },
    })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.classifyEmails()
    })

    expect(result.current.statusMessage).toBe(
      'Classification of 15 emails started in background'
    )
  })

  it('submits feedback and refreshes', async () => {
    apiClient.post.mockResolvedValue({ data: {} })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.submitFeedback('e1', 'correct')
    })

    expect(apiClient.post).toHaveBeenCalledWith('/api/emails/e1/feedback', {
      feedback: 'correct',
    })
  })

  it('dismisses status message', async () => {
    apiClient.post.mockResolvedValue({ data: { synced: 1 } })

    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.syncInbox()
    })

    expect(result.current.statusMessage).toBeTruthy()

    act(() => {
      result.current.dismissStatus()
    })

    expect(result.current.statusMessage).toBeNull()
  })

  it('changes page', async () => {
    const { result } = renderHook(() => useEmails())
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => {
      result.current.changePage(2)
    })

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/emails', {
        params: { page: 2, page_size: 20 },
      })
    })
  })
})
