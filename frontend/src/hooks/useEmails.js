import { useCallback, useEffect, useState } from 'react'
import apiClient from '../api/client'

export function useEmails() {
  const [emails, setEmails] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [priorityFilter, setPriorityFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [classifying, setClassifying] = useState(false)
  const [statusMessage, setStatusMessage] = useState(null)

  const fetchEmails = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: pageSize }
      if (priorityFilter) {
        params.priority = priorityFilter
      }
      const res = await apiClient.get('/api/emails', { params })
      setEmails(res.data.emails)
      setTotal(res.data.total)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load emails')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, priorityFilter])

  useEffect(() => {
    fetchEmails()
  }, [fetchEmails])

  const syncInbox = useCallback(async () => {
    setSyncing(true)
    setStatusMessage(null)
    try {
      const res = await apiClient.post('/api/emails/sync')
      setStatusMessage(`Synced ${res.data.synced} new emails`)
      await fetchEmails()
    } catch (err) {
      const detail = err.response?.data?.detail || 'Sync failed'
      setStatusMessage(detail)
    } finally {
      setSyncing(false)
    }
  }, [fetchEmails])

  const classifyEmails = useCallback(async () => {
    setClassifying(true)
    setStatusMessage(null)
    try {
      const res = await apiClient.post('/api/emails/classify')
      if (res.data.status === 'accepted') {
        setStatusMessage(res.data.message)
      } else {
        setStatusMessage(res.data.message)
        await fetchEmails()
      }
    } catch (err) {
      setStatusMessage(err.response?.data?.detail || 'Classification failed')
    } finally {
      setClassifying(false)
    }
  }, [fetchEmails])

  const submitFeedback = useCallback(
    async (emailId, feedback) => {
      try {
        await apiClient.post(`/api/emails/${emailId}/feedback`, { feedback })
        await fetchEmails()
      } catch {
        setStatusMessage('Failed to submit feedback')
      }
    },
    [fetchEmails]
  )

  const changePage = useCallback((newPage) => {
    setPage(newPage)
  }, [])

  const changeFilter = useCallback((priority) => {
    setPriorityFilter(priority)
    setPage(1)
  }, [])

  const dismissStatus = useCallback(() => {
    setStatusMessage(null)
  }, [])

  return {
    emails,
    total,
    page,
    pageSize,
    priorityFilter,
    loading,
    error,
    syncing,
    classifying,
    statusMessage,
    syncInbox,
    classifyEmails,
    submitFeedback,
    changePage,
    changeFilter,
    dismissStatus,
  }
}
